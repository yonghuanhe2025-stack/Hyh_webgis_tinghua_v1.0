# main.py
import os
import sys
import time
import shutil
import threading
import webbrowser
import socket
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

PORT = int(os.getenv("PORT", 8000))
WEB_DIR = os.path.abspath(os.path.dirname(__file__))

def _purge_py_caches(root: str) -> None:
    """删除 __pycache__ 目录与 *.pyc 缓存文件。"""
    for dirpath, dirnames, filenames in os.walk(root):
        if "__pycache__" in dirnames:
            shutil.rmtree(os.path.join(dirpath, "__pycache__"), ignore_errors=True)
        for fn in filenames:
            if fn.endswith(".pyc"):
                try:
                    os.remove(os.path.join(dirpath, fn))
                except OSError:
                    pass

class NoCacheHandler(SimpleHTTPRequestHandler):
    """强制禁用缓存的静态服务器处理器。"""
    def end_headers(self):
        # 彻底禁止缓存
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        self.send_header("Vary", "Accept-Encoding")
        super().end_headers()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=WEB_DIR, **kwargs)

def start_server(stop_event: threading.Event):
    ThreadingHTTPServer.allow_reuse_address = True
    with ThreadingHTTPServer(("", PORT), NoCacheHandler) as httpd:
        try:
            hostname = socket.gethostname()
            lan_ip = socket.gethostbyname(hostname)
        except Exception:
            lan_ip = "127.0.0.1"

        print("Serving at:")
        print(f"  http://localhost:{PORT}")
        print(f"  http://{lan_ip}:{PORT}")
        sys.stdout.flush()

        while not stop_event.is_set():
            httpd.handle_request()

if __name__ == "__main__":
    # 1) 清理 Python 字节码缓存
    _purge_py_caches(WEB_DIR)

    # 2) 启动服务器
    stop_event = threading.Event()
    t = threading.Thread(target=start_server, args=(stop_event,), daemon=True)
    t.start()

    # 3) 打开浏览器，并带时间戳避免历史缓存
    ts = int(time.time() * 1000)
    webbrowser.open(f"http://localhost:{PORT}/index.html?_={ts}")

    # 4) 友好退出
    try:
        input("按回车键退出服务器...\n")
    except KeyboardInterrupt:
        pass
    finally:
        stop_event.set()
        time.sleep(0.2)
        print("服务器已关闭。")
