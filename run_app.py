import os
import sys
import socket
import streamlit.web.cli as stcli

def is_port_in_use(port: int) -> bool:
    """Check if a local TCP port is already in use."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            return s.connect_ex(('127.0.0.1', port)) == 0
    except Exception:
        return False

def find_available_port(start_port: int = 8501) -> int:
    """Find the first available open port starting from start_port."""
    for port in range(start_port, start_port + 100):
        if not is_port_in_use(port):
            return port
    return 8501

def resolve_path(path: str) -> str:
    if getattr(sys, "frozen", False):
        base_path = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, path)

def main():
    if getattr(sys, "frozen", False):
        base_path = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))

    if base_path not in sys.path:
        sys.path.insert(0, base_path)

    app_path = resolve_path("app.py")
    port = find_available_port(8501)

    sys.argv = [
        "streamlit",
        "run",
        app_path,
        "--global.developmentMode=false",
        "--server.headless=false",
        "--browser.gatherUsageStats=false",
        f"--server.port={port}",
    ]
    sys.exit(stcli.main())

if __name__ == "__main__":
    main()
