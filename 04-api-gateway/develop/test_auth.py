import json
import os
import sys
import urllib.error
import urllib.request


BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
API_KEY = os.getenv("AGENT_API_KEY", "my-secret-key")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def request_json(path: str, *, api_key: str | None = None, body: dict | None = None):
    data = None
    headers = {}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if api_key is not None:
        headers["X-API-Key"] = api_key

    req = urllib.request.Request(f"{BASE_URL}{path}", data=data, headers=headers, method="POST" if body is not None else "GET")
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8")


def assert_status(label: str, actual: int, expected: int):
    if actual != expected:
        raise AssertionError(f"{label}: expected {expected}, got {actual}")


def main():
    health_status, health_body = request_json("/health")
    assert_status("health", health_status, 200)

    no_key_status, no_key_body = request_json("/ask", body={"question": "hello"})
    assert_status("no_key", no_key_status, 401)

    bad_key_status, bad_key_body = request_json("/ask", api_key="wrong-key", body={"question": "hello"})
    assert_status("bad_key", bad_key_status, 401)

    ok_status, ok_body = request_json("/ask", api_key=API_KEY, body={"question": "hello"})
    assert_status("valid_key", ok_status, 200)

    print("PASS develop auth")
    print(f"health={health_body}")
    print(f"no_key={no_key_body}")
    print(f"bad_key={bad_key_body}")
    print(f"valid_key={ok_body}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # pragma: no cover - helper script
        print(f"FAIL develop auth: {exc}")
        sys.exit(1)
