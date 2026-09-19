---
document_id: vtk-user-guide
document_version: 2026-09-19
document_type: user_guide
title: Hướng dẫn sử dụng VTK
product: VTK
language: vi
audience:
  - end_user
  - chatbot
status: published
source_of_truth: true
chunk_strategy: h2_h3_sections
default_access_scope: authenticated
---

# Hướng dẫn sử dụng VTK

## 1. Thông tin chung

- **Tên ứng dụng:** VTK — Điều hành Sản xuất & Quản lý HĐ Tư vấn BTS.
- **Mục đích:** theo dõi tiến độ hợp đồng, sản lượng thi công, thanh toán, nguồn việc, phân công, đối tượng tồn và vướng mắc.
- **Đối tượng sử dụng:** cán bộ quản lý hợp đồng, cán bộ sản lượng, cán bộ phân công, cán bộ quản trị và nhà thầu.
- **Nguyên tắc hiển thị:** người dùng chỉ nhìn thấy các menu phù hợp với quyền được cấp. Không nhìn thấy menu không có nghĩa là dữ liệu không tồn tại; có thể tài khoản chưa được cấp quyền.

## 2. Đăng nhập và phiên làm việc

**Router:** [Đăng nhập](/login)

1. Mở ứng dụng VTK.
2. Nhập **tên đăng nhập** và **mật khẩu**.
3. Chọn **Đăng nhập**.
4. Sau khi đăng nhập thành công, ứng dụng mở trang **Dashboard Sản lượng & Thanh toán**.

Nếu phiên đăng nhập hết hạn, ứng dụng chuyển về trang Đăng nhập. Người dùng đăng nhập lại để tiếp tục. Nếu hệ thống yêu cầu đổi mật khẩu hoặc mật khẩu sắp hết hạn, hãy thực hiện đổi mật khẩu trước khi sử dụng các chức năng khác.

Để kết thúc phiên, mở menu tài khoản và chọn **Đăng xuất**. Không chia sẻ tài khoản hoặc token đăng nhập cho người khác.

## 3. Dashboard Sản lượng & Thanh toán

**Router:** [Dashboard Sản lượng & Thanh toán](/dashboard)

### Mục đích

Dashboard cung cấp cái nhìn tổng quan về sản lượng, thanh toán và các chỉ số điều hành.

### Cách sử dụng

1. Mở **Tổng quan & Báo cáo > Dashboard Sản lượng & Thanh toán**.
2. Xem các thẻ tổng quan và biểu đồ.
3. Chọn bộ lọc nếu cần xem theo thời gian, loại hợp đồng, khu vực hoặc phạm vi dữ liệu.
4. Đọc các cảnh báo sản lượng bất thường và chi tiết trung tâm để xác định nội dung cần xử lý.

## 4. Tiến độ hợp đồng

**Router:** [Danh sách tiến độ hợp đồng](/stations) · [Tạo hợp đồng](/stations/create) · [Import Excel](/stations/import)

### Mục đích

Quản lý danh sách hợp đồng hoặc đối tượng thuộc hợp đồng, theo dõi trạng thái và tiến độ thực hiện.

### Thao tác chính

- Chọn **Quản lý Hợp đồng & Phân công > Tiến độ hợp đồng** để xem danh sách.
- Dùng tìm kiếm và bộ lọc để tìm hợp đồng, mã đối tượng, nhà thầu hoặc phạm vi cần theo dõi.
- Chọn **Tạo hợp đồng** để nhập hợp đồng mới.
- Chọn một dòng để **Chỉnh sửa hợp đồng**.
- Route chỉnh sửa có dạng `/stations/{id}/edit`, ví dụ [chỉnh sửa hợp đồng mẫu](/stations/00000000-0000-0000-0000-000000000000/edit).
- Chọn **Import Excel** để nhập dữ liệu theo file Excel và mapping đã cấu hình.
- Mở chi tiết để xem tiến độ, trạng thái, sản lượng và các thông tin liên quan.

### Lưu ý nghiệp vụ

- Nhóm cảnh báo tiến độ Xanh, Vàng, Đỏ phản ánh mức hoàn thành khối lượng thi công: Xanh từ 90% trở lên, Vàng từ 70% đến dưới 90%, Đỏ dưới 70%.
- Cảnh báo tiến độ không phải là cảnh báo ngày hết hạn hợp đồng. Hệ thống không dùng chức năng này để khẳng định một hợp đồng có kịp deadline hay không.

## 5. Quản lý nguồn việc

**Router:** [Quản lý Nguồn việc](/work-sources)

### Mục đích

Theo dõi nguồn việc theo trung tâm hoặc khu vực, giá trị hợp đồng, sản xuất, doanh thu và trạng thái pháp lý.

### Cách sử dụng

1. Mở **Quản lý Hợp đồng & Phân công > Quản lý Nguồn việc**.
2. Chọn trung tâm hoặc khu vực cần xem.
3. Lọc theo nhà thầu, trạng thái pháp lý hoặc từ khóa hợp đồng.
4. Xem danh sách nguồn việc và nhóm hợp đồng có rủi ro cao.

## 6. Quản lý phân công

**Router:** [Quản lý Phân công](/stations/assignment)

### Mục đích

Theo dõi đối tượng đã giao cho nhà thầu hoặc cán bộ, đối tượng chưa phân công và khối lượng công việc của từng đơn vị.

### Cách sử dụng

1. Mở **Quản lý Hợp đồng & Phân công > Quản lý Phân công**.
2. Tìm theo nhà thầu, cán bộ, mã vùng, hợp đồng hoặc từ khóa.
3. Kiểm tra danh sách phân công và trạng thái hoạt động.
4. Xem danh sách đối tượng chưa phân công để xử lý.

## 7. Quản lý đối tượng tồn

**Router:** [Quản lý ĐT tồn](/stations/surplus)

### Mục đích

Theo dõi đối tượng chờ quyết toán, chưa đủ điều kiện pháp lý hoặc đang có vướng mắc.

### Cách sử dụng

1. Mở **Quản lý Hợp đồng & Phân công > Quản lý ĐT tồn**.
2. Xem tổng quan số lượng và giá trị tồn theo nguyên nhân.
3. Lọc theo mã đối tượng, hợp đồng, nhà thầu hoặc khu vực.
4. Ưu tiên xử lý các đối tượng tồn lâu, thiếu nhiều điều kiện hoặc lâu không cập nhật sản lượng.

## 8. Ghi nhận vướng mắc

**Router:** [Ghi nhận Vướng mắc](/issues)

### Mục đích

Ghi nhận, theo dõi và xử lý các vướng mắc về mặt bằng, kỹ thuật, pháp lý, tài chính hoặc các nguyên nhân khác.

### Cách sử dụng

1. Mở **Tiến độ & Vướng mắc > Ghi nhận Vướng mắc**.
2. Chọn tạo vướng mắc mới.
3. Nhập đối tượng hoặc hợp đồng liên quan, loại vướng mắc, mô tả và thông tin xử lý.
4. Lưu bản ghi.
5. Cập nhật trạng thái khi vướng mắc được tiếp nhận, xử lý hoặc giải quyết.
6. Dùng bộ lọc để xem vướng mắc đang mở, quá hạn hoặc theo loại.

## 9. Sản lượng Thi công

**Router:** [Sản lượng Thi công](/construction-output)

### Mục đích

Nhập và theo dõi sản lượng thi công đã thực hiện, sản lượng theo kỳ, theo hợp đồng, nhà thầu hoặc đối tượng.

### Cách sử dụng

1. Mở **Tiến độ & Vướng mắc > Sản lượng Thi công**.
2. Chọn khoảng thời gian cần xem.
3. Lọc theo hợp đồng, đối tượng, nhà thầu hoặc khu vực.
4. Nhập hoặc kiểm tra sản lượng theo quy trình được cấp quyền.
5. Kiểm tra các bản ghi bất thường trước khi xác nhận.

### Lưu ý

- Nếu không chọn khoảng thời gian, báo cáo sản lượng thường sử dụng khoảng mặc định do hệ thống quy định.
- Số liệu lũy kế cần chọn khoảng thời gian đủ dài; không nên suy ra lũy kế từ báo cáo chỉ hiển thị một kỳ ngắn.
- Câu hỏi “tôi đã báo bao nhiêu” cần cung cấp rõ tên hoặc mã nhà thầu/cán bộ vì trợ lý dữ liệu không tự suy ra danh tính người hỏi trong mọi ngữ cảnh.

## 10. Kiểm soát Volume Hợp đồng

**Router:** [Kiểm soát Volume Hợp đồng](/volume)

### Mục đích

Đối soát giá trị hợp đồng với thành tiền thi công đã ghi nhận và nhận diện hợp đồng có mức sử dụng vượt hoặc thiếu so với giá trị hợp đồng.

### Cách sử dụng

1. Mở **Hồ sơ & Hợp đồng > Kiểm soát Volume Hợp đồng**.
2. Xem tổng quan mức sử dụng volume.
3. Tìm theo mã hoặc tên hợp đồng.
4. Mở chi tiết để xem chênh lệch, tỷ lệ sử dụng và phân bổ theo nhóm hạng mục/khu vực nếu có.

## 11. Hồ sơ, lưu trữ và Archive hợp đồng

**Router:** [Lưu trữ & Archive HĐ](/archive)

Mở **Quản trị Hệ thống > Lưu trữ & Archive HĐ** để tra cứu hoặc quản lý hồ sơ hợp đồng đã lưu trữ theo quyền được cấp. Trước khi archive, cần kiểm tra trạng thái hợp đồng và hồ sơ liên quan theo quy trình nội bộ.

## 12. Quản trị và cấu hình hệ thống

Các chức năng này thường dành cho quản trị viên hoặc người được cấp quyền tương ứng:

- **Quản lý Tỉnh:** quản lý danh mục tỉnh/thành tại [Quản lý Tỉnh](/resources/provinces).
- **Quản lý Khu vực:** quản lý danh mục khu vực/trung tâm tại [Quản lý Khu vực](/resources/regions).
- **Phân quyền Người dùng:** quản lý người dùng và quyền truy cập tại [Phân quyền Người dùng](/authorization).
- **Đối tượng quản lý:** xem danh sách tại [Đối tượng quản lý](/config/managed-objects), thêm tại [Thêm đối tượng quản lý](/config/managed-objects/create), sửa tại `/config/managed-objects/{id}/edit`.
- **Thuộc tính HĐ:** cấu hình thuộc tính hợp đồng tại [Thuộc tính HĐ](/config/contract-attributes).
- **Luồng trạng thái:** cấu hình các trạng thái và luồng chuyển trạng thái tại [Luồng trạng thái](/config/contract-statuses).
- **Kiểu hợp đồng:** quản lý loại/kiểu hợp đồng tại [Kiểu hợp đồng](/config/contract-types).
- **Liên kết HĐ:** cấu hình quan hệ giữa các hợp đồng tại [Liên kết HĐ](/config/contract-links).
- **Cấu hình Mapping Excel:** ánh xạ cột Excel vào trường dữ liệu tại [Cấu hình Mapping Excel](/config/excel-mapping).

Không tự ý sửa danh mục, luồng trạng thái hoặc mapping Excel khi chưa xác định rõ phạm vi ảnh hưởng. Thay đổi cấu hình có thể làm thay đổi cách nhập và hiển thị dữ liệu của các bộ phận khác.

## 13. Trợ lý AI

**Router:** [Trợ lý AI](/ai-assistant) · Route hội thoại cụ thể có dạng `/ai-assistant/{conversationId}`.

### Mục đích

Trợ lý AI hỗ trợ hỏi đáp trên dữ liệu nghiệp vụ và có thể trả về bảng, số liệu hoặc biểu đồ khi dữ liệu phù hợp.

### Cách đặt câu hỏi hiệu quả

Nên nêu đủ bốn thành phần:

1. **Đối tượng:** hợp đồng, đối tượng/trạm, nhà thầu, khu vực hoặc cán bộ.
2. **Chỉ tiêu:** sản lượng, tiến độ, volume, vướng mắc, phân công hoặc hồ sơ.
3. **Phạm vi thời gian:** hôm nay, tháng này, quý này hoặc khoảng ngày cụ thể.
4. **Cách phân tích:** tổng quan, so sánh, xếp hạng, danh sách chi tiết hoặc cảnh báo.

### Cách làm việc với hội thoại

- Tạo hội thoại mới cho một chủ đề lớn khác.
- Câu hỏi tiếp theo có thể tham chiếu kết quả trước, ví dụ: “Lọc riêng khu vực TTKV2”.
- Khi cần kiểm chứng, yêu cầu trợ lý nêu mã hợp đồng, mã đối tượng, kỳ dữ liệu và nguồn chỉ tiêu.
- Không xem câu trả lời AI là phê duyệt nghiệp vụ. Người dùng cần kiểm tra lại bản ghi gốc trước khi quyết định.

### Giới hạn cần biết

- Trợ lý chỉ trả lời dựa trên dữ liệu và chỉ tiêu mà hệ thống cung cấp.
- Không nên yêu cầu suy đoán ngày hoàn thành hoặc ngày hết hạn hợp đồng nếu dữ liệu không có ngày deadline.
- Không suy ra thông tin nhân sự như lương, nghỉ phép, chấm công khi hệ thống không cung cấp dữ liệu đó.
- Kết quả “rủi ro” hoặc “bất thường” có thể là chỉ báo theo quy tắc; cần kiểm tra chi tiết trước khi xử lý.
- Khi câu hỏi thiếu mã/tên nhà thầu, hợp đồng, đối tượng hoặc khoảng thời gian, hãy bổ sung thông tin để kết quả chính xác hơn.

## 14. Từ điển thuật ngữ cho người dùng và chatbot

| Thuật ngữ | Từ đồng nghĩa thường gặp | Ý nghĩa trong ứng dụng |
|---|---|---|
| Hợp đồng | HĐ, contract | Hồ sơ/quản lý hợp đồng tư vấn BTS |
| Đối tượng | ĐT, trạm | Đơn vị công việc thuộc hợp đồng |
| ĐT tồn | Trạm tồn, đối tượng tồn | Đối tượng đang chờ quyết toán, thiếu điều kiện hoặc vướng mắc |
| Sản lượng | Khối lượng thi công, volume thi công | Giá trị/khối lượng đã ghi nhận theo kỳ |
| Vướng mắc | Sự cố, issue, trở ngại | Nội dung cản trở việc triển khai hoặc hoàn tất công việc |
| Nguồn việc | Backlog, danh mục việc | Tập hợp công việc/hợp đồng theo trung tâm hoặc khu vực |
| Phân công | Giao việc, assignment | Quan hệ phụ trách giữa đối tượng và nhà thầu/cán bộ |
| Volume hợp đồng | Giá trị hợp đồng, ngân sách hợp đồng | Đối soát giá trị hợp đồng với thành tiền thi công |
| Hồ sơ/biên bản | Tài liệu hợp đồng | Các báo cáo, biên bản và tài liệu cần theo dõi |

audience: end_user
## 15. Quy chuẩn dữ liệu RAG

Đây là file nguồn chuẩn cho knowledge base hướng dẫn sử dụng VTK. File được nạp theo section Markdown, không nạp toàn bộ tài liệu thành một vector duy nhất.

### Quy tắc chunk

- Ưu tiên một section `##` cho một chunk nghiệp vụ.
- Nếu section dài hơn giới hạn token của pipeline, tách tiếp theo heading `###`.
- Mỗi chunk phải giữ được tiêu đề nghiệp vụ, router, mục đích, quy trình và giới hạn liên quan.
- Không nối hai nghiệp vụ không liên quan vào cùng một chunk.
- Không đưa số liệu realtime, token, API key, mật khẩu hoặc dữ liệu cá nhân thật vào tài liệu.

### Metadata tối thiểu

```yaml
document_id: vtk-user-guide
document_version: 2026-09-19
chunk_id: vtk-user-guide-contract-create
title: Quy trình nghiệp vụ: tạo hợp đồng mới
module: contract
intent: how_to
router: /stations/create
related_routers:
	- /stations
language: vi
access_scope: authenticated
source: docs/huong-dan-su-dung-vtk-rag.md
content_hash: sha256:<generated-by-ingestion>
```

### Phân loại nội dung

- `how_to`: hướng dẫn thao tác hoặc quy trình.
- `definition`: giải thích thuật ngữ, trạng thái hoặc khái niệm.
- `navigation`: router và vị trí màn hình.
- `permission`: quyền truy cập và giới hạn vai trò.
- `limitation`: dữ liệu hệ thống không cung cấp hoặc không được suy diễn.

### Ranh giới giữa RAG và MCP

- Dùng RAG cho hướng dẫn, quy trình, định nghĩa, router và quyền.
- Dùng MCP/backend cho số lượng hợp đồng, sản lượng, vướng mắc, phân công và các số liệu thay đổi theo thời gian.
- Với câu hỏi kết hợp, chatbot dùng MCP lấy số liệu rồi dùng RAG để giải thích quy trình hoặc màn hình xử lý.

Không trộn số liệu realtime vào file này. Khi tài liệu thay đổi, phải tăng `document_version` và chạy lại ingestion theo manifest.

## 16. Quy trình nghiệp vụ: tra cứu một hợp đồng

**Router:** [Tiến độ hợp đồng](/stations)

Quy trình này dùng khi người dùng cần kiểm tra nhanh một hợp đồng cụ thể theo mã, tên, nhà thầu hoặc đối tượng thuộc hợp đồng.

1. Mở router **Tiến độ hợp đồng**.
2. Nhập mã hợp đồng hoặc một phần tên hợp đồng vào ô tìm kiếm.
3. Nếu có nhiều kết quả, lọc tiếp theo trạng thái, loại hợp đồng, khu vực hoặc nhà thầu.
4. Chọn dòng hợp đồng cần xem để mở màn hình chi tiết.
5. Đối chiếu trạng thái hợp đồng, danh sách đối tượng, tiến độ hoàn thành, sản lượng, vướng mắc và thông tin phân công.
6. Nếu phát hiện sai thông tin và có quyền chỉnh sửa, mở route `/stations/{id}/edit`, cập nhật trường cần thiết rồi lưu.

Khi hỏi chatbot, nên cung cấp mã hợp đồng nếu có. Câu hỏi “Hợp đồng ABC đang thế nào?” có thể cần hỏi lại nếu có nhiều hợp đồng trùng tên. Câu hỏi “Hợp đồng ABC có kịp hạn không?” không thể kết luận nếu dữ liệu không có ngày hết hạn hoặc tốc độ dự báo.

## 17. Quy trình nghiệp vụ: tạo hợp đồng mới

**Router:** [Tạo hợp đồng](/stations/create)

Tạo hợp đồng là bước khởi tạo hồ sơ để hệ thống có thể theo dõi đối tượng, tiến độ, sản lượng, phân công và hồ sơ liên quan.

Trước khi tạo, người dùng cần chuẩn bị mã hợp đồng, tên/chương trình, loại và kiểu hợp đồng, khu vực, nhà thầu, các thuộc tính bắt buộc và danh sách đối tượng nếu quy trình yêu cầu. Không tạo bản ghi trùng mã hợp đồng.

1. Mở router **Tạo hợp đồng**.
2. Nhập các trường thông tin bắt buộc.
3. Chọn loại hợp đồng và kiểu hợp đồng từ danh mục đã cấu hình.
4. Chọn khu vực, tỉnh/thành và các thông tin liên quan.
5. Kiểm tra lại mã, tên, đơn vị phụ trách và giá trị hợp đồng.
6. Chọn lưu và kiểm tra thông báo kết quả.
7. Mở lại hợp đồng trong [Tiến độ hợp đồng](/stations) để xác nhận dữ liệu đã được tạo.

Nếu không thấy loại hợp đồng, trạng thái hoặc thuộc tính cần chọn, người dùng cần liên hệ quản trị viên kiểm tra các router [Kiểu hợp đồng](/config/contract-types), [Thuộc tính HĐ](/config/contract-attributes) và [Luồng trạng thái](/config/contract-statuses).

## 18. Quy trình nghiệp vụ: import dữ liệu Excel

**Router:** [Import Excel](/stations/import) · [Cấu hình Mapping Excel](/config/excel-mapping)

Import Excel phù hợp khi cần nạp nhiều hợp đồng hoặc nhiều đối tượng trong một lần. File cần đúng mẫu và các cột phải được ánh xạ đúng với trường dữ liệu của hệ thống.

1. Mở [Cấu hình Mapping Excel](/config/excel-mapping) để kiểm tra mapping hiện hành nếu bạn là người quản trị.
2. Chuẩn bị file Excel với tên cột, kiểu dữ liệu và giá trị danh mục đúng quy định.
3. Mở router **Import Excel**.
4. Chọn file cần nạp.
5. Kiểm tra phần xem trước hoặc kết quả kiểm tra dữ liệu nếu giao diện hiển thị.
6. Sửa các dòng lỗi trong file nguồn rồi thực hiện import lại.
7. Sau khi import thành công, mở [Tiến độ hợp đồng](/stations) và tìm một số mã mẫu để đối chiếu.

Không nên thay đổi mapping trong lúc các bộ phận khác đang import dữ liệu. Nếu import báo lỗi danh mục, cần kiểm tra tỉnh, khu vực, loại hợp đồng, kiểu hợp đồng và trạng thái trước khi thử lại.

## 19. Quy trình nghiệp vụ: theo dõi và xử lý vướng mắc

**Router:** [Ghi nhận Vướng mắc](/issues)

Vướng mắc phải gắn với đúng hợp đồng hoặc đối tượng để các báo cáo tiến độ, đối tượng tồn và trợ lý AI có thể đối chiếu nguyên nhân.

1. Mở router **Ghi nhận Vướng mắc**.
2. Chọn tạo bản ghi vướng mắc.
3. Chọn hợp đồng hoặc đối tượng liên quan.
4. Chọn loại vướng mắc, ví dụ mặt bằng, kỹ thuật, pháp lý hoặc tài chính.
5. Viết mô tả ngắn nhưng đủ thông tin: hiện trạng, ảnh hưởng, đơn vị đang xử lý và đề xuất.
6. Lưu bản ghi với trạng thái ban đầu phù hợp.
7. Theo dõi các bản ghi đang mở trong danh sách.
8. Khi có kết quả xử lý, cập nhật trạng thái và bổ sung nội dung kết quả.

Khi báo cáo, cần phân biệt “đang mở”, “đang xử lý”, “đã giải quyết”, “từ chối” và “quá hạn”. Một vướng mắc quá hạn là vướng mắc đang mở vượt ngưỡng số ngày, không nhất thiết là vướng mắc có deadline xử lý chính thức.

## 20. Quy trình nghiệp vụ: cập nhật và kiểm tra sản lượng

**Router:** [Sản lượng Thi công](/construction-output) · [Dashboard Sản lượng & Thanh toán](/dashboard)

Sản lượng là dữ liệu theo kỳ. Khi nhập hoặc kiểm tra sản lượng, cần xác định rõ ngày ghi nhận, hợp đồng, đối tượng, hạng mục, nhà thầu và giá trị. Sau khi lưu, nên đối chiếu lại trên Dashboard để phát hiện chênh lệch hoặc số liệu bất thường.

1. Mở router **Sản lượng Thi công**.
2. Chọn kỳ dữ liệu cần nhập hoặc tra cứu.
3. Chọn hợp đồng và đối tượng chính xác.
4. Nhập giá trị sản lượng theo hạng mục hoặc biểu mẫu được cấp quyền.
5. Kiểm tra đơn vị tính, ngày thực hiện và giá trị tiền.
6. Lưu dữ liệu.
7. Mở [Dashboard](/dashboard) để xem tổng hợp theo kỳ.
8. Nếu số liệu không đúng, kiểm tra bộ lọc thời gian trước khi tạo yêu cầu điều chỉnh.

Không cộng các báo cáo có kỳ thời gian chồng lấn nếu chưa biết báo cáo là số phát sinh hay số lũy kế. Khi hỏi chatbot, luôn nêu rõ “phát sinh trong kỳ” hoặc “lũy kế đến ngày”.

## 21. Quy trình nghiệp vụ: rà soát đối tượng tồn

**Router:** [Quản lý ĐT tồn](/stations/surplus)

Rà soát đối tượng tồn giúp xác định các đối tượng chưa thể quyết toán, thiếu pháp lý, có vướng mắc hoặc lâu không phát sinh cập nhật.

1. Mở router **Quản lý ĐT tồn**.
2. Xem tổng quan theo nhóm nguyên nhân.
3. Sắp xếp theo tuổi tồn hoặc giá trị tồn nếu giao diện hỗ trợ.
4. Lọc theo khu vực, nhà thầu, hợp đồng hoặc mã đối tượng.
5. Mở chi tiết đối tượng cần xử lý.
6. Đối chiếu với [Ghi nhận Vướng mắc](/issues), [Quản lý Phân công](/stations/assignment) và [Sản lượng Thi công](/construction-output).
7. Ghi nhận đầu việc xử lý ở đúng module nghiệp vụ, không sửa số liệu gốc chỉ để làm mất cảnh báo.

Các cụm từ “trạm tồn”, “ĐT tồn”, “đối tượng chờ quyết toán” và “đối tượng chưa đủ điều kiện” thường cùng liên quan đến router này, nhưng cần xem nguyên nhân cụ thể trước khi kết luận.

## 22. Quy trình nghiệp vụ: kiểm tra phân công

**Router:** [Quản lý Phân công](/stations/assignment)

Kiểm tra phân công dùng để biết ai hoặc nhà thầu nào đang phụ trách đối tượng, phát hiện đối tượng chưa giao và đánh giá khối lượng công việc.

1. Mở router **Quản lý Phân công**.
2. Chọn bộ lọc nhà thầu, cán bộ, mã vùng, hợp đồng hoặc khu vực.
3. Kiểm tra danh sách đối tượng đang được giao.
4. Mở nhóm **chưa phân công** để tìm các đối tượng chưa có nhà thầu phụ trách.
5. Với từng đối tượng, đối chiếu trạng thái hợp đồng và vướng mắc.
6. Sau khi phân công hoặc điều chỉnh theo quy trình, tìm lại đối tượng để xác nhận dữ liệu mới.

Khi hỏi “tôi đang phụ trách bao nhiêu đối tượng”, người dùng cần nêu tên hoặc mã cán bộ/nhà thầu nếu hệ thống không có ngữ cảnh danh tính. Không suy luận người hỏi là một cán bộ cụ thể chỉ từ đại từ “tôi”.

## 23. Quy trình nghiệp vụ: kiểm soát volume

**Router:** [Kiểm soát Volume Hợp đồng](/volume)

Kiểm soát volume giúp phát hiện chênh lệch giữa giá trị hợp đồng và thành tiền thi công đã ghi nhận. Đây là kiểm soát giá trị, khác với theo dõi tiến độ phần trăm hoặc sản lượng theo kỳ.

1. Mở router **Kiểm soát Volume Hợp đồng**.
2. Xem tổng quan các nhóm hợp đồng vượt, thiếu, thừa hoặc cân bằng.
3. Tìm theo mã hoặc tên hợp đồng.
4. Mở chi tiết hợp đồng để kiểm tra tỷ lệ sử dụng, chênh lệch và nhóm hạng mục.
5. Nếu cần phân tích theo tỉnh hoặc khu vực, sử dụng phần phân bổ chi tiết nếu có dữ liệu.
6. Không chỉnh sửa sản lượng hoặc giá trị hợp đồng chỉ để làm cho tỷ lệ cân bằng; mọi điều chỉnh phải theo quy trình kiểm soát dữ liệu.

## 24. Quy trình nghiệp vụ: quản trị danh mục và quyền

**Router:** [Quản lý Tỉnh](/resources/provinces) · [Quản lý Khu vực](/resources/regions) · [Phân quyền Người dùng](/authorization)

Quản trị danh mục là nền tảng cho các bộ lọc và báo cáo. Tỉnh, khu vực, người dùng và quyền cần được duy trì nhất quán với dữ liệu nghiệp vụ.

- Tại [Quản lý Tỉnh](/resources/provinces), thêm hoặc cập nhật danh mục tỉnh/thành dùng trong hợp đồng và đối tượng.
- Tại [Quản lý Khu vực](/resources/regions), quản lý khu vực/trung tâm và quan hệ địa bàn.
- Tại [Phân quyền Người dùng](/authorization), cấp đúng quyền theo vai trò, kiểm tra quyền sau khi cập nhật và không cấp quyền rộng hơn phạm vi công việc.

Nếu người dùng đăng nhập nhưng không thấy menu, cần kiểm tra quyền trước khi kết luận router bị lỗi. Tài khoản có vai trò nhà thầu có thể chỉ thấy các nghiệp vụ [Tiến độ hợp đồng](/stations) và [Sản lượng Thi công](/construction-output).

## 25. Quy trình nghiệp vụ: cấu hình hợp đồng

**Router:** [Đối tượng quản lý](/config/managed-objects) · [Thuộc tính HĐ](/config/contract-attributes) · [Luồng trạng thái](/config/contract-statuses) · [Kiểu hợp đồng](/config/contract-types) · [Liên kết HĐ](/config/contract-links)

Cấu hình hợp đồng quyết định cách người dùng tạo, nhập, lọc và chuyển trạng thái dữ liệu. Chỉ người được phân quyền mới được thay đổi.

- **Đối tượng quản lý:** khai báo loại đối tượng và thông tin cần quản lý.
- **Thuộc tính HĐ:** khai báo các trường bổ sung của hợp đồng.
- **Luồng trạng thái:** khai báo trạng thái và các bước chuyển được phép.
- **Kiểu hợp đồng:** khai báo loại/kiểu để sử dụng khi tạo hợp đồng.
- **Liên kết HĐ:** khai báo quan hệ giữa các hợp đồng liên quan.

Trước khi thay đổi cấu hình, cần xác định dữ liệu cũ có bị ảnh hưởng không, trường có bắt buộc trong import Excel không và các báo cáo/chatbot có đang dùng tên danh mục đó không.

## 26. Bảng router đầy đủ cho chatbot

| Nghiệp vụ | Router chính | Router con hoặc liên quan |
|---|---|---|
| Đăng nhập | [`/login`](/login) | Đổi mật khẩu trong menu tài khoản |
| Dashboard | [`/dashboard`](/dashboard) | Báo cáo tổng quan, cảnh báo, xu hướng |
| Tiến độ hợp đồng | [`/stations`](/stations) | [`/stations/create`](/stations/create), [`/stations/import`](/stations/import), `/stations/{id}/edit` |
| Nguồn việc | [`/work-sources`](/work-sources) | Lọc theo trung tâm, nhà thầu, pháp lý |
| Phân công | [`/stations/assignment`](/stations/assignment) | Đối tượng chưa phân công, theo cán bộ/nhà thầu |
| Đối tượng tồn | [`/stations/surplus`](/stations/surplus) | Chờ quyết toán, thiếu pháp lý, lâu cập nhật |
| Vướng mắc | [`/issues`](/issues) | Vướng mở, quá hạn, theo loại |
| Sản lượng | [`/construction-output`](/construction-output) | Lọc theo kỳ, hợp đồng, đối tượng, nhà thầu |
| Volume hợp đồng | [`/volume`](/volume) | Tổng quan, chi tiết hợp đồng, chênh lệch |
| Lưu trữ | [`/archive`](/archive) | Tra cứu hồ sơ/archive hợp đồng |
| Tỉnh | [`/resources/provinces`](/resources/provinces) | Danh mục tỉnh/thành |
| Khu vực | [`/resources/regions`](/resources/regions) | Danh mục khu vực/trung tâm |
| Phân quyền | [`/authorization`](/authorization) | Người dùng, quyền hạn |
| Đối tượng quản lý | [`/config/managed-objects`](/config/managed-objects) | `/config/managed-objects/create`, `/config/managed-objects/{id}/edit` |
| Thuộc tính hợp đồng | [`/config/contract-attributes`](/config/contract-attributes) | Trường dữ liệu hợp đồng |
| Luồng trạng thái | [`/config/contract-statuses`](/config/contract-statuses) | Trạng thái và chuyển trạng thái |
| Kiểu hợp đồng | [`/config/contract-types`](/config/contract-types) | Loại/kiểu hợp đồng |
| Liên kết hợp đồng | [`/config/contract-links`](/config/contract-links) | Quan hệ hợp đồng |
| Mapping Excel | [`/config/excel-mapping`](/config/excel-mapping) | Mapping cột Excel |
| Trợ lý AI | [`/ai-assistant`](/ai-assistant) | `/ai-assistant/{conversationId}` |
