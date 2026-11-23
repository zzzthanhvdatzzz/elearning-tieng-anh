"""Chạy API bằng HTTPS tự ký — cần thiết để test ghi âm trên điện thoại (rủi ro R2).

    ~/.venv-docx/bin/python scripts/run_https.py        # sinh cert (nếu chưa có) rồi chạy 8443
    # hoặc: .venv/bin/python scripts/run_https.py

Trình duyệt trên điện thoại sẽ cảnh báo "không an toàn" → chọn "Vẫn tiếp tục" là dùng được micro.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CERT_DIR = ROOT / "data" / "certs"
CERT = CERT_DIR / "local.crt"
KEY = CERT_DIR / "local.key"


def ensure_cert() -> tuple[Path, Path]:
    CERT_DIR.mkdir(parents=True, exist_ok=True)
    if CERT.exists() and KEY.exists():
        return CERT, KEY

    # SAN phải có cả localhost và IP LAN, nếu không điện thoại vẫn báo không bảo mật.
    import socket

    san = ["DNS:localhost", "IP:127.0.0.1"]
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        lan_ip = s.getsockname()[0]
        s.close()
        if lan_ip not in ("127.0.0.1", "0.0.0.0"):
            san.append(f"IP:{lan_ip}")
            print(f"Đã thêm IP LAN {lan_ip} vào chứng chỉ")
    except OSError:
        pass

    subprocess.run([
        "openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes",
        "-keyout", str(KEY), "-out", str(CERT), "-days", "365",
        "-subj", "/CN=elearning.local",
        "-addext", "subjectAltName=" + ",".join(san),
    ], check=True, capture_output=True)
    return CERT, KEY


def main() -> None:
    cert, key = ensure_cert()
    port = sys.argv[1] if len(sys.argv) > 1 else "8443"

    print(f"Certificate: {cert}")
    print(f"Mở https://localhost:{port} — điện thoại trong cùng mạng dùng https://<IP-LAN>:{port}")
    print("Lần đầu trình duyệt cảnh báo chứng chỉ tự ký: chọn 'Vẫn tiếp tục' thì micro mới chạy.")

    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=int(port),
                ssl_certfile=str(cert), ssl_keyfile=str(key))


if __name__ == "__main__":
    main()
