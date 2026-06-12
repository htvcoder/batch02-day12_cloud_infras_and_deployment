import argparse
import json
import os
import sys
import urllib.error
import urllib.request


BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def request_json(path: str, *, method: str = "GET", token: str | None = None, body: dict | None = None):
    data = None
    headers = {}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"

    req = urllib.request.Request(f"{BASE_URL}{path}", data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, resp.read().decode("utf-8"), dict(resp.headers.items())
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8"), dict(exc.headers.items())


def get_token(username: str = "student", password: str = "demo123") -> str:
    status, body, _headers = request_json(
        "/auth/token",
        method="POST",
        body={"username": username, "password": password},
    )
    if status != 200:
        raise RuntimeError(f"token request failed: HTTP {status} body={body}")
    payload = json.loads(body)
    return payload["access_token"]


def run_smoke():
    token = get_token()
    status, body, _headers = request_json(
        "/ask",
        method="POST",
        token=token,
        body={"question": "what is docker?"},
    )
    if status != 200:
        raise RuntimeError(f"ask with token failed: HTTP {status} body={body}")

    missing_status, missing_body, _headers = request_json(
        "/ask",
        method="POST",
        body={"question": "what is docker?"},
    )
    if missing_status != 401:
        raise RuntimeError(f"ask without token expected 401, got {missing_status} body={missing_body}")

    print("PASS production smoke")
    print(body)


def run_rate_limit():
    token = get_token()
    hit_429 = False
    for i in range(1, 21):
        status, body, headers = request_json(
            "/ask",
            method="POST",
            token=token,
            body={"question": f"rate limit test {i}"},
        )
        if status == 429:
            hit_429 = True
            print(f"PASS rate limit at request {i}")
            print(body)
            retry_after = headers.get("Retry-After")
            if retry_after:
                print(f"Retry-After={retry_after}")
            break
        if status != 200:
            raise RuntimeError(f"unexpected status at request {i}: HTTP {status} body={body}")

    if not hit_429:
        raise RuntimeError("rate limit test did not hit 429 within 20 requests")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--test", choices=["smoke", "rate-limit"], default="smoke")
    args = parser.parse_args()

    if args.test == "smoke":
        run_smoke()
    elif args.test == "rate-limit":
        run_rate_limit()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # pragma: no cover - helper script
        print(f"FAIL production advanced: {exc}")
        sys.exit(1)
