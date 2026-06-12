# Day 12 Lab - Solution

## 0. Tổng quan

Day 12 Lab tập trung vào việc đưa một AI agent từ môi trường local lên trạng thái gần production-ready qua 5 bước chính:

- Hiểu khác biệt giữa localhost và production.
- Đóng gói agent bằng Docker.
- Deploy agent lên cloud.
- Bảo vệ API bằng auth, rate limit và cost guard.
- Thiết kế hệ thống có khả năng scale và reliable với health check, readiness, graceful shutdown, stateless design, Redis và load balancing.

File này tổng hợp lời giải và trạng thái thực tế của **Part 1 đến Part 5** dựa trên:

- `PLAN.md`
- `CODE_LAB.md`
- `README.md`
- `MISSION_ANSWERS.md`
- `DEPLOYMENT.md`
- `03-cloud-deployment/PART3_STATUS.md`
- `04-api-gateway/PART4_STATUS.md`
- `05-scaling-reliability/PART5_STATUS.md`
- README và source/config thực tế trong từng thư mục Part

---

## Part 1 - Localhost vs Production

### 1.1. Mục tiêu

Part 1 giúp nhận ra vì sao code "chạy trên máy em" chưa đủ để xem là production-ready. Trọng tâm là phân biệt app kiểu local/develop với app có config management, health check, logging và graceful shutdown phù hợp hơn cho môi trường deploy.

### 1.2. Files đã đọc

- `01-localhost-vs-production/README.md`
- `01-localhost-vs-production/develop/app.py`
- `01-localhost-vs-production/develop/requirements.txt`
- `01-localhost-vs-production/develop/utils/mock_llm.py`
- `01-localhost-vs-production/production/app.py`
- `01-localhost-vs-production/production/config.py`
- `01-localhost-vs-production/production/.env.example`
- `01-localhost-vs-production/production/requirements.txt`
- `01-localhost-vs-production/production/utils/mock_llm.py`
- `MISSION_ANSWERS.md`

### 1.3. Anti-patterns trong bản develop

1. **Hardcoded secret và connection string**
   - Mô tả: `OPENAI_API_KEY` và `DATABASE_URL` được ghi trực tiếp trong `develop/app.py`.
   - Vì sao nguy hiểm trong production: dễ lộ secret khi commit, log hoặc chia sẻ source.
   - Cách bản production xử lý: đọc từ environment variables qua `production/config.py`.

2. **Config hardcode trong source**
   - Mô tả: `DEBUG = True`, `MAX_TOKENS = 500` và các giá trị cấu hình được để cứng trong code.
   - Vì sao nguy hiểm trong production: khó tách dev/staging/prod và mọi thay đổi đều phải sửa code.
   - Cách bản production xử lý: gom config trong `config.py`, đọc từ env như `HOST`, `PORT`, `DEBUG`, `OPENAI_API_KEY`.

3. **Port cố định và chỉ bind localhost**
   - Mô tả: app develop bind `host="localhost"` và port `8000`.
   - Vì sao nguy hiểm trong production: container hoặc platform cloud thường yêu cầu bind `0.0.0.0` và đọc port động từ biến `PORT`.
   - Cách bản production xử lý: bind `settings.host` mặc định `0.0.0.0` và đọc `settings.port` từ env.

4. **Debug reload bật cứng**
   - Mô tả: `reload=True` trong `uvicorn.run(...)`.
   - Vì sao nguy hiểm trong production: làm hành vi runtime không ổn định, không phù hợp cho môi trường thật.
   - Cách bản production xử lý: `reload=settings.debug`, chỉ bật khi `DEBUG=true`.

5. **Không có health check**
   - Mô tả: bản develop không có endpoint `/health`.
   - Vì sao nguy hiểm trong production: platform hoặc load balancer không có cách đơn giản để kiểm tra liveness.
   - Cách bản production xử lý: bổ sung `GET /health`.

6. **Không graceful shutdown**
   - Mô tả: develop không xử lý `SIGTERM` hoặc shutdown có kiểm soát.
   - Vì sao nguy hiểm trong production: request đang xử lý có thể bị cắt giữa chừng khi container bị stop/restart.
   - Cách bản production xử lý: đăng ký signal handler `SIGTERM` và log quá trình shutdown.

7. **Logging chưa phù hợp production**
   - Mô tả: dùng `print()` và còn log cả secret.
   - Vì sao nguy hiểm trong production: vừa khó quan sát tập trung, vừa tăng nguy cơ lộ thông tin nhạy cảm.
   - Cách bản production xử lý: dùng logging có cấu trúc tốt hơn và không log secret trực tiếp.

### 1.4. So sánh develop vs production

| Feature | Develop | Production | Vì sao quan trọng? |
| --- | --- | --- | --- |
| Config | Hardcode trong code | Đọc từ `config.py` + env vars | Tách dev/prod rõ ràng, đổi config không cần sửa source |
| Secrets | Hardcode trực tiếp | Lấy từ env vars | Tránh lộ key khi commit hoặc log |
| Port | Cố định `8000` | Đọc từ `PORT` | Phù hợp với cloud/platform inject port động |
| Health check | Không có `/health` | Có `/health` | Giúp platform biết app còn sống |
| Logging | `print()` thường | Logging có kiểm soát hơn | Dễ quan sát và an toàn hơn |
| Shutdown | Không xử lý rõ | Có `SIGTERM` handler | Tránh cắt request đột ngột |

### 1.5. Kết quả chạy thử

Theo `MISSION_ANSWERS.md`:

- Bản develop chạy được local.
- `POST /ask` từng gặp `500 Internal Server Error` trên PowerShell do lỗi `UnicodeEncodeError` khi `print()` tiếng Việt ra console Windows.
- Sau khi chạy với `PYTHONIOENCODING=utf-8`, `/ask` trả response mock bình thường.
- `/health` ở bản develop trả `404 Not Found`.

Với bản production:

- `GET /health`: chạy thành công, trả `200 OK`.
- `POST /ask`: chạy thành công khi gửi JSON hợp lệ.
- App thực sự đọc được `HOST`, `PORT`, `DEBUG`, `APP_VERSION`, `ENVIRONMENT`, `LLM_MODEL` từ biến môi trường.

### 1.6. Câu hỏi thảo luận

1. Nếu push code có API key hardcode lên GitHub public, key có thể bị bot hoặc người khác quét thấy rất nhanh, dẫn đến lạm dụng dịch vụ, phát sinh chi phí, lộ dữ liệu hoặc phải khóa tài khoản. Sau đó cần rotate key và rà log.
2. Stateless quan trọng khi scale vì mọi instance đều có thể xử lý bất kỳ request nào mà không phụ thuộc state trong RAM của một máy cụ thể. Nhờ đó load balancer phân phối request linh hoạt hơn và failover tốt hơn.
3. "Dev/prod parity" nghĩa là môi trường develop nên càng giống production càng tốt về dependency, config, cách chạy app và service phụ trợ để giảm lỗi kiểu "works on my machine".

---

## Part 2 - Docker Containerization

### 2.1. Mục tiêu

Part 2 tập trung vào việc đóng gói agent bằng Docker, hiểu cấu trúc Dockerfile, lợi ích của multi-stage build và cách chạy một stack nhiều service bằng Docker Compose.

### 2.2. Files đã đọc

- `02-docker/README.md`
- `02-docker/develop/Dockerfile`
- `02-docker/develop/requirements.txt`
- `02-docker/develop/app.py`
- `02-docker/production/Dockerfile`
- `02-docker/production/requirements.txt`
- `02-docker/production/main.py`
- `02-docker/production/docker-compose.yml`
- `02-docker/production/nginx/nginx.conf`
- `MISSION_ANSWERS.md`

### 2.3. Dockerfile develop

1. Base image là `python:3.11`.
2. Working directory là `/app`.
3. Dockerfile develop là **single-stage build**.
4. `CMD` là:

```dockerfile
CMD ["python", "app.py"]
```

5. `COPY requirements.txt .` rồi `RUN pip install` nên đặt trước `COPY . .` để tận dụng Docker layer cache. Khi code thay đổi nhưng dependencies không đổi, Docker không phải cài lại toàn bộ packages.

### 2.4. Dockerfile production / multi-stage build

- Stage `builder` dùng `python:3.11-slim` để cài dependencies và chuẩn bị artifact runtime.
- Stage `runtime` cũng dùng `python:3.11-slim`, chỉ copy phần cần thiết để chạy app.
- Image production nhỏ hơn vì không giữ lại tool build hoặc file thừa từ quá trình build.
- Multi-stage an toàn hơn vì runtime image gọn hơn, ít bề mặt tấn công hơn, và trong code hiện tại còn có `USER appuser` thay vì chạy bằng root.

### 2.5. Docker Compose stack

`docker-compose.yml` trong Part 2 production mô tả các service:

- `agent`
- `redis`
- `qdrant`
- `nginx`

Sơ đồ text:

```text
Client
  ↓
Nginx / Reverse Proxy
  ↓
Agent container
  ↓
Redis / Qdrant
```

`nginx.conf` dùng upstream trỏ tới `agent:8000`.

### 2.6. Kết quả build/run/test

Theo `MISSION_ANSWERS.md`:

- Build command develop:

```bash
docker build -f 02-docker/develop/Dockerfile -t agent-develop .
```

- Run command develop:

```bash
docker run -p 8000:8000 agent-develop
```

- Test `/health` develop: `200 OK`
- Test `/ask` develop: thành công

- Build command production:

```bash
docker build -f 02-docker/production/Dockerfile -t agent-production .
```

- Run Docker Compose production:

```bash
docker compose -f 02-docker/production/docker-compose.yml up --build -d
```

- Test qua Nginx:
  - `/health`: thành công
  - `/ask`: thành công khi gửi JSON đúng format

- Image size develop:
  - `DISK USAGE` khoảng `1.66GB`
  - `CONTENT SIZE` khoảng `424MB`

- Image size production:
  - `DISK USAGE` khoảng `236MB`
  - `CONTENT SIZE` khoảng `56.6MB`

- So sánh:
  - Production nhỏ hơn khoảng `1.42GB` theo `DISK USAGE`
  - Tương đương giảm khoảng `85.8%`

### 2.7. Câu hỏi thảo luận

1. `COPY requirements.txt` trước giúp tận dụng cache của Docker và tăng tốc build khi chỉ thay đổi source code.
2. `.dockerignore` nên chứa `__pycache__/`, `*.pyc`, `.git/`, `.venv/`, `venv/`, `.env`, file IDE, docs/test không cần thiết. `venv/` quan trọng vì nếu copy vào image sẽ phình context và lẫn dependency local; `.env` quan trọng vì có thể làm lộ secret vào image hoặc registry.
3. Nếu agent cần đọc file từ disk thì mount volume bằng `-v` hoặc `volumes:` trong Compose, ví dụ `./data:/app/data`.

---

## Part 3 - Cloud Deployment

### 3.1. Mục tiêu

Part 3 tập trung vào việc đưa agent lên cloud, hiểu sự khác nhau giữa các lựa chọn như Railway, Render, Cloud Run và xác nhận ít nhất một hướng deploy thực sự hoạt động.

### 3.2. Files đã đọc

- `03-cloud-deployment/README.md`
- `03-cloud-deployment/PART3_STATUS.md`
- `03-cloud-deployment/railway/app.py`
- `03-cloud-deployment/railway/Procfile`
- `03-cloud-deployment/railway/railway.toml`
- `03-cloud-deployment/railway/requirements.txt`
- `03-cloud-deployment/render/render.yaml`
- `03-cloud-deployment/production-cloud-run/cloudbuild.yaml`
- `03-cloud-deployment/production-cloud-run/service.yaml`
- `DEPLOYMENT.md`
- `MISSION_ANSWERS.md`

### 3.3. So sánh platform

| Platform | Best for | Ưu điểm | Nhược điểm | Khi nào dùng |
| --- | --- | --- | --- | --- |
| Railway | Prototype, demo, học lab | Nhanh, ít cấu hình, deploy dễ | Ít production controls hơn Cloud Run/K8s | Khi cần public URL nhanh để demo |
| Render | Side project, IaC đơn giản | Có `render.yaml`, workflow khá trực quan | Thường cần GitHub + dashboard để deploy thật | Khi muốn deploy qua GitHub/Blueprint |
| Cloud Run | Production vừa và nhỏ theo kiểu serverless container | Tích hợp tốt với GCP, autoscaling, CI/CD | Cần GCP project, account, cấu hình nhiều hơn | Khi app đã vượt mức demo và cần vận hành bài bản hơn |
| Kubernetes | Enterprise, quy mô lớn | Linh hoạt và mạnh nhất | Setup và vận hành phức tạp nhất | Khi hệ thống đủ lớn và cần orchestration đầy đủ |

### 3.4. Railway deployment

Railway đã được deploy **thật sự thành công** theo `DEPLOYMENT.md` và `PART3_STATUS.md`.

Public URL thực tế:

```text
https://day12-cloud-deployment-part3-production.up.railway.app
```

Kết quả test thực tế:

```text
GET /health: OK
POST /ask: OK
```

Tóm tắt response đã ghi nhận:

- `/health` trả `200 OK` với JSON chứa `status`, `uptime_seconds`, `platform`, `timestamp`.
- `/ask` trả response mock thành công qua `Invoke-RestMethod`.

Không có secret nào được ghi vào repo trong phần này.

### 3.5. Render review

Render hiện ở mức **review/config only**, chưa có bằng chứng deploy thật.

Tóm tắt:

- `render.yaml` khai báo một web service cho Render.
- File đang dùng `rootDir: 03-cloud-deployment/railway`, tức là tái sử dụng app Railway.
- Có `startCommand: uvicorn app:app --host 0.0.0.0 --port $PORT`
- Có `healthCheckPath: /health`
- Muốn deploy thật cần GitHub repo và Render dashboard/account.
- Hiện **chưa có public URL Render**.

### 3.6. Cloud Run review

Cloud Run hiện ở mức **review only**, chưa có deploy thật.

Tóm tắt:

- `cloudbuild.yaml` mô tả pipeline build/push/deploy image lên GCP.
- `service.yaml` mô tả Cloud Run service definition.
- Cần GCP account, project và region để deploy thật.
- Có placeholder cần thay như `PROJECT_ID`.
- Theo `PART3_STATUS.md`, `service.yaml` còn điểm cần rà lại trước khi deploy thật.

### 3.7. Câu hỏi thảo luận

1. Serverless/Lambda không phải lúc nào cũng tốt cho AI agent vì agent thường có latency cao hơn app CRUD thông thường, có thể cần warm state, dependency nặng hoặc kết nối đến Redis/vector DB; cold start và giới hạn runtime có thể làm UX xấu đi.
2. Cold start là thời gian platform phải khởi động container/instance mới trước khi xử lý request đầu tiên. Nó làm request đầu tiên chậm đáng kể và gây cảm giác phản hồi không ổn định.
3. Nên upgrade từ Railway lên Cloud Run khi app không còn chỉ là demo nữa mà bắt đầu cần autoscaling tốt hơn, CI/CD chặt hơn, secret management chuẩn hơn và khả năng vận hành production rõ ràng hơn.

---

## Part 4 - API Gateway & Security

### 4.1. Mục tiêu

Part 4 thêm lớp bảo vệ trước agent bằng authentication, rate limiting và cost guard để tránh lộ API công khai dẫn đến lạm dụng hoặc vượt ngân sách.

### 4.2. Files đã đọc

- `04-api-gateway/README.md`
- `04-api-gateway/PART4_STATUS.md`
- `04-api-gateway/develop/app.py`
- `04-api-gateway/develop/test_auth.py`
- `04-api-gateway/develop/requirements.txt`
- `04-api-gateway/production/app.py`
- `04-api-gateway/production/auth.py`
- `04-api-gateway/production/rate_limiter.py`
- `04-api-gateway/production/cost_guard.py`
- `04-api-gateway/production/test_advanced.py`
- `04-api-gateway/production/requirements.txt`
- `MISSION_ANSWERS.md`

### 4.3. API Key Authentication

Tổng hợp theo code và status hiện tại:

- API key được đọc từ environment variable `AGENT_API_KEY`.
- Header dùng để truyền key là `X-API-Key`.
- Không có key: trả `401 Unauthorized`.
- Sai key: trả `401 Unauthorized`.
- Đúng key: request qua được và trả `200 OK`.
- Test script `develop/test_auth.py`: pass.

Ghi chú:

- Code develop có fallback demo key trong source cho mục đích lab.
- Endpoint được bảo vệ là `POST /ask`.

### 4.4. JWT Authentication

Tổng hợp theo code thực tế:

- Endpoint lấy token trong code hiện tại là `POST /auth/token`.
- Demo credentials:
  - `student / demo123`
  - `teacher / teach456`
- File tạo/verify JWT là `04-api-gateway/production/auth.py`.
- Header dùng token là:

```text
Authorization: Bearer <TOKEN>
```

- Missing token: `401 Unauthorized`
- Invalid token: `403 Forbidden`
- Expired token: `401 Unauthorized`

Không ghi token thật trong file này.

### 4.5. Rate Limiting

- File implementation: `04-api-gateway/production/rate_limiter.py`
- Thuật toán/storage: **in-memory sliding window** dùng `deque`
- Limit mặc định:
  - User thường: `10 request / 60 giây`
  - Admin: `100 request / 60 giây`
- Khi vượt limit: trả `429 Too Many Requests`
- Rate limit hiện đang áp theo user lấy từ JWT payload, không phải global IP limiter

### 4.6. Cost Guard

- File implementation: `04-api-gateway/production/cost_guard.py`
- Budget model hiện tại trong code:
  - Per-user daily budget: `$1/ngày`
  - Global daily budget: `$10/ngày`
- Spending tracking:
  - `input_tokens`
  - `output_tokens`
  - `request_count`
  - `cost_usd`
- Khi vượt budget user: trả `402 Payment Required`
- Khi vượt global budget: trả `503 Service Unavailable`
- Storage hiện tại: **in-memory/mock**, chưa phải Redis hay database

### 4.7. Security flow

Luồng mô tả trong lab:

```text
Request
  ↓
Auth Check
  ↓
Rate Limit
  ↓
Input Validation
  ↓
Cost Check
  ↓
Agent
```

Theo code thực tế của FastAPI, input validation ở tầng framework có thể diễn ra trước khi vào handler endpoint. Với request JSON hợp lệ, luồng chính đang thể hiện là:

```text
Request
  ↓
Body Validation / Parse
  ↓
Auth Check
  ↓
Rate Limit
  ↓
Cost Check
  ↓
Agent
```

### 4.8. Kết quả test

Tổng hợp từ `MISSION_ANSWERS.md` và `PART4_STATUS.md`:

- Develop API Key Auth: **pass**
- Production JWT: **pass**
- Rate limit: **pass**
- Cost guard: **pass ở mức module-level**, chưa có bằng chứng hit trực tiếp qua API với budget mặc định

### 4.9. Câu hỏi thảo luận

1. API Key phù hợp cho service-to-service hoặc MVP đơn giản. JWT phù hợp khi cần mang theo danh tính/role user theo kiểu stateless. OAuth2 phù hợp khi có đăng nhập qua bên thứ ba hoặc luồng ủy quyền phức tạp hơn.
2. Không có một con số cố định cho mọi hệ thống, nhưng với AI agent demo/lab thì `10 request/phút` cho user thường là mức hợp lý để cân bằng UX, chi phí và chống spam.
3. Nếu API key bị lộ thì cần rotate key ngay, rà log để tìm lạm dụng, khóa hoặc giới hạn tạm thời endpoint, sau đó siết lại secret handling và các lớp bảo vệ như rate limit/cost guard.

---

## Part 5 - Scaling & Reliability

### 5.1. Lưu ý nguồn yêu cầu

Part 5 không có README riêng. Nội dung phần này được tổng hợp từ:

- `CODE_LAB.md`
- `PLAN.md`
- `MISSION_ANSWERS.md`
- `05-scaling-reliability/PART5_STATUS.md`
- Source code thực tế trong `05-scaling-reliability/`

### 5.2. Mục tiêu

Part 5 tập trung vào:

- Health check
- Readiness check
- Graceful shutdown
- Stateless design
- Redis shared state
- Nginx load balancing
- Scale nhiều agent instances
- Test tính stateless của session/history

### 5.3. Files đã đọc

- `05-scaling-reliability/PART5_STATUS.md`
- `05-scaling-reliability/develop/app.py`
- `05-scaling-reliability/develop/requirements.txt`
- `05-scaling-reliability/develop/utils/mock_llm.py`
- `05-scaling-reliability/production/app.py`
- `05-scaling-reliability/production/Dockerfile`
- `05-scaling-reliability/production/requirements.txt`
- `05-scaling-reliability/production/docker-compose.yml`
- `05-scaling-reliability/production/nginx.conf`
- `05-scaling-reliability/production/test_stateless.py`
- `05-scaling-reliability/production/utils/mock_llm.py`
- `MISSION_ANSWERS.md`

### 5.4. Health và Readiness

- `/health` dùng để báo app còn sống, ở production còn trả thêm `instance_id`, `storage`, `redis_connected`.
- `/ready` dùng để báo app đã sẵn sàng nhận traffic; production sẽ ping Redis nếu Redis đang được dùng.
- Liveness khác readiness ở chỗ:
  - Liveness: process còn sống hay không
  - Readiness: service phụ thuộc đã sẵn sàng để nhận request hay chưa

Kết quả test đã ghi nhận:

- Develop:
  - `GET /health` -> `200`
  - `GET /ready` -> `200`
- Production:
  - `GET /health` -> `200`
  - `GET /ready` -> `200` trong local smoke test

### 5.5. Graceful Shutdown

Theo code:

- App develop xử lý cả `SIGTERM` và `SIGINT`
- Có tracking `in_flight_requests`
- Có `timeout_graceful_shutdown=30`
- Có middleware đếm request đang xử lý
- Có log shutdown qua `lifespan`

Kết luận:

- Graceful shutdown ở develop: **pass**
- Bản production có `lifespan` logging nhưng chưa thể hiện mức xử lý signal rõ như develop

### 5.6. Stateless Design với Redis

- Không nên lưu state conversation hoàn toàn trong memory vì khi scale nhiều instance, mỗi instance sẽ có RAM riêng và dễ mất context khi request đi sang máy khác.
- Trong production app, state/session được ưu tiên lưu qua Redis với key dạng:

```text
session:{session_id}
```

- Nếu Redis không sẵn sàng hoặc module `redis` không có, app fallback sang in-memory store.
- Test history/session có tồn tại qua:
  - `POST /chat`
  - `GET /chat/{session_id}/history`
  - `DELETE /chat/{session_id}`

Trạng thái trung thực hiện tại:

- Thiết kế stateless theo hướng Redis: **đúng hướng**
- Chứng minh runtime fully stateless/shared-state: **partial**
- Lý do: local smoke test hiện đang chạy được cả nhánh fallback in-memory

### 5.7. Load Balancing

Docker Compose production có các service:

- `agent`
- `redis`
- `nginx`

Nginx route theo upstream `agent_cluster` và proxy sang service agent.

Scale command được ghi rõ trong compose:

```bash
docker compose up --build --scale agent=3
```

Trạng thái:

- Về config: đã chuẩn bị để scale 3 instances
- Về bằng chứng runtime thật: chưa xác nhận đầy đủ trên máy hiện tại do Docker daemon không chạy
- `test_stateless.py` có quan sát trường `served_by` để xem request được phục vụ bởi instance nào

### 5.8. Architecture diagram

```text
Client
  ↓
Nginx / Load Balancer
  ↓
Agent instance 1
Agent instance 2
Agent instance 3
  ↓
Redis shared state
```

### 5.9. Kết quả test

Tổng hợp từ `MISSION_ANSWERS.md` và `PART5_STATUS.md`:

- `/health`: **pass**
- `/ready`: **pass**
- Graceful shutdown: **pass ở develop**
- Docker Compose: **config ready**, chưa chốt full runtime pass
- Redis/stateless: **partial**
- Load balancing scale 3: **config ready**, chưa có bằng chứng runtime thật trên máy hiện tại
- `test_stateless.py`: **present / partial**

Nguyên nhân chính của phần partial:

- Docker daemon trên máy tại thời điểm kiểm tra không chạy
- Python env local chưa có đầy đủ package để chứng minh nhánh Redis-backed runtime thật

### 5.10. Key takeaways

- Health check và readiness check là hai khái niệm khác nhau và đều quan trọng khi deploy.
- Graceful shutdown giúp hệ thống dừng an toàn hơn, đặc biệt khi có request đang xử lý.
- Stateless design là điều kiện quan trọng để scale ngang.
- Redis/shared store giúp tách session ra khỏi memory của từng instance.
- Có config load balancing là chưa đủ; vẫn cần bằng chứng runtime thật để chốt hoàn toàn.

---

## Tổng kết chung Part 1-5

| Part | Chủ đề | Trạng thái | Kết quả chính |
| --- | --- | --- | --- |
| Part 1 | Localhost vs Production | Hoàn thành | Chỉ ra rõ anti-patterns và bản production xử lý bằng env, health check, graceful shutdown |
| Part 2 | Docker | Hoàn thành | Build/run được, có so sánh image size, stack qua Nginx/Redis/Qdrant hoạt động |
| Part 3 | Cloud Deployment | Hoàn thành | Railway deployed OK với public URL thật |
| Part 4 | API Security | Hoàn thành ở mức local test | API key auth, JWT, rate limit và cost guard đều đã được kiểm tra |
| Part 5 | Scaling & Reliability | Partial | Source/config đúng hướng, health/ready pass, nhưng chưa có full runtime proof cho scale 3 + Redis shared state |

Qua 5 phần đầu, lab đã bao phủ các concept cốt lõi để đưa AI agent tiến gần production: config theo env, containerization, deploy cloud, auth/security và reliability/scaling. Những phần đã có bằng chứng chạy thành công rõ ràng gồm Part 1 đến Part 4, và Railway ở Part 3 đã có public URL thật. Phần còn partial chủ yếu nằm ở runtime scaling của Part 5, do tại thời điểm ghi nhận chưa có đầy đủ bằng chứng multi-instance + Redis thật. Part 6 sẽ là bước ghép toàn bộ các mảnh này vào một final production agent hoàn chỉnh.
