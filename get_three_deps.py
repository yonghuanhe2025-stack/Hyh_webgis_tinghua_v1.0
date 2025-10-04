# get_three_deps.py
import os, sys, time, urllib.request

# 优先 r160；examples/js 在 r160 不存在 → 回退 r146（保留非模块 UMD 版本）
CORE_VERSION = "0.160.0"
CORE_TAG = "r160"
LEGACY_TAG = "r146"  # 存在 examples/js/controls/ 与 loaders/

UA = "xzdxbl-stl-downloader/1.1"

TARGETS = {
    "three.min.js": [
        f"https://cdn.jsdelivr.net/npm/three@{CORE_VERSION}/build/three.min.js",
        f"https://unpkg.com/three@{CORE_VERSION}/build/three.min.js",
        f"https://raw.githubusercontent.com/mrdoob/three.js/{CORE_TAG}/build/three.min.js",
    ],
    # OrbitControls：r160 的路径不存在 → 回退 r146 的非模块版本
    "OrbitControls.js": [
        f"https://raw.githubusercontent.com/mrdoob/three.js/{LEGACY_TAG}/examples/js/controls/OrbitControls.js",
        f"https://cdn.jsdelivr.net/gh/mrdoob/three.js@{LEGACY_TAG}/examples/js/controls/OrbitControls.js",
        f"https://unpkg.com/three@{LEGACY_TAG}/examples/js/controls/OrbitControls.js",
    ],
    # STLLoader 同理
    "STLLoader.js": [
        f"https://raw.githubusercontent.com/mrdoob/three.js/{LEGACY_TAG}/examples/js/loaders/STLLoader.js",
        f"https://cdn.jsdelivr.net/gh/mrdoob/three.js@{LEGACY_TAG}/examples/js/loaders/STLLoader.js",
        f"https://unpkg.com/three@{LEGACY_TAG}/examples/js/loaders/STLLoader.js",
    ],
}

def fetch(url, dst):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=25) as r, open(dst, "wb") as f:
        while True:
            chunk = r.read(8192)
            if not chunk: break
            f.write(chunk)

def download_one(name, urls, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, name)
    if os.path.exists(path) and os.path.getsize(path) > 0:
        print(f"[skip] {name} 已存在 ({os.path.getsize(path)} bytes)")
        return
    last_err = None
    for i, u in enumerate(urls, 1):
        try:
            print(f"[{name}] 尝试 {i}/{len(urls)}: {u}")
            fetch(u, path)
            size = os.path.getsize(path)
            if size == 0: raise IOError("0 bytes")
            print(f"[ok]  {name} 下载完成：{size} bytes -> {path}")
            return
        except Exception as e:
            last_err = e
            print(f"[warn] 源失败：{e}")
            time.sleep(0.5)
    raise SystemExit(f"[fail] {name} 所有源均失败：{last_err}")

def main():
    out_dir = sys.argv[1] if len(sys.argv) > 1 else "."
    print("输出目录：", os.path.abspath(out_dir))
    for fname, url_list in TARGETS.items():
        download_one(fname, url_list, out_dir)
    print("\n完成。将这三文件与 HTML 放同目录使用：three.min.js / OrbitControls.js / STLLoader.js")

if __name__ == "__main__":
    main()
