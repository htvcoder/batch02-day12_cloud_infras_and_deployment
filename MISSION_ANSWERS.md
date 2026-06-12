# Day 12 Lab - Mission Answers

## Part 1: Localhost vs Production

### Exercise 1.1: Anti-patterns found

Kiểm tra cấu trúc `01-localhost-vs-production/`:

- `develop/`: có `app.py`, `requirements.txt`, `utils/mock_llm.py`; không thấy `.env.example`, không thấy `config.py`.
- `production/`: có `app.py`, `config.py`, `.env.example`, `requirements.txt`, `utils/mock_llm.py`.

Các anti-pattern ở bản `develop`:

1. Hardcode secret ngay trong code với `OPENAI_API_KEY` và cả `DATABASE_URL`.
   Điều này rất nguy hiểm vì chỉ cần push nhầm lên GitHub public là key và thông tin kết nối bị lộ ngay.
2. Config để cứng trong source như `DEBUG = True`, `MAX_TOKENS = 500`.
   Việc này làm môi trường dev/prod khó tách bạch và mỗi lần đổi config lại phải sửa code rồi deploy lại.
3. Dùng `print()` để log và còn in cả secret ra log.
   Log thường bị thu thập tập trung; nếu log lộ key thì rủi ro gần giống lộ trực tiếp trong source.
4. Không có endpoint `/health`.
   Khi deploy lên cloud, platform hoặc load balancer không có cách đơn giản để biết app còn sống hay cần restart.
5. Bind `host="localhost"` thay vì `0.0.0.0`.
   App có thể chạy trên máy local nhưng không nhận được traffic từ bên ngoài container hoặc từ platform.
6. Port bị cố định là `8000`.
   Nhiều nền tảng inject `PORT` động; nếu không đọc từ env var thì app có thể fail khi deploy.
7. `reload=True` được bật cứng.
   Đây là hành vi phù hợp cho local development nhưng không nên giữ cố định khi chạy production.
8. Không thấy xử lý graceful shutdown hoặc signal như `SIGTERM`.
   Khi container bị dừng đột ngột, request đang chạy dở có thể bị mất hoặc lỗi.

### Exercise 1.2: Run basic/develop version

- Folder tested: `01-localhost-vs-production/develop`
- Command used:
  ```powershell
  cd 01-localhost-vs-production/develop
  .\.venv\Scripts\python.exe app.py
  ```
- Test command:
  ```powershell
  curl.exe http://localhost:8000/
  curl.exe -X POST "http://localhost:8000/ask?question=hello"
  curl.exe http://localhost:8000/health
  ```
- Result:
  App chạy được và endpoint `/` trả về:
  ```json
  {"message":"Hello! Agent is running on my machine :)"}
  ```

  Lần test đầu với `curl.exe` cho `/ask` trả `500 Internal Server Error`. Log cho thấy lỗi:
  ```text
  UnicodeEncodeError: 'charmap' codec can't encode character '\u0110'
  ```
  Nguyên nhân dự đoán: app dùng `print()` để log response tiếng Việt ra console Windows với encoding mặc định `cp1252`, nên bị lỗi khi ghi log.

  Sau khi chạy lại với biến môi trường `PYTHONIOENCODING=utf-8` để tránh lỗi encoding của console, `/ask` trả về:
  ```json
  {"answer":"Agent đang hoạt động tốt! (mock response) Hỏi thêm câu hỏi đi nhé."}
  ```

  Endpoint `/health` không tồn tại; gọi vào trả `404 Not Found`.

### Exercise 1.3: Comparison table

| Feature | Develop | Production | Why Important? |
| --- | --- | --- | --- |
| Config | Để cứng trong code | Tập trung trong `config.py`, đọc bằng `os.getenv(...)` | Giúp tách dev/staging/prod và đổi cấu hình mà không sửa source |
| Secrets | Hardcode trực tiếp trong `app.py` | Không hardcode trong source; lấy từ env vars | Giảm nguy cơ lộ key khi commit, log hoặc chia sẻ code |
| Port | Cố định `8000` | Đọc từ `PORT` | Hợp với môi trường cloud nơi port thường được inject động |
| Health check | Không có `/health` | Có `/health`, thêm cả `/ready` và `/metrics` | Giúp platform kiểm tra liveness/readiness và quan sát hệ thống |
| Logging | `print()` thường, còn log cả secret | Logging có format JSON, không log secret trong request handler | Dễ thu thập, tìm kiếm, cảnh báo và an toàn hơn |
| Shutdown | Không thấy xử lý shutdown | Có `lifespan` và đăng ký `SIGTERM` handler | Giúp app dừng gọn hơn, tránh cắt request giữa chừng |

### Exercise 1.4: Run production version

- Folder tested: `01-localhost-vs-production/production`
- Command used:
  ```powershell
  cd 01-localhost-vs-production/production
  $env:HOST='127.0.0.1'
  $env:PORT='8010'
  $env:DEBUG='false'
  $env:ENVIRONMENT='development'
  $env:APP_NAME='AI Agent'
  $env:APP_VERSION='1.0.0'
  $env:LLM_MODEL='gpt-4o-mini'
  $env:MAX_TOKENS='500'
  $env:ALLOWED_ORIGINS='http://localhost:3000,https://your-frontend.com'
  $env:OPENAI_API_KEY=''
  $env:AGENT_API_KEY=''
  .\.venv\Scripts\python.exe app.py
  ```
- Test command:
  ```powershell
  curl.exe http://127.0.0.1:8010/health
  $body = @{ question = 'hello' } | ConvertTo-Json -Compress
  Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8010/ask' -ContentType 'application/json' -Body $body
  ```
- Result:
  App chạy được.

  `/health` trả về JSON dạng:
  ```json
  {"status":"ok","uptime_seconds":2.4,"version":"1.0.0","environment":"development","timestamp":"2026-06-12T08:08:01.729586+00:00"}
  ```

  `/ask` trả về:
  ```json
  {"question":"hello","answer":"Đây là câu trả lời từ AI agent (mock). Trong production, đây sẽ là response từ OpenAI/Anthropic.","model":"gpt-4o-mini"}
  ```

  App có đọc config từ environment variables: khi mình set `HOST`, `PORT`, `DEBUG`, `APP_NAME`, `APP_VERSION`, `ENVIRONMENT`, `LLM_MODEL`, `ALLOWED_ORIGINS` trước lúc chạy thì app dùng đúng các giá trị đó.

  Tuy nhiên, từ code hiện tại mình không thấy chỗ tự nạp file `.env` vào process. `config.py` chỉ gọi `os.getenv(...)`, và lúc chạy app cũng không có `load_dotenv()`. Vì vậy `.env.example` hiện đóng vai trò file mẫu; muốn app đọc giá trị trong `.env` thì cần một launcher hoặc thư viện nạp `.env` trước khi import `settings`.

  Lần test đầu cho `/ask` bằng `curl.exe -d ...` bị lỗi `500 Internal Server Error`, log báo:
  ```text
  json.decoder.JSONDecodeError: Expecting property name enclosed in double quotes
  ```
  Đây là lỗi do payload JSON gửi từ lệnh test chưa đúng format trong PowerShell, không phải do route `/ask` bị hỏng.

### Discussion Questions

#### 1. Điều gì xảy ra nếu push code với API key hardcode lên GitHub public?

API key có thể bị bot hoặc người khác quét thấy rất nhanh, rồi bị dùng trái phép để gọi dịch vụ, phát sinh chi phí, lộ dữ liệu hoặc làm tài khoản bị khóa. Sau đó không chỉ cần xóa khỏi repo mà còn phải rotate key, kiểm tra log và xử lý hậu quả.

#### 2. Tại sao stateless quan trọng khi scale?

Vì khi app stateless, mọi instance đều có thể xử lý bất kỳ request nào mà không phụ thuộc trạng thái đang nằm trong bộ nhớ của một máy cụ thể. Nhờ vậy load balancer mới phân phối tải linh hoạt, scale ngang dễ hơn và khi một instance chết thì request mới vẫn có thể chuyển sang instance khác.

#### 3. 12-factor nói "dev/prod parity" nghĩa là gì trong thực tế?

Trong thực tế, điều đó nghĩa là môi trường dev nên càng giống production càng tốt về cách cấu hình, dependency, cách chạy app và các service phụ trợ. Càng ít khác biệt thì càng giảm tình huống “chạy trên máy em thì được nhưng lên server thì hỏng”.
