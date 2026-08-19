# Plan: Câu hỏi tổng quan/phân tích có giá trị nghiệp vụ cao nhất

## 0. Cơ sở

Rà theo tool MCP thực tế đã có ở backend (`common/tools/*.java`): mỗi domain đều có sẵn
`*_tongquan` (số liệu tổng hợp toàn hệ thống), một số domain có thêm `*_top`/xếp hạng và tool
phát hiện bất thường. Đây là các "viên gạch" đã sẵn sàng — phần lớn giá trị nằm ở việc **orchestrator
biết gộp đúng viên gạch nào** cho câu hỏi tổng quan/phân tích, không phải xây tool mới.

Xếp theo 3 tier: đã trả lời được ngay / cần orchestrator gộp nhiều module / cần bổ sung tool mới.

## 1. Tier 1 — Đã có tool, trả lời được ngay (ưu tiên viết test case + đảm bảo routing đúng)

| Câu hỏi mẫu | Module | Tool |
|---|---|---|
| "Tổng quan hợp đồng hiện nay thế nào?" | tiendo | `hopdong_tongquan` |
| "Sản lượng kỳ này so với kỳ trước tăng/giảm bao nhiêu %?" | tiendo | `sanluong_tonghop` (periodGrowthPercent) |
| "Tình hình vướng mắc chung ra sao, bao nhiêu đang mở/quá hạn?" | vanhanh | `vuongmac_tongquan` |
| "Top 5 hợp đồng nhiều vướng mắc nhất" | vanhanh | `vuongmac_top_hopdong` |
| "Vướng mắc nào quá hạn 30 ngày chưa xử lý?" | vanhanh | `vuongmac_qua_han` |
| "Tổng quan trạm tồn, phân theo lý do/thời gian tồn (aging)" | vanhanh | `tramton_tongquan` |
| "Trạm nào sản lượng bất thường so với hệ số hợp đồng?" | vanhanh | `tramton_sanluong_bat_thuong` |
| "Trạm nào lâu không cập nhật tiến độ, có nguy cơ bị bỏ quên?" | vanhanh | `tramton_thieu_capnhat` |
| "Tổng quan phân công hiện nay, bao nhiêu đang hoạt động?" | nhansu | `phancong_tongquan` |
| "Tổng quan nguồn lực đang triển khai" | nhansu | `nguonluc_tongquan` |
| "Tốc độ hoàn thành theo khu vực/nhà thầu, ai đang chậm hơn trung bình?" | nhansu | `nguonluc_toc_do_hoan_thanh` |
| "Top hợp đồng rủi ro nhất theo [tiêu chí]" | nhansu | `hopdong_top` |
| "Khu vực X có bao nhiêu trạm đang thi công/hoàn thành/vướng mắc?" | tiendo | `hopdong_trangthai_theo_khuvuc` |

**Việc cần làm**: không cần code mới — bổ sung bộ câu hỏi mẫu (đã có `tests/bo_cau_hoi_mau_va_tool.xlsx`)
để regression-test đúng tool được gọi, tránh orchestrator/agent chọn sai tool tương tự (vd nhầm
`_search` với `_tongquan`).

## 2. Tier 2 — Giá trị cao nhất, cần orchestrator gộp ≥2 module (chưa có tool sẵn kiểu này, nhưng
dữ liệu nền đã đủ — chỉ cần prompt điều phối + responder tổng hợp tốt)

Đây là nhóm **giá trị nghiệp vụ cao nhất** vì trả lời câu hỏi quản lý thực sự quan tâm ("tình hình
chung", "rủi ro ở đâu") mà không hệ thống báo cáo rời rạc nào trả lời trực tiếp được — chính là lý do
chatbot tồn tại thay vì chỉ mở từng màn hình báo cáo.

| Câu hỏi mẫu | Modules cần gộp | Giá trị nghiệp vụ |
|---|---|---|
| "Cho tôi tình hình chung hôm nay" / "Báo cáo nhanh đầu ngày" | tiendo + nhansu + vanhanh | Digest điều hành, thay thế việc mở 3-4 màn hình report mỗi sáng |
| "Trạm nào đang vướng mắc mà thiếu nhân lực xử lý?" | vanhanh + nhansu | Phát hiện điểm nghẽn (bottleneck) cần điều phối gấp |
| "Hợp đồng nào đang vướng mắc nhiều nhất, ai đang phụ trách xử lý?" | vanhanh + tiendo + nhansu | Gắn trách nhiệm xử lý trực tiếp vào vướng mắc, rút ngắn thời gian điều phối |
| "Khu vực nào tiến độ chậm nhất so với KPI hợp đồng và vì sao (thiếu nguồn lực hay vướng mắc)?" | tiendo + nhansu + vanhanh | Phân tích nguyên nhân gốc (root cause), không chỉ số liệu thô |
| "Cán bộ X đang phụ trách bao nhiêu trạm, trạm nào đang vướng, có đang quá tải không?" | nhansu (đã gộp phần vướng qua `phancong_tram_theo_canbo`) + đối chiếu nguồn lực | Đánh giá tải công việc cá nhân |
| "Rủi ro tuần này nằm ở đâu?" (trạm sắp quá hạn KPI + đang thiếu người + đang có sự cố) | cả 3 | Cảnh báo sớm chủ động thay vì chờ báo cáo |

**Việc cần làm**:
- Bổ sung ví dụ few-shot trong `orchestrator.txt` cho các câu hỏi "tình hình chung"/"rủi ro ở đâu"
  để đảm bảo chọn đúng ≥2-3 module thay vì chỉ 1.
- Tăng cường `responder.txt` để biết **đối chiếu chéo** kết quả (vd nối "trạm có vướng mắc" từ vanhanh
  với "trạm chưa phân công" từ nhansu theo mã trạm) thay vì chỉ nối 2 đoạn văn cạnh nhau.
- Đây là nhóm nên ưu tiên viết eval set riêng (không chỉ đúng tool, mà đúng cả việc tổng hợp chéo).

## 3. Tier 3 — Giá trị cao nhưng cần tool mới ở backend (`SanLuongTools`, v.v. chưa có)

| Câu hỏi mẫu | Vì sao chưa trả lời được | Đề xuất |
|---|---|---|
| "Sản lượng theo từng khu vực/nhà thầu là bao nhiêu?" | `sanluong_tonghop` chỉ trả số toàn hệ thống, không breakdown theo nhóm | Thêm param `groupBy` (khuVuc/nhaThau) hoặc tool `sanluong_theo_nhom` |
| "Xu hướng sản lượng 6 tháng gần nhất" (theo chuỗi thời gian) | Chỉ có growth % kỳ hiện tại vs kỳ trước, không có chuỗi | Thêm tool trả series theo tháng để vẽ xu hướng |
| "Dự báo hợp đồng nào có nguy cơ trễ KPI trong tháng tới" | Chưa có tool dự báo, chỉ có số liệu hiện trạng | Cần thêm rule/threshold hoặc mô hình dự báo đơn giản ở backend |
| "So sánh hiệu suất giữa các khu vực/nhà thầu" (ranking đa tiêu chí) | Có `hopdong_top` (1 tiêu chí) và `nguonluc_toc_do_hoan_thanh` (breakdown) riêng lẻ, chưa có view so sánh gộp | Có thể ghép ở Tier 2 trước khi cần tool mới |

**Việc cần làm**: không ưu tiên ngay — chỉ triển khai sau khi Tier 1 & 2 đã ổn định và có tín hiệu
người dùng thực sự hỏi các dạng này.

## 4. Đề xuất thứ tự triển khai

1. **Tier 1**: viết bộ test case đầy đủ (mở rộng `tests/bo_cau_hoi_mau_va_tool.xlsx`) để khóa đúng
   tool routing cho toàn bộ câu hỏi tổng quan/xếp hạng hiện có — rủi ro thấp, làm ngay.
2. **Tier 2**: đầu tư prompt engineering cho `orchestrator.txt` + `responder.txt` để xử lý tốt câu hỏi
   "tình hình chung"/"rủi ro ở đâu" — đây là nhóm mang lại giá trị khác biệt lớn nhất so với việc chỉ
   tra cứu số liệu đơn lẻ.
3. **Tier 3**: backlog — chỉ làm khi có tool mới, ưu tiên breakdown sản lượng theo nhóm trước (nhu cầu
   rõ ràng nhất, ít phức tạp nhất trong nhóm này).
