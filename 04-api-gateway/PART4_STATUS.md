# Part 4 Status - API Gateway & Security

## 1. Summary

- Overall status: Hoàn thành develop và production ở mức local test
- Last checked: 2026-06-12
- Files changed:
  - `04-api-gateway/develop/app.py`
  - `04-api-gateway/develop/test_auth.py`
  - `04-api-gateway/production/app.py`
  - `04-api-gateway/production/test_advanced.py`
  - `MISSION_ANSWERS.md`
  - `04-api-gateway/PART4_STATUS.md`

## 2. Develop - API Key Auth

- Local test: Pass
- API key source: `AGENT_API_KEY` từ environment variable, có fallback demo trong code
- Header used: `X-API-Key`
- No key returns: `401`
- Invalid key returns: `401`
- Valid key returns: `200`
- Health endpoint: Có `GET /health`
- Ask endpoint: Có `POST /ask`
- Notes:
  - Ban đầu repo thiếu `test_auth.py` dù README có nhắc
  - Ban đầu `/ask` nhận `question` qua query parameter nên test JSON body theo README bị `422`
  - Đã sửa tối thiểu để `/ask` nhận JSON body đúng như README mong đợi

## 3. Production - JWT + Rate Limiting + Cost Guard

- JWT token test: Pass
- Protected ask endpoint: Pass
- Rate limit test: Pass
- Cost guard test: Pass ở mức module-level
- Notes:
  - Endpoint lấy token là `POST /auth/token`
  - Demo credentials trong code:
    - `student / demo123`
    - `teacher / teach456`
  - Protected endpoint dùng `Authorization: Bearer <token>`
  - Ban đầu middleware security headers gây `500` vì gọi `response.headers.pop(...)`
  - Đã sửa tối thiểu để bỏ header `server` an toàn hơn
  - Rate limiter là in-memory sliding window theo `username` từ JWT
  - Cost guard là in-memory, chưa dùng Redis hay database

## 4. Remaining issues

- README mô tả `test_auth.py` và `test_advanced.py`, nhưng repo ban đầu bị thiếu hai file này
- `develop/.venv` hiện không có sẵn dependency như global Python, nên nếu chạy bằng Python trong `.venv` cũ có thể gặp lỗi import
- Cost guard chưa được hit trực tiếp qua API với budget mặc định, vì mock request quá rẻ; hiện đã xác nhận bằng test trực tiếp ở mức module
- Một số lệnh `curl.exe -d ...` trong PowerShell có thể làm hỏng JSON body nếu quote không đúng, nên `Invoke-RestMethod` hoặc script Python ổn định hơn

## 5. Recommended next step

- Có thể xem Part 4 đã hoàn thành ở mức lab local
- Nếu muốn làm sạch hơn nữa, người dùng có thể:
  - Tạo `.venv` nhất quán cho `develop` và `production`
  - Nếu muốn demo cost guard qua API, hạ budget demo hoặc thêm test mode riêng
  - Sau đó mới chuyển sang Part 5, không cần sửa thêm Part 4 trừ khi muốn polish môi trường chạy
