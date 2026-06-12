# Deployment Information

## Public URL

https://day12-cloud-deployment-part3-production.up.railway.app

## Platform

Railway

## Status

- Railway deploy thật: Thành công
- Render: Review/config only, chưa deploy
- Cloud Run: Review only, chưa deploy

## Test Commands

### Health Check

```powershell
$URL="https://day12-cloud-deployment-part3-production.up.railway.app"
curl.exe "$URL/health"
```

Expected result:

```json
{"status":"ok","uptime_seconds":549.5,"platform":"Railway","timestamp":"2026-06-12T15:25:05.902317+00:00"}
```

### API Test

```powershell
$URL="https://day12-cloud-deployment-part3-production.up.railway.app"
Invoke-RestMethod `
  -Uri "$URL/ask" `
  -Method Post `
  -ContentType "application/json" `
  -Body '{"question":"Hello from Railway"}'
```

Observed result:

```text
question: Hello from Railway
answer: AI agent đã được deploy lên cloud. Câu hỏi của bạn là: Hello from Railway
platform: Railway
```

## Notes

- Endpoint `/health` đã trả `200 OK`.
- Endpoint `/ask` đã gọi thành công bằng `Invoke-RestMethod`.
- Trong PowerShell, tiếng Việt có thể hiển thị lỗi encoding, nhưng API đã trả đúng dữ liệu.
- Không có secret nào được thêm vào repo trong lần cập nhật này.
