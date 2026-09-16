# Production Authentication and Authorization Plan for Chatbot

## 1. Mục tiêu

Bảo đảm mỗi request chatbot:

- Được gắn với đúng người dùng đã đăng nhập.
- Không thể dùng `session_id` hoặc `stream_id` của người khác.
- Chỉ gọi được tool mà người dùng có quyền.
- Chỉ đọc được dữ liệu thuộc phạm vi dữ liệu của người dùng.
- Không để LLM tự quyết định quyền truy cập.
- Có thể audit đầy đủ từ user request đến MCP tool call.

Backend Spring là nguồn quyết định quyền cuối cùng. Chatbot chỉ là lớp điều phối hội thoại và gọi tool.

## 2. Kiến trúc production

```text
Browser / Frontend
    |
    | Authorization: Bearer <user-access-token>
    v
Chatbot API
    |
    | 1. Verify user token hoặc token exchange
    | 2. Tạo chatbot session/stream gắn với user
    | 3. Chạy agent
    v
Backend Auth / Token Exchange
    |
    | Cấp internal token ngắn hạn cho chatbot
    v
MCP Backend
    |
    | X-API-Key: chatbot-service-key
    | Authorization: Bearer <internal-token>
    | Kiểm tra permission + data scope tại boundary tool
    v
Business data
```

Không dùng API key tĩnh làm danh tính người dùng. API key chỉ xác thực chatbot là service được phép gọi MCP.

## 3. Luồng xác thực đề xuất

### 3.1. Frontend gọi Chatbot

Frontend gửi `Authorization` cho cả hai request:

```http
POST /api/v1/chat/stream
Authorization: Bearer <user-access-token>
Content-Type: application/json
```

```http
GET /api/v1/chat/stream/{streamId}
Authorization: Bearer <user-access-token>
Accept: text/event-stream
```

Chatbot không tin `user_id`, `role`, `khuVucId` hoặc permission do client gửi trong request body.

### 3.2. Chatbot xác thực user

Chatbot cần xác thực:

- Có header `Authorization`.
- Scheme là `Bearer`.
- JWT có chữ ký hợp lệ.
- JWT chưa hết hạn.
- Claim `loai` có giá trị `access`.
- Claim `sub` là UUID hợp lệ.

Có hai phương án:

#### Phương án A: chia sẻ JWT secret

Chatbot và Backend cùng verify JWT HMAC bằng `JWT_SECRET`.

Ưu điểm:

- Nhanh, không thêm network hop.
- Phù hợp giai đoạn đầu.

Nhược điểm:

- Secret xuất hiện ở nhiều service.
- Xoay secret phức tạp hơn.

#### Phương án B: token introspection hoặc token exchange

Chatbot gửi user token tới Backend qua endpoint nội bộ. Backend xác thực và trả về danh tính/quyền hoặc internal token.

Ưu điểm:

- Backend giữ toàn quyền kiểm soát secret.
- Dễ thu hồi hoặc thay đổi chính sách.

Khuyến nghị production: dùng **token exchange**, có thể triển khai sau khi hoàn tất flow cơ bản.

## 4. Token exchange

Đề xuất endpoint nội bộ:

```http
POST /internal/auth/token-exchange
X-Internal-Service-Key: <chatbot-service-key>
Authorization: Bearer <user-access-token>
```

Response:

```json
{
  "accessToken": "<short-lived-internal-token>",
  "expiresIn": 300,
  "subject": {
    "userId": "...",
    "roleId": "...",
    "areaId": "..."
  }
}
```

Internal token nên có các claim:

```json
{
  "sub": "user-id",
  "iss": "bts-backend",
  "aud": "chatbot-mcp",
  "type": "internal_access",
  "jti": "unique-token-id",
  "quyenId": "role-id",
  "khuVucId": "area-id",
  "permissions": ["SAN_LUONG_READ"],
  "iat": 0,
  "exp": 0
}
```

Thiết lập:

- TTL: 1-5 phút.
- Audience bắt buộc: `chatbot-mcp`.
- Không dùng refresh token cho token exchange.
- Không ghi token vào log.
- Có thể cache theo `userId + token fingerprint` trong thời gian rất ngắn.
- MCP vẫn phải verify token, không tin chatbot tự khai báo claims.

## 5. Middleware Chatbot

Tạo middleware/dependency dùng chung, ví dụ:

```text
chatbot/app/security/auth.py
chatbot/app/security/middleware.py
```

Middleware tạo `request.state.principal` gồm:

```text
user_id
role_id
area_id
permissions
access_token hoặc internal_token
```

Không nên parse JWT lặp lại trong từng route.

Các route cần bảo vệ:

- `POST /api/v1/chat/stream`
- `GET /api/v1/chat/stream/{stream_id}`
- `GET /api/v1/models`
- Các API chatbot khác nếu được thêm sau này

Các endpoint public nếu có:

- health check
- readiness check
- metrics nội bộ, phải giới hạn bằng network policy hoặc service auth

Khi token không hợp lệ:

- Trả `401`.
- Không gọi LLM.
- Không gọi MCP.
- Không tạo session hoặc stream.

## 6. Session và stream ownership

Không dùng `session_id` client gửi làm khóa toàn cục.

Khóa logic phải chứa user:

```text
(user_id, session_id)
```

Khi tạo stream, lưu metadata:

```json
{
  "streamId": "...",
  "userId": "...",
  "sessionId": "...",
  "createdAt": "...",
  "expiresAt": "..."
}
```

Khi GET stream:

- Lấy user từ token hiện tại.
- So sánh với owner của stream.
- Khác user thì trả `403` hoặc `404` để tránh lộ stream tồn tại.
- Stream hết hạn thì xóa và trả `404`.

Không lưu stream ownership chỉ trong process dictionary khi chạy nhiều instance. Production cần Redis với TTL:

```text
chatbot:stream:{stream_id} -> owner/session/status
chatbot:session:{user_id}:{session_id} -> conversation metadata
```

## 7. Truyền identity sang MCP

Mỗi MCP request cần có hai lớp xác thực:

```http
X-API-Key: <chatbot-service-key>
Authorization: Bearer <internal-token>
```

MCP backend thực hiện:

1. Xác thực service key.
2. Verify internal token.
3. Kiểm tra `iss`, `aud`, `type`, `exp`.
4. Tạo `SecurityContext` từ `sub` và claims.
5. Kiểm tra permission của tool.
6. Áp dụng data scope vào repository query.

Chatbot không truyền quyền bằng body như:

```json
{
  "role": "ADMIN",
  "khuVucId": "..."
}
```

Các giá trị này chỉ được lấy từ token đã verify hoặc từ Backend.

## 8. Phân quyền MCP tool

Tạo allowlist rõ ràng:

```text
sanluong_tool       -> SAN_LUONG_READ
hopdong_tool        -> HOP_DONG_READ
tram_ton_tool       -> TRAM_TON_READ
vuong_mac_tool      -> VUONG_MAC_READ
phan_cong_tool      -> PHAN_CONG_READ
bien_ban_tool       -> BIEN_BAN_READ
```

Có thể triển khai bằng một trong hai cách:

- Gắn `@RequiresPermission` trực tiếp trên từng MCP method.
- Tạo `ToolAuthorizationService` kiểm tra theo tên tool trước khi invoke.

Khuyến nghị dùng cả hai lớp:

- Boundary MCP kiểm tra allowlist.
- Handler/service kiểm tra permission và data scope lần cuối.

LLM có thể chọn tool, nhưng không thể vượt qua authorization.

## 9. Data scope

`DataScopeService` phải lấy `khuVucId` từ authenticated principal.

Không tin các filter do LLM truyền nếu chúng mở rộng phạm vi user được phép xem:

- `khuVuc`
- `nhaThauId`
- `maHopDong`
- `maDoiTuong`

Quy tắc:

- Admin/global scope: được xem theo policy riêng.
- User có khu vực: query phải luôn giới hạn theo `khuVucId` của token.
- Filter trong câu hỏi chỉ được thu hẹp phạm vi, không được mở rộng.
- Nếu filter mâu thuẫn với scope, trả kết quả rỗng hoặc `403` theo nghiệp vụ.

## 10. Cập nhật frontend

Trong service chatbot, lấy access token từ auth storage và gửi vào cả POST/GET:

```ts
const token = getAccessToken()

headers: {
  'Content-Type': 'application/json',
  ...(token ? { Authorization: `Bearer ${token}` } : {}),
}
```

Khi nhận `401`:

1. Thử refresh access token một lần.
2. Gửi lại request tạo stream.
3. Nếu refresh thất bại, xóa session auth và chuyển về trang đăng nhập.

Không retry vô hạn với stream GET.

## 11. Logging và audit

Mỗi request cần có:

- `request_id`
- `user_id` đã mask hoặc UUID
- `session_id` dạng hash hoặc ID an toàn
- `stream_id`
- tool name
- permission cần kiểm tra
- kết quả authorization: allow/deny
- latency
- error code

Không log:

- access token
- refresh token
- internal token
- API key
- toàn bộ dữ liệu nghiệp vụ nhạy cảm

Audit event đề xuất:

```text
CHAT_REQUEST_ACCEPTED
CHAT_REQUEST_DENIED
MCP_TOOL_ALLOWED
MCP_TOOL_DENIED
MCP_SCOPE_RESTRICTED
CHAT_STREAM_OWNERSHIP_DENIED
```

## 12. Rate limit và giới hạn tài nguyên

Áp dụng theo `user_id` và IP:

- Giới hạn số stream đồng thời.
- Giới hạn số request mỗi phút.
- Giới hạn độ dài message.
- Timeout cho LLM và MCP.
- Giới hạn kích thước tool result đưa vào prompt.
- Hủy task khi client disconnect.
- Dọn stream/session hết hạn bằng TTL.

Admin có thể có quota riêng nhưng vẫn phải audit.

## 13. Lộ trình triển khai

### Phase 1: Authentication boundary

- Frontend gửi Bearer sang chatbot.
- Chatbot verify user JWT.
- Bảo vệ POST/GET stream và models.
- Từ chối request không có token.
- Chưa cần token exchange nếu cần triển khai nhanh.

### Phase 2: MCP identity propagation

- Chatbot giữ principal trong stream context.
- Forward user JWT hoặc internal token sang MCP.
- Backend MCP verify token.
- Gắn permission cho `sanluong_tool` và các tool đọc dữ liệu.

### Phase 3: Data scope

- Áp dụng `DataScopeService` cho tool handlers/repositories.
- Kiểm thử user khác khu vực.
- Chặn việc giả mạo `khuVuc` và các filter khác.

### Phase 4: Token exchange

- Thêm endpoint nội bộ token exchange.
- Cấp internal token TTL 1-5 phút.
- MCP chỉ nhận internal token cho tool call.
- Bật audience/issuer validation.
- Xoay service key và JWT secret theo quy trình production.

### Phase 5: Distributed state và hardening

- Chuyển stream/session state sang Redis.
- Ownership check trên mọi instance.
- Rate limit, audit, metrics, alerting.
- Chạy security regression và load test.

## 14. Test bắt buộc

### Authentication

- Không có token -> `401`.
- Token sai chữ ký -> `401`.
- Token hết hạn -> `401`.
- Refresh token dùng cho chatbot -> `401`.
- Token đúng nhưng thiếu `sub` -> `401`.
- Token sai audience/issuer -> `401`.

### Ownership

- User A không đọc được session User B.
- User A không đọc được stream User B.
- Stream hết hạn -> `404`.
- Retry cùng stream không làm lộ dữ liệu.

### Authorization

- Không có `SAN_LUONG_READ` -> tool bị từ chối.
- Có quyền tool nhưng khác khu vực -> dữ liệu bị giới hạn.
- LLM truyền khu vực khác -> không vượt scope.
- User global scope hoạt động theo policy.

### MCP

- Thiếu `X-API-Key` -> từ chối.
- API key đúng nhưng token sai -> từ chối.
- Service gọi tool không nằm allowlist -> từ chối.
- Internal token hết hạn giữa các request -> không cho gọi tiếp.

### Regression

- Chat bình thường vẫn tạo được stream.
- SSE token/tool_result/chart/suggestions/done vẫn đúng thứ tự.
- MCP tool lỗi không làm lộ token hoặc permission.
- Refresh token không tạo nhiều stream trùng.

## 15. Definition of Done

- Mọi chatbot API production đều yêu cầu user authentication.
- Mọi stream/session đều có owner và TTL.
- MCP backend biết user thực sự của từng tool call.
- Permission được kiểm tra tại Backend, không chỉ tại chatbot.
- Data scope được áp dụng ở query/service layer.
- Không có token hoặc secret trong log.
- Có test cho 401, 403, ownership, scope và MCP propagation.
- Có metrics và audit cho deny/allow.
- Có thể revoke/rotate token và service key mà không sửa code.
