# -*- coding: utf-8 -*-
"""Sinh sheet 'Tools' trong CauHoi_AI.xlsx:
TOOL_NAME | TOOL_DESCRIPTION | TOOL_PARAMS | TOOL_RESPONSE | QUERY_SCOPE | EXAMPLE_QUERIES | OUT_OF_SCOPE

Nguồn CHUẨN = code production tại
backend/src/main/java/.../common/tools/definitions/*.java  (annotation @Tool + @ToolParam)
và  .../dto/response/*.java  (field thực tế trả về).
KHÔNG lấy theo TOOL.md — file đó đã lệch so với code.

Chatbot nạp 10 tool nghiệp vụ; tool `thoigian_hientai` bị loại (ngày hiện tại tiêm
thẳng vào system message, xem app/utils/time_context.py). Tool `hosodoituong_tool`
mà TOOL.md nhắc tới HIỆN CHƯA tồn tại (dữ liệu khảo sát chỉ có một phần: ngày bàn
giao mặt bằng / trạng thái vật tư nằm trên hop_dong_doi_tuong, chưa có loại cột /
chiều cao / ảnh / ngày khảo sát).
"""
import re
import pandas as pd

XLSX = "CauHoi_AI.xlsx"
ALIAS = {"tramton_tool": "doituongton_tool"}  # tên cũ trong sheet 'Câu hỏi'

TOOLS = [
    dict(
        name="sanluong_tool",
        desc="Báo cáo sản lượng thi công. Tool tự thu hẹp phạm vi theo tham số lọc truyền vào nên một lần "
             "gọi đủ trả lời nhiều cách hỏi. Mọi số liệu chỉ tính trong khoảng [tuNgay, denNgay], mặc định "
             "30 ngày gần nhất, không quét toàn bộ lịch sử — ngoại lệ duy nhất là monthlyTrend luôn quét 6 tháng.",
        params="maDoiTuong, maHopDong, nhaThauId (ưu tiên hơn tenNhaThau), tenNhaThau, khuVuc, tuNgay, denNgay "
               "— tất cả tùy chọn; để trống hết thì trả tổng quan toàn hệ thống.",
        resp="period (kỳ đang xét); summary (tổng sản lượng, số đối tượng đã / chưa có sản lượng, sản lượng hôm nay, "
             "trung bình, openIssueCount = số vướng mắc mở liên quan); progress (% hoàn thành theo hạng mục + 4 nhóm "
             "trạng thái); trend (so với kỳ trước liền kề); contractor / object / hopDong (xếp hạng theo sản lượng trong "
             "kỳ, đã lọc theo tham số nếu có); monthlyTrend (6 tháng gần nhất, CHỈ có khi không truyền maDoiTuong / maHopDong).",
        scope="Dùng khi câu hỏi chính là về sản lượng / khối lượng thi công đã nghiệm thu: tổng sản lượng theo kỳ "
              "(hôm nay, tuần, tháng, quý), so sánh kỳ này với kỳ trước, % hoàn thành theo hạng mục và hạng mục nào "
              "còn thiếu, % lũy kế đạt so kế hoạch của một hợp đồng, xếp hạng nhà thầu / hợp đồng / đối tượng theo sản "
              "lượng cao – thấp, trạm nào báo nhiều nhất trong kỳ, hôm nay ai đã báo và tổng bao nhiêu tiền, tổng giá "
              "trị một trạm đã báo và phần đã duyệt / còn chờ. Câu hỏi 'tự tra' (vd 'tháng này tôi báo bao nhiêu') "
              "phải yêu cầu người hỏi nêu rõ tên / mã nhà thầu — MCP chạy không auth, không có danh tính người dùng. "
              "Muốn số lũy kế phải chủ động truyền tuNgay lùi xa vì mặc định chỉ 30 ngày.",
        oos="Không dùng để tra ảnh thi công (số ảnh, ngày chụp), hạng mục bị nghiệm thu không đạt kèm lý do, trạng "
            "thái 'đã khảo sát' riêng, hay danh sách nhà thầu CHƯA báo gì trong tuần (chỉ xếp hạng người CÓ báo). "
            "Không có audit log ai sửa sản lượng, giá trị cũ / mới, thời điểm.",
    ),
    dict(
        name="hopdong_tool",
        desc="Báo cáo hợp đồng, tự thu hẹp theo tham số lọc. Lưu ý canhBaoTienDo là mức 'chậm tiến độ thi công' "
             "tính theo % khối lượng, KHÔNG phải hạn / deadline hợp đồng — hệ thống không có dữ liệu ngày kết thúc hợp đồng.",
        params="maDoiTuong, maHopDong, nhaThauId (ưu tiên hơn tenNhaThau), tenNhaThau, khuVuc, query (từ khóa "
               "tìm theo mã / tên hợp đồng) — tất cả tùy chọn.",
        resp="tongQuan (breakdown theo trạng thái / loại / kiểu hợp đồng, tỷ lệ hoàn thành trung bình — luôn có); "
             "danhSach (chỉ có khi truyền query / nhaThauId / maDoiTuong); thongKeThuHep (chỉ có khi truyền khuVuc / "
             "nhaThauId / maHopDong); canhBaoTienDo (phân loại Xanh ≥ 90% / Vàng 70–90% / Đỏ < 70%, kèm danh sách nhóm "
             "Đỏ — luôn có, lọc theo maHopDong / nhaThauId nếu truyền).",
        scope="Dùng khi câu hỏi chính là về hợp đồng: có bao nhiêu hợp đồng và phân theo trạng thái / loại / kiểu, "
              "tìm một hợp đồng theo mã hoặc tên, hợp đồng của một nhà thầu, tình hình một khu vực, hợp đồng nào chậm "
              "tiến độ / thuộc nhóm Xanh–Vàng–Đỏ, một hợp đồng cụ thể có chậm tiến độ thi công không, % hoàn thành của "
              "ba mảng GCCC / Xây mới / Tư vấn thiết kế, một trạm thuộc hợp đồng nào. So sánh 2 hợp đồng thì gọi tool "
              "2 lần rồi ghép.",
        oos="Không có dữ liệu hạn hợp đồng nên không trả được 'hợp đồng nào sắp hết hạn', 'có kịp hạn không', 'bao "
            "giờ xong', không có dự báo tốc độ / ngày hoàn thành. Không track ngày ký, ngày khởi công, ngày hoàn "
            "thành / nghiệm thu theo tuần. Không có tọa độ trạm, loại cột, chiều cao. Không có breakdown theo bước / "
            "giai đoạn hiện tại của một trạm, không có lịch sử chuyển bước, không có xếp hạng đa khu vực / xếp hạng "
            "tỉnh trong một hợp đồng, không có lý do / người hủy đối tượng.",
    ),
    dict(
        name="doituongton_tool",
        desc="Báo cáo đối tượng tồn (chờ quyết toán / chưa đủ pháp lý / đang vướng mắc), tự thu hẹp theo tham số "
             "lọc. Tên cũ trong tài liệu là tramton_tool.",
        params="maDoiTuong, maHopDong, nhaThauId (ưu tiên hơn tenNhaThau), tenNhaThau, khuVuc, query (từ khóa theo "
               "mã đối tượng / khu vực), tuNgay (ngưỡng ngày cho thieuCapNhat — truyền ngày cách đây N ngày, mặc định 7), "
               "top (số dòng xepHangKhuVuc, mặc định 5, tối đa 20) — tất cả tùy chọn.",
        resp="tongQuan (số lượng và giá trị tồn tách theo choQuyetToan / chuaDuDieuKien / dangVuongMac, kèm phân bố "
             "theo độ tuổi tồn); danhSach (chỉ có khi truyền query / maDoiTuong / nhaThauId / maHopDong); thieuCapNhat "
             "(đối tượng đã khởi công nhưng quá ngưỡng ngày không có sản lượng mới — tối đa 20, luôn có); sanLuongBatThuong "
             "(đối tượng có sản lượng vượt ngưỡng bình quân — tối đa 20, luôn có); xepHangKhuVuc (khuVuc / soDoiTuong / "
             "giaTriTon, top N — luôn có); thieuNhieuDieuKien (đối tượng thiếu ≥ 2 điều kiện trong 3: pháp lý hợp đồng, "
             "không vướng mắc mở, đã có sản lượng hiệu lực — mỗi dòng kèm soDieuKienThieu + dieuKienThieu[], tối đa 20, luôn có).",
        scope="Dùng khi câu hỏi chính là về tồn đọng / chậm quyết toán: tổng giá trị tiền chưa quyết toán tách theo "
              "lý do, giá trị còn tồn của một hợp đồng hoặc một nhà thầu, trạm đủ điều kiện mà chưa thanh toán, trạm "
              "tồn lâu nhất hoặc xong lâu mà chưa quyết toán, trạm khởi công lâu không cập nhật sản lượng, trạm có sản "
              "lượng bất thường, khu vực nào tồn nhiều nhất, trạm nào thiếu từ 2 điều kiện quyết toán trở lên. Câu "
              "hỏi 'tự tra' phải yêu cầu người hỏi nêu rõ tên / mã nhà thầu (MCP chạy không auth).",
        oos="thieuNhieuDieuKien chỉ xét 3 điều kiện tính được bằng SQL (pháp lý hợp đồng / vướng mắc / có sản lượng) — "
            "không đối chiếu checklist biên bản chi tiết. xepHangKhuVuc xếp theo số đối tượng chờ quyết toán, không "
            "theo giá trị quá hạn. Không track ngày quyết toán hoàn tất nên không trả 'tháng này quyết toán được mấy "
            "trạm'. Làm việc ở cấp trạm, không phải cấp hợp đồng.",
    ),
    dict(
        name="vuongmac_tool",
        desc="Báo cáo vướng mắc / sự cố, tự thu hẹp theo tham số lọc.",
        params="maDoiTuong, maHopDong, nhaThauId (ưu tiên hơn tenNhaThau), tenNhaThau, query (từ khóa theo mã / mô "
               "tả vướng mắc), top (số dòng xếp hạng, mặc định 5), tuNgay (kiêm 2 vai: ngưỡng ngày cho quaHan mặc "
               "định 30, và đầu kỳ để tính resolvedTrongKy) — tất cả tùy chọn. LƯU Ý: không có tham số khuVuc để lọc.",
        resp="tongQuan (total / pending / inProgress / resolved / rejected / overdue30Days / countsByKieu, kèm "
             "resolvedTrongKy = số vướng chuyển 'resolved' trong kỳ khi truyền tuNgay — xấp xỉ theo ngay_cap_nhat); "
             "danhSach (chỉ có khi truyền query / nhaThauId / maHopDong); xepHangHopDong (top N hợp đồng nhiều vướng "
             "mắc mở nhất — luôn có); xepHangKhuVuc (top N khu vực nhiều vướng mắc mở nhất, qua đối tượng của vướng "
             "mắc — luôn có); quaHan (vướng mắc mở quá ngưỡng ngày, kèm người đang giữ việc — tối đa 20, luôn có).",
        scope="Dùng khi câu hỏi chính là về vướng mắc / sự cố: đang có bao nhiêu vướng mắc mở và tỷ lệ trên tổng, "
              "phân theo loại (mặt bằng, kỹ thuật, pháp lý, tài chính) và loại nào nhiều nhất, chi tiết vướng mắc của "
              "một trạm, vướng mở quá N ngày kèm người giữ việc, vướng mở từ trước mà chưa đóng, hợp đồng nào / khu "
              "vực nào nhiều vướng mắc nhất, tháng này gỡ được mấy vướng (truyền tuNgay = đầu kỳ), lý do một đối tượng "
              "bị chặn không làm tiếp được (thường ghép thêm phancong_tool).",
        oos="Không có mức 'cấp thiết' và không có 'người nhận' nên không trả 'vướng nào gấp mà chưa ai nhận'. Không "
            "có 'hạn xử lý dự kiến' — chỉ tính quá hạn theo số ngày kể từ ngày mở. resolvedTrongKy chỉ xấp xỉ theo "
            "ngay_cap_nhat (không có cột resolved_at riêng). MCP chạy không auth nên không có 'người dùng hiện tại' "
            "— câu 'vướng nào tôi phải xử lý' phải hỏi lại tên người xử lý.",
    ),
    dict(
        name="phancong_tool",
        desc="Báo cáo phân công công việc, tự thu hẹp theo tham số lọc. Nếu câu hỏi còn hỏi thêm về tiến độ / "
             "trạng thái của hợp đồng liên quan tới kết quả, phải gọi tiếp hopdong_tool với mã hợp đồng đó trước khi trả lời.",
        params="maVung (mã vùng quản lý, không phải mã đối tượng), nhaThauId (ưu tiên hơn tenNhaThau), tenNhaThau, "
               "canBoId (ưu tiên hơn tenCanBo), tenCanBo, query (từ khóa theo nhà thầu / giai đoạn / mã vùng), "
               "maHopDong + khuVuc (lọc chuaPhanCong), top (số dòng xepHangNhaThau, mặc định 5, tối đa 20) — tất cả tùy chọn.",
        resp="tongQuan (tongPhanCong, tongHoatDong, theoKhuVuc, theoTinhThanh — luôn có); danhSach (chỉ có khi truyền "
             "query / nhaThauId / tenNhaThau / maVung); theoCanBo (phân công của một cán bộ, mỗi dòng kèm cờ coVuongMacMo "
             "— chỉ có khi truyền canBoId / tenCanBo); chuaPhanCong (đối tượng có nha_thau_id NULL, lọc theo maHopDong / "
             "khuVuc — tối đa 30, luôn có); xepHangNhaThau (tenNhaThau / soDoiTuong / soDangVuongMac / tongSanLuongHieuLuc, "
             "nguồn là hop_dong_doi_tuong.nha_thau_id — top N, luôn có).",
        scope="Dùng khi câu hỏi chính là về ai đang phụ trách việc gì: một trạm ai làm, một cán bộ / nhà thầu đang "
              "được giao những trạm nào, phân công tổng quan theo khu vực / tỉnh thành, một cán bộ đang ôm mấy trạm "
              "đang vướng (ghép với vuongmac_tool), đối tượng / trạm nào chưa giao nhà thầu, nhà thầu nào ôm nhiều "
              "việc nhất hoặc đang vướng nhiều nhất. Câu hỏi 'tự tra' phải yêu cầu người hỏi nêu rõ tên / mã cán "
              "bộ hoặc nhà thầu (MCP chạy không auth, không có danh tính người dùng).",
        oos="chuaPhanCong dựa trên hop_dong_doi_tuong.nha_thau_id (nguồn chân lý), không phải bảng phan_cong. "
            "xepHangNhaThau xếp theo số đối tượng phụ trách, không phải theo % tiến độ. Không có lịch sử phân công nên "
            "không trả 'trạm này trước giao cho ai'. Không có khái niệm 'đến hạn trong tuần'. Không track hợp đồng "
            "thầu phụ. Phải từ chối các câu về lương / nghỉ phép / chấm công / hồ sơ nhân sự.",
    ),
    dict(
        name="bienban_tool",
        desc="Báo cáo biên bản / hồ sơ hợp đồng, tự thu hẹp theo tham số lọc. Không truyền gì thì trả toàn hệ thống, "
             "giới hạn 20 dòng mỗi mục.",
        params="khuVuc, maHopDong, nhaThauId (ưu tiên hơn tenNhaThau), tenNhaThau, trangThai (lọc theoTrangThai: "
               "cho_duyet | da_duyet | tu_choi) — tất cả tùy chọn. LƯU Ý: không có tham số maDoiTuong; muốn tra theo "
               "một trạm phải truyền maHopDong của trạm đó.",
        resp="tongQuan (total + choDuyet / daDuyet / tuChoi + countsByLoai theo loại biên bản — luôn có); theoTrangThai "
             "(danh sách biên bản, lọc theo trangThai nếu truyền, mỗi dòng kèm lyDoTuChoi + nguoiPheDuyetTen + "
             "ngayPheDuyet — tối đa 20, luôn có); thieuKhaoSat (trạm / hợp đồng chưa có báo cáo khảo sát đã duyệt — "
             "KẾT QUẢ XẤP XỈ Ở CẤP HỢP ĐỒNG); thieuHoSo (hợp đồng còn thiếu biên bản bắt buộc theo checklist, kèm "
             "tên loại còn thiếu). Tất cả luôn có, tối đa 20 dòng mỗi mục.",
        scope="Dùng khi câu hỏi chính là về biên bản / hồ sơ: có bao nhiêu biên bản và phân theo trạng thái duyệt / "
              "theo loại, biên bản nào đang chờ duyệt hoặc bị từ chối và vì sao (truyền trangThai), trạm nào chưa "
              "khảo sát ở một khu vực hoặc của một nhà thầu, một hợp đồng còn thiếu hồ sơ gì theo checklist, một trạm "
              "còn thiếu biên bản gì (lọc theo maHopDong của trạm). Câu hỏi 'tự tra' phải yêu cầu người hỏi nêu rõ "
              "tên / mã nhà thầu (MCP chạy không auth).",
        oos="Biên bản lưu theo hợp đồng, không theo từng đối tượng — lọc theo trạm chỉ gián tiếp qua maHopDong. Không "
            "trả danh sách biên bản ĐÃ xuất theo loại một cách riêng (chỉ có theoTrangThai). Không track ngày khảo "
            "sát. Không đối chiếu biên bản đã ký với điều kiện thanh toán đã cập nhật.",
    ),
    dict(
        name="nguonviec_tool",
        desc="Báo cáo nguồn việc — danh mục hợp đồng theo trung tâm: giá trị hợp đồng, sản xuất / doanh thu theo "
             "kỳ, trạng thái pháp lý, số đội khảo sát / thi công. Tự thu hẹp theo tham số lọc.",
        params="khuVuc (mã trung tâm, ví dụ TTKV2 — mặc định TTKV2 nếu bỏ trống), nhaThauId (ưu tiên hơn tenNhaThau), "
               "tenNhaThau, trangThai (trạng thái pháp lý, ví dụ vuong_phap_ly), tuNgay, denNgay, query (từ khóa theo "
               "mã / tên hợp đồng), top (số dòng xếp hạng rủi ro, mặc định 5, tối đa 10) — tất cả tùy chọn.",
        resp="summary (giaTriHD, sxTong, dtTong, dtConSL, chuaKhaThi, slConHD — đơn vị tỷ đồng); tabCounts (all / "
             "active / nearly); danhSach (tối đa 30 dòng, mỗi dòng gồm mã hợp đồng, chương trình, loại công việc, giai "
             "đoạn pháp lý, giá trị, sản xuất / doanh thu theo kỳ, nhà thầu, số đội KS–TC); xepHangRuiRo (top N hợp "
             "đồng theo điểm rủi ro heuristic = vướng mắc mở + tiến độ sản lượng chậm + đang vướng pháp lý, KHÔNG phải "
             "dự báo KPI thực — luôn có).",
        scope="Dùng khi câu hỏi chính là về nguồn việc / tình hình một trung tâm: một trung tâm có gì (giá trị, sản "
              "xuất, doanh thu), hợp đồng nào đang vướng pháp lý / rủi ro, nguồn việc của một nhà thầu, khu vực còn "
              "bao nhiêu việc chưa làm, hợp đồng chưa ký mà đã làm (so phapLyStage với sxTong), chỗ nào báo sản lượng "
              "mà chưa lên doanh thu (so sxTong với dtTong).",
        oos="Chỉ query một trung tâm mỗi lần nên không so sánh trực tiếp nhiều trung tâm ('quý này trung tâm nào làm "
            "nhiều nhất'). xepHangRuiRo là heuristic, không phải dự báo KPI thật. Không có dữ liệu 'kế hoạch triển "
            "khai' để đối chiếu chênh lệch kế hoạch với thực tế. Không có xếp hạng trung tâm hay danh sách nguồn việc "
            "sắp hết giá trị.",
    ),
    dict(
        name="nhathau_tool",
        desc="Hồ sơ tổng hợp một nhà thầu — gộp sản lượng, hợp đồng, trạm tồn, vướng mắc, phân công của nhà thầu đó "
             "trong một lần gọi, thay vì gọi lần lượt từng tool với cùng nhaThauId.",
        params="nhaThauId (ưu tiên) hoặc tenNhaThau — BẮT BUỘC phải có một trong hai; tuNgay, denNgay tùy chọn (áp "
               "cho phần sản lượng). Không truyền nhà thầu thì trả dữ liệu toàn hệ thống, vô nghĩa.",
        resp="nhaThauId, tenNhaThau, sanLuong (cấu trúc như sanluong_tool), hopDong (như hopdong_tool), tramTon (như "
             "doituongton_tool), vuongMac (như vuongmac_tool), phanCong (như phancong_tool) — mỗi mục giữ nguyên cấu "
             "trúc kết quả của tool domain tương ứng khi không lọc.",
        scope="Dùng khi câu hỏi cần bức tranh chung của MỘT nhà thầu cụ thể, phải đối chiếu nhiều mảng cùng lúc: nhà "
              "thầu X đang làm mấy trạm và tiến độ ra sao, còn tồn mấy trạm, đang vướng gì, tình hình chung thế nào.",
        oos="Không xếp hạng / so sánh nhiều nhà thầu với nhau. Không có breakdown địa bàn theo tỉnh của nhà thầu. "
            "Không track hợp đồng thầu phụ. Bắt buộc xác định được nhà thầu, nếu không thì kết quả vô nghĩa.",
    ),
    dict(
        name="nganho_tool",
        desc="Báo cáo kiểm soát ngân sách hợp đồng — đối soát giá trị hợp đồng với thành tiền thi công đã ghi nhận. "
             "Wrapper mỏng trên module Volume. Khác với tiến độ khối lượng (hopdong_tool) và sản lượng nghiệm thu "
             "(sanluong_tool).",
        params="maHopDong (tùy chọn — có thì trả thêm chiTietHopDong + theoKhuVucTinh), query (từ khóa mã / tên hợp "
               "đồng cho phần tongQuan). KHÔNG có tham số khuVuc / tuNgay / denNgay.",
        resp="tongQuan (giaTriHopDong, tongThanhTienThiCong, chenhLech, tyLeSuDung, soHopDongVuotNguong / CanhBao / "
             "Thieu / Thua / CanBang, tổng quyết toán — luôn có); chiTietHopDong (tyLeSuDung + breakdown theo nhóm "
             "hạng mục — chỉ khi truyền maHopDong); theoKhuVucTinh (duLieu theo khu vực + canhBaoThieu / canhBaoThua "
             "theo tỉnh — chỉ khi truyền maHopDong).",
        scope="Dùng khi câu hỏi chính là về ngân sách / chi phí / mức tiêu thụ giá trị hợp đồng: hợp đồng nào vượt "
              "ngân sách / thừa / thiếu, một hợp đồng tiêu hết bao nhiêu %, bình quân mỗi trạm bao nhiêu tiền, trong "
              "một hợp đồng trạm nào / tỉnh nào chênh nhiều nhất, tỉnh nào thừa / thiếu sản lượng.",
        oos="Không tra hệ số cảnh báo đang cấu hình (config hệ thống). Không giải thích logic ('sao hợp đồng mới tạo "
            "đã báo vượt ngưỡng'). Không có audit log điều chỉnh sản lượng. Chỉ nhận maHopDong, không lọc theo khu "
            "vực hay khoảng thời gian ở mức tool.",
    ),
    dict(
        name="system_overview_tool",
        desc="Tổng quan gộp cả 7 module (hợp đồng, sản lượng, phân công, trạm tồn, vướng mắc, biên bản, nguồn việc) "
             "trong một lần gọi duy nhất. Dùng tool này một lần thay cho việc gọi lần lượt từng tool khi câu hỏi rõ "
             "ràng cần nhiều module.",
        params="tuNgay, denNgay — tùy chọn, chỉ áp cho phần sản lượng. Không nhận bộ lọc theo nhà thầu / hợp đồng / trạm.",
        resp="Một object gồm 7 field hopDong, sanLuong, phanCong, tramTon, vuongMac, bienBan, nguonViec — mỗi field "
             "có cấu trúc giống hệt kết quả tool tương ứng khi không truyền bộ lọc (chỉ gồm các mục 'luôn có sẵn' của "
             "từng tool).",
        scope="Dùng khi câu hỏi cần đối chiếu số liệu tổng hợp từ nhiều module cùng lúc và không khoanh vùng theo "
              "một nhà thầu / hợp đồng / trạm cụ thể — ví dụ 'hôm nay có gì bất thường không', 'tổng quan hệ thống', "
              "'tình hình chung thế nào'.",
        oos="Không dùng khi câu hỏi chỉ cần một module, hoặc cần lọc theo nhà thầu / hợp đồng / trạm cụ thể — khi đó "
            "dùng thẳng tool của module đó, hoặc nhathau_tool nếu hỏi về một nhà thầu.",
    ),
]


def load_examples():
    df = pd.read_excel(XLSX, sheet_name="Câu hỏi")
    pat = re.compile(r"[a-z_]+_tool|thoigian_hientai")
    known = {t["name"] for t in TOOLS}
    ex, rej, global_oos = {}, {}, []
    for _, r in df.iterrows():
        q = str(r["Câu hỏi"]).strip()
        raw = str(r["Tool cần gọi"])
        if not q or q == "nan":
            continue
        toks = {ALIAS.get(t, t) for t in pat.findall(raw)}
        toks = {t for t in toks if t in known}
        is_oos = raw.strip().startswith("—")
        for t in toks:
            (rej if is_oos else ex).setdefault(t, []).append(q)
        if is_oos and not toks:
            global_oos.append(f"{q}  [{raw.strip()}]")
    return ex, rej, global_oos


def main():
    ex, rej, global_oos = load_examples()

    rows = []
    for t in TOOLS:
        oos_txt = t["oos"]
        if rej.get(t["name"]):
            oos_txt += "\n\nCâu hỏi trong sheet 'Câu hỏi' bị đánh ngoài phạm vi tool này:\n" + \
                       "\n".join(f"- {q}" for q in rej[t["name"]])
        rows.append({
            "TOOL_NAME": t["name"],
            "TOOL_DESCRIPTION": t["desc"],
            "TOOL_PARAMS": t["params"],
            "TOOL_RESPONSE": t["resp"],
            "QUERY_SCOPE": t["scope"],
            "EXAMPLE_QUERIES": "\n".join(f"- {q}" for q in ex.get(t["name"], [])),
            "OUT_OF_SCOPE": oos_txt,
        })

    rows.append({
        "TOOL_NAME": "(NONE — ngoài phạm vi mọi tool)",
        "TOOL_DESCRIPTION": "Câu hỏi cần dữ liệu hoặc tính năng chưa tool nào đáp ứng. Chatbot nên từ chối và nói rõ "
                            "thiếu gì, không được đoán bừa.",
        "TOOL_PARAMS": "", "TOOL_RESPONSE": "", "QUERY_SCOPE": "", "EXAMPLE_QUERIES": "",
        "OUT_OF_SCOPE": "\n".join(f"- {q}" for q in global_oos),
    })

    cols = ["TOOL_NAME", "TOOL_DESCRIPTION", "TOOL_PARAMS", "TOOL_RESPONSE",
            "QUERY_SCOPE", "EXAMPLE_QUERIES", "OUT_OF_SCOPE"]
    new = pd.DataFrame(rows, columns=cols)

    book = pd.read_excel(XLSX, sheet_name=None)
    with pd.ExcelWriter(XLSX, engine="openpyxl") as w:
        for name, d in book.items():
            if name != "Tools":
                d.to_excel(w, sheet_name=name, index=False)
        new.to_excel(w, sheet_name="Tools", index=False)

        ws = w.sheets["Tools"]
        from openpyxl.styles import Alignment, Font
        for c, wd in {"A": 20, "B": 60, "C": 50, "D": 62, "E": 70, "F": 46, "G": 72}.items():
            ws.column_dimensions[c].width = wd
        for row in ws.iter_rows(min_row=1):
            for cell in row:
                cell.alignment = Alignment(wrap_text=True, vertical="top")
        for cell in ws[1]:
            cell.font = Font(bold=True)
        ws.freeze_panes = "A2"

    print(f"Đã ghi sheet 'Tools': {len(TOOLS)} tool nghiệp vụ + 1 dòng NONE.")
    print(f"Câu hỏi map vào tool: {sum(len(v) for v in ex.values())} | "
          f"bị đánh ngoài phạm vi 1 tool: {sum(len(v) for v in rej.values())} | "
          f"ngoài phạm vi mọi tool: {len(global_oos)}")


if __name__ == "__main__":
    main()
