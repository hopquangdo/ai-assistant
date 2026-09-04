"""``PromptRegistry`` — nạp prompt từ thư mục file, có cache + render biến + version.

    reg = PromptRegistry("app/prompts")           # *.txt / *.md / *.prompt
    sys = reg.get("agent")                          # nội dung file agent.txt
    msg = reg.get("followup", n=3, topic="hợp đồng")  # render {n} {topic} bằng str.format
    v2  = reg.get("agent", version="v2")            # đọc agent.v2.txt (hoặc agent/v2.txt)

Không phụ thuộc jinja2 — render bằng ``str.format`` (đủ cho prompt). Muốn template mạnh
hơn thì tự render trước rồi truyền chuỗi vào.
"""
from __future__ import annotations

from pathlib import Path

__all__ = ["PromptRegistry", "PromptNotFound"]

_EXTS = (".txt", ".md", ".prompt", ".j2", ".jinja")


class PromptNotFound(KeyError):
    """Không tìm thấy prompt theo tên/version."""


class PromptRegistry:
    def __init__(self, *dirs: str | Path, encoding: str = "utf-8") -> None:
        self._dirs = [Path(d) for d in dirs]
        self._encoding = encoding
        self._cache: dict[tuple[str, str | None], str] = {}

    def get(self, name: str, /, *, version: str | None = None, **variables: object) -> str:
        """Nội dung prompt ``name`` (đã render ``**variables`` bằng ``str.format`` nếu có).

        ``name`` là positional-only nên có thể truyền biến template trùng tên: ``get("greet", name="An")``.
        """
        key = (name, version)
        raw = self._cache.get(key)
        if raw is None:
            raw = self._cache[key] = self._read(name, version)
        return raw.format(**variables) if variables else raw

    def exists(self, name: str, /, *, version: str | None = None) -> bool:
        try:
            self._read(name, version)
            return True
        except PromptNotFound:
            return False

    def list(self) -> list[str]:
        """Tên các prompt (không version) tìm thấy trong mọi thư mục đã đăng ký."""
        names: set[str] = set()
        for d in self._dirs:
            if d.is_dir():
                names.update(p.stem for p in d.iterdir() if p.suffix in _EXTS)
        return sorted(names)

    def reload(self) -> None:
        self._cache.clear()

    # -- nội bộ -----------------------------------------------------------

    def _candidates(self, name: str, version: str | None) -> list[Path]:
        stems = [f"{name}.{version}", f"{name}"] if version else [name]
        out: list[Path] = []
        for d in self._dirs:
            for stem in stems:
                out += [d / f"{stem}{ext}" for ext in _EXTS]
            if version:
                out += [d / name / f"{version}{ext}" for ext in _EXTS]
        return out

    def _read(self, name: str, version: str | None) -> str:
        for path in self._candidates(name, version):
            if path.is_file():
                return path.read_text(encoding=self._encoding)
        raise PromptNotFound(f"{name!r}" + (f" (version {version!r})" if version else ""))
