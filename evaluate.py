"""Eval harness cho chatbot: đọc eval_dataset_1000.jsonl, gọi /api/v1/chat/stream, bắt tool thực
tế đã gọi qua SSE event "status" (on_tool_start), so với expected_tools, tính các chỉ số:
tool-selection accuracy, precision/recall (multi-tool), refusal accuracy, redundant-call rate,
latency p50/p95. Không cần parse log backend — SSE đã phát tên tool ngay khi agent bắt đầu gọi.

Chạy:
    python evaluate.py --dataset data/eval_dataset_cauhoi_ai.jsonl --base-url http://localhost:8000 --limit 50 --workers 8
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import threading
import time
import uuid
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass

import requests

# Console Windows mac dinh dung cp1252, khong in duoc tieng Viet co dau -> ep UTF-8.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


@dataclass
class CaseResult:
    id: int
    question: str
    category: str
    test_type: str
    expected_tools: list[str]
    actual_tools: list[str]
    latency_ms: float
    error: str | None = None

    @property
    def passed(self) -> bool:
        if self.error:
            return False
        expected = set(self.expected_tools)
        actual = set(self.actual_tools)
        if self.test_type in ("refusal", "clarify"):
            # refusal: câu hỏi ngoài phạm vi, agent phải từ chối, không gọi tool nào.
            # clarify: câu hỏi thiếu định danh bắt buộc (thiếu mã/tên cụ thể), agent phải hỏi
            # lại thay vì tự đoán/tự chọn đại — cùng tín hiệu đo (không gọi tool) nhưng khác
            # ý nghĩa nghiệp vụ nên giữ 2 category riêng để đọc report dễ phân biệt.
            return len(actual) == 0
        if self.test_type == "no_redundant_call":
            return actual == expected
        # single_tool / multi_tool / multi_tool_chain: recall đủ tool cần thiết (không bắt buộc
        # khớp tuyệt đối thứ tự/số lần gọi, vì agent có thể hợp lệ gọi thêm bước phụ trợ nhỏ).
        return expected.issubset(actual)

    @property
    def precision_ok(self) -> bool:
        """Không gọi tool thừa ngoài expected — chỉ áp dụng khi expected không rỗng."""
        if not self.expected_tools:
            return True
        return set(self.actual_tools).issubset(set(self.expected_tools))


def call_chat_stream(base_url: str, question: str, timeout: float) -> tuple[list[str], float]:
    """Gọi /api/v1/chat/stream, trả về (danh sách tool đã gọi theo thứ tự, latency ms)."""
    session_id = str(uuid.uuid4())
    start = time.perf_counter()
    tools_called: list[str] = []

    with requests.post(
        f"{base_url}/api/v1/chat/stream",
        json={"message": question, "session_id": session_id},
        stream=True,
        timeout=timeout,
    ) as resp:
        resp.raise_for_status()
        current_event = None
        for raw_line in resp.iter_lines(decode_unicode=True):
            if raw_line is None:
                continue
            line = raw_line.strip()
            if not line:
                current_event = None
                continue
            if line.startswith("event:"):
                current_event = line[len("event:"):].strip()
                continue
            if line.startswith("data:"):
                payload = line[len("data:"):].strip()
                if current_event == "status":
                    try:
                        data = json.loads(payload)
                    except json.JSONDecodeError:
                        continue
                    module = data.get("module") or data.get("node")
                    if module and (not module.startswith("thoigian_") or True):
                        tools_called.append(module)
                elif current_event == "done":
                    break

    latency_ms = (time.perf_counter() - start) * 1000
    return tools_called, latency_ms


def _run_one(row: dict, base_url: str, timeout: float) -> CaseResult:
    try:
        tools_called, latency_ms = call_chat_stream(base_url, row["question"], timeout)
        return CaseResult(
            id=row["id"], question=row["question"], category=row["category"],
            test_type=row["test_type"], expected_tools=row["expected_tools"],
            actual_tools=tools_called, latency_ms=latency_ms,
        )
    except Exception as exc:  # noqa: BLE001 - eval harness phải tiếp tục dù 1 case lỗi
        return CaseResult(
            id=row["id"], question=row["question"], category=row["category"],
            test_type=row["test_type"], expected_tools=row["expected_tools"],
            actual_tools=[], latency_ms=0.0, error=str(exc),
        )


def run_eval(
    dataset_path: str, base_url: str, limit: int | None, timeout: float, workers: int,
) -> list[CaseResult]:
    with open(dataset_path, encoding="utf-8") as f:
        rows = [json.loads(line) for line in f]
    if limit:
        rows = rows[:limit]

    total = len(rows)
    print(f"Chạy {total} testcase với {workers} luồng song song...", flush=True)

    results: list[CaseResult] = [None] * total  # type: ignore[list-item]
    done_count = 0
    lock = threading.Lock()

    with ThreadPoolExecutor(max_workers=workers) as pool:
        future_to_idx = {
            pool.submit(_run_one, row, base_url, timeout): i
            for i, row in enumerate(rows)
        }
        for future in as_completed(future_to_idx):
            idx = future_to_idx[future]
            results[idx] = future.result()
            with lock:
                done_count += 1
                if done_count % 10 == 0 or done_count == total:
                    print(f"[{done_count}/{total}] hoàn tất...", flush=True)

    return results


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    values = sorted(values)
    idx = min(int(len(values) * pct), len(values) - 1)
    return values[idx]


def print_report(results: list[CaseResult]) -> None:
    total = len(results)
    passed = sum(1 for r in results if r.passed)
    errors = sum(1 for r in results if r.error)

    print("\n" + "=" * 70)
    print(f"TỔNG QUAN — {total} testcase, {errors} lỗi gọi API")
    print("=" * 70)
    print(f"Tool-selection accuracy (tổng): {passed}/{total} = {passed / total * 100:.1f}%")

    print("\n--- Theo test_type ---")
    by_type: dict[str, list[CaseResult]] = defaultdict(list)
    for r in results:
        by_type[r.test_type].append(r)
    for test_type, rows in by_type.items():
        p = sum(1 for r in rows if r.passed)
        print(f"  {test_type:20s}: {p}/{len(rows)} = {p / len(rows) * 100:.1f}%")

    print("\n--- Theo category ---")
    by_cat: dict[str, list[CaseResult]] = defaultdict(list)
    for r in results:
        by_cat[r.category].append(r)
    for cat, rows in sorted(by_cat.items()):
        p = sum(1 for r in rows if r.passed)
        print(f"  {cat:15s}: {p}/{len(rows)} = {p / len(rows) * 100:.1f}%")

    # Precision — chỉ tính trên case có expected_tools (loại refusal)
    precision_rows = [r for r in results if r.expected_tools and not r.error]
    if precision_rows:
        prec_ok = sum(1 for r in precision_rows if r.precision_ok)
        print(f"\nPrecision (không gọi tool thừa): {prec_ok}/{len(precision_rows)} = "
              f"{prec_ok / len(precision_rows) * 100:.1f}%")

    # Redundant-call rate riêng
    redundant_rows = [r for r in results if r.test_type == "no_redundant_call"]
    if redundant_rows:
        ok = sum(1 for r in redundant_rows if r.passed)
        print(f"Redundant-call rate: {len(redundant_rows) - ok}/{len(redundant_rows)} lượt gọi thừa "
              f"({(len(redundant_rows) - ok) / len(redundant_rows) * 100:.1f}%)")

    # Refusal accuracy riêng
    refusal_rows = [r for r in results if r.test_type == "refusal"]
    if refusal_rows:
        ok = sum(1 for r in refusal_rows if r.passed)
        print(f"Refusal accuracy: {ok}/{len(refusal_rows)} = {ok / len(refusal_rows) * 100:.1f}%")

    # Latency
    latencies = [r.latency_ms for r in results if not r.error]
    if latencies:
        print("\n--- Latency (ms) ---")
        print(f"  p50: {percentile(latencies, 0.5):.0f}")
        print(f"  p95: {percentile(latencies, 0.95):.0f}")
        print(f"  avg: {statistics.mean(latencies):.0f}")

    # Danh sách case FAIL để soi nhanh
    failed = [r for r in results if not r.passed][:30]
    if failed:
        print(f"\n--- {len(failed)} case FAIL đầu tiên (tối đa 30) ---")
        for r in failed:
            print(f"  [{r.id}] {r.question[:60]}")
            print(f"        expected={r.expected_tools} actual={r.actual_tools} error={r.error}")


def save_results(results: list[CaseResult], out_path: str) -> None:
    with open(out_path, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps({
                "id": r.id, "question": r.question, "category": r.category,
                "test_type": r.test_type, "expected_tools": r.expected_tools,
                "actual_tools": r.actual_tools, "latency_ms": round(r.latency_ms, 1),
                "passed": r.passed, "error": r.error,
            }, ensure_ascii=False) + "\n")
    print(f"\nĐã lưu chi tiết kết quả: {out_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Eval tool-selection cho chatbot MCP")
    parser.add_argument("--dataset", default="data/eval_dataset_cauhoi_ai.jsonl")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--limit", type=int, default=None, help="Chỉ chạy N testcase đầu (test nhanh)")
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--workers", type=int, default=8, help="So luong request chay song song")
    parser.add_argument("--out", default="data/eval_results.jsonl")
    args = parser.parse_args()

    results = run_eval(args.dataset, args.base_url, args.limit, args.timeout, args.workers)
    print_report(results)
    save_results(results, args.out)


if __name__ == "__main__":
    main()
