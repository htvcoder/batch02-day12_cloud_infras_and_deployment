# Part 5 Status

## Scope source

Part 5 này được đối chiếu từ:

- `PLAN.md`
- `CODE_LAB.md`
- root `README.md`
- source code thật trong `05-scaling-reliability/`

Không thấy README riêng cho Part 5 trong thư mục này, nên trạng thái bên dưới bám theo các file trên và code thực tế.

## Current status

Trạng thái hiện tại của Part 5 là: `local review + local smoke check done`, chưa chứng minh full Docker scaling runtime vì Docker daemon trên máy hiện tại không chạy.

## What is implemented in code

### Develop app

File: `05-scaling-reliability/develop/app.py`

- Có `GET /health`
- Có `GET /ready`
- Có graceful shutdown qua `lifespan` + signal handler `SIGTERM`/`SIGINT`
- Có tracking in-flight requests
- Có `uvicorn` graceful shutdown timeout

Ghi chú:

- Endpoint xử lý câu hỏi ở bản develop là `POST /ask`
- Route này nhận `question` qua query parameter, không phải JSON body

### Production app

File: `05-scaling-reliability/production/app.py`

- Có `GET /health`
- Có `GET /ready`
- Có thiết kế session dùng Redis khi Redis sẵn sàng
- Có nhiều endpoint stateless conversation:
  - `POST /chat`
  - `GET /chat/{session_id}/history`
  - `DELETE /chat/{session_id}`
- Có `served_by` để quan sát instance nào xử lý request
- Có `instance_id` trong health response

Ghi chú quan trọng:

- Production app không có `POST /ask`; code thực tế dùng `POST /chat`
- Nếu Redis không sẵn sàng hoặc module `redis` không có, app fallback sang in-memory store
- Fallback in-memory giúp app vẫn chạy local, nhưng khi đó không còn đúng nghĩa scalable/stateless giữa nhiều instances

## Local smoke-check evidence

### Python packages available on machine

Kiểm tra nhanh bằng `python -c` cho thấy:

- `fastapi`: có
- `uvicorn`: có
- `redis`: chưa có trong Python env hiện tại
- `psutil`: chưa có trong Python env hiện tại

Điều này vẫn đủ để import app production ở chế độ fallback in-memory, nhưng chưa đủ để chứng minh Redis-backed stateless runtime thật.

### Compose config validation

Sau khi sửa file trong repo, lệnh sau đã parse được compose config:

```bash
docker compose -f 05-scaling-reliability/production/docker-compose.yml config
```

Kết quả:

- Compose đã resolve được `Dockerfile`
- Không còn lỗi `.env.local not found`
- Vẫn còn warning ngoài repo:

```text
WARNING: Error loading config file: open C:\Users\Lenovo\.docker\config.json: Access is denied.
```

Warning này không phải lỗi cú pháp compose của repo.

### Develop smoke test

Chạy local bằng `FastAPI TestClient` và bật `PYTHONIOENCODING=utf-8` để tránh lỗi console Windows với tiếng Việt.

Kết quả:

- `GET /health` -> `200`
- `GET /ready` -> `200`
- `POST /ask?question=hello from develop` -> `200`

Response mẫu:

```text
health_json.status = ok
ready_json.ready = True
ask_json.answer = Agent đang hoạt động tốt! (mock response) Hỏi thêm câu hỏi đi nhé.
```

Ghi chú:

- Nếu không đi qua startup lifecycle hoặc không chờ app ready, `/ready` và `/ask` có thể tạm thời trả `503`, đúng với thiết kế readiness của app

### Production smoke test

Chạy local bằng `FastAPI TestClient` với `PYTHONIOENCODING=utf-8`.

Kết quả:

- `GET /health` -> `200`
- `GET /ready` -> `200`
- `POST /chat` -> `200`
- `GET /chat/{session_id}/history` -> `200`

Response mẫu:

```text
health_json.storage = in-memory
ready_json.ready = True
chat_json.served_by = instance-c9c76a
history_json.count = 2
```

Kết luận từ smoke test production:

- App production chạy được local
- Session/history hoạt động ở chế độ in-memory fallback
- Chưa chứng minh Redis-backed shared state thật vì Python env hiện tại chưa có package `redis` và Docker daemon chưa chạy

Ghi chú:

- Khi `redis` package không có, app rơi vào fallback branch
- Trên Windows console mặc định, thông báo fallback có emoji có thể gây lỗi encoding nếu không bật UTF-8

### Docker status

`docker --version` và `docker compose version` có sẵn, nhưng `docker info` lỗi:

```text
failed to connect to the docker API at npipe:////./pipe/docker_engine; check if the path is correct and if the daemon is running: open //./pipe/docker_engine: The system cannot find the file specified.
```

Ngoài ra Docker CLI còn cảnh báo:

```text
WARNING: Error loading config file: open C:\Users\Lenovo\.docker\config.json: Access is denied.
```

Theo đúng scope, mình không sửa Docker ngoài repo; vì vậy phần full runtime test với `docker compose up --scale agent=3` dừng ở mức review/config.

## Repo fixes applied for Part 5

Đã chỉnh trong repo để Part 5 khớp cấu trúc hơn:

- Thêm `05-scaling-reliability/production/requirements.txt`
- Thêm `05-scaling-reliability/production/Dockerfile`
- Sửa `05-scaling-reliability/production/docker-compose.yml`

Các lỗi cấu hình đã sửa:

- Build path cũ trỏ sai sang `05-scaling-reliability/advanced/Dockerfile`
- Có tham chiếu `.env.local` không tồn tại
- `docker compose` scaling nên dùng rõ ràng bằng `--scale agent=3`, không dựa vào `deploy.replicas`

## Requirement-by-requirement status

| Requirement | Status | Evidence |
| --- | --- | --- |
| Health check | PASS | `develop/app.py` và `production/app.py` đều có `GET /health` |
| Readiness check | PASS | `develop/app.py` và `production/app.py` đều có `GET /ready` |
| Graceful shutdown | PASS ở develop | Có signal handling trong `develop/app.py`; production chỉ có lifespan logging |
| Stateless design | PARTIAL | Production dùng Redis nếu có; fallback in-memory nếu Redis/module không sẵn |
| Shared state qua Redis | PARTIAL | Code có Redis path, nhưng local machine hiện chưa chứng minh runtime Redis thật |
| Multiple instances | CONFIG READY | Có `docker-compose.yml` + Nginx để scale qua `--scale agent=3` |
| Load balancing | CONFIG READY | `production/nginx.conf` proxy tới service `agent` |
| Test stateless | SCRIPT READY + single-instance local path PASS | Có `production/test_stateless.py`, nhưng chưa chạy full multi-instance vì Docker daemon down |

## Overall conclusion

Part 5 hiện đã:

- hoàn thành review toàn bộ code và config
- sửa các lỗi cấu hình rõ ràng trong production compose path
- xác nhận health/readiness/graceful shutdown ở mức source code
- xác nhận production app có hướng stateless dùng Redis

Part 5 chưa thể chốt `full runtime PASS` cho scaling demo trên máy hiện tại vì Docker daemon không chạy, nên chưa có bằng chứng thật cho:

- `docker compose up --build --scale agent=3`
- multi-instance load balancing runtime
- session continuity qua Redis khi kill instance
