#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
一键下载 three.js r146 非模块版所需文件（GLTF/GLB 查看器）+ Draco 解码器
- 下载到当前工作目录（或通过 --out 指定输出目录）
- 先尝试 GitHub Raw，失败自动切换到 jsDelivr
- 自动创建 ./draco/ 并放置解码器文件
"""
import os
import sys
import time
import hashlib
import argparse
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

R = "r146"

# 目标文件与多镜像 URL（按顺序尝试）
FILES = {
    "three.min.js": [
        f"https://raw.githubusercontent.com/mrdoob/three.js/{R}/build/three.min.js",
        f"https://cdn.jsdelivr.net/gh/mrdoob/three.js@{R}/build/three.min.js",
    ],
    "OrbitControls.js": [
        f"https://raw.githubusercontent.com/mrdoob/three.js/{R}/examples/js/controls/OrbitControls.js",
        f"https://cdn.jsdelivr.net/gh/mrdoob/three.js@{R}/examples/js/controls/OrbitControls.js",
    ],
    "GLTFLoader.js": [
        f"https://raw.githubusercontent.com/mrdoob/three.js/{R}/examples/js/loaders/GLTFLoader.js",
        f"https://cdn.jsdelivr.net/gh/mrdoob/three.js@{R}/examples/js/loaders/GLTFLoader.js",
    ],
    "DRACOLoader.js": [
        f"https://raw.githubusercontent.com/mrdoob/three.js/{R}/examples/js/loaders/DRACOLoader.js",
        f"https://cdn.jsdelivr.net/gh/mrdoob/three.js@{R}/examples/js/loaders/DRACOLoader.js",
    ],
    # Draco 解码器（非模块版目录）
    os.path.join("draco", "draco_decoder.js"): [
        f"https://raw.githubusercontent.com/mrdoob/three.js/{R}/examples/js/libs/draco/draco_decoder.js",
        f"https://cdn.jsdelivr.net/gh/mrdoob/three.js@{R}/examples/js/libs/draco/draco_decoder.js",
    ],
    os.path.join("draco", "draco_wasm_wrapper.js"): [
        f"https://raw.githubusercontent.com/mrdoob/three.js/{R}/examples/js/libs/draco/draco_wasm_wrapper.js",
        f"https://cdn.jsdelivr.net/gh/mrdoob/three.js@{R}/examples/js/libs/draco/draco_wasm_wrapper.js",
    ],
    os.path.join("draco", "draco_decoder.wasm"): [
        f"https://raw.githubusercontent.com/mrdoob/three.js/{R}/examples/js/libs/draco/draco_decoder.wasm",
        f"https://cdn.jsdelivr.net/gh/mrdoob/three.js@{R}/examples/js/libs/draco/draco_decoder.wasm",
    ],
}

UA = "Mozilla/5.0 (X11; Linux x86_64) PythonDownloader/1.0"
TIMEOUT = 30
RETRIES = 2  # 每个镜像的重试次数

def human(n):
    for u in ["B","KB","MB","GB","TB"]:
        if n < 1024:
            return f"{n:.1f}{u}"
        n /= 1024
    return f"{n:.1f}PB"

def fetch(url, timeout=TIMEOUT):
    req = Request(url, headers={"User-Agent": UA})
    with urlopen(req, timeout=timeout) as resp:
        data = resp.read()
        return data, resp.getheader("Content-Length")

def download_one(out_path, urls):
    # 确保父目录存在
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)

    last_err = None
    for mirror_idx, url in enumerate(urls):
        for attempt in range(1, RETRIES + 2):
            try:
                print(f"[down] {url}  (try {attempt}/{RETRIES+1})")
                data, clen = fetch(url)
                size = len(data)
                # 可选校验：如果提供了 Content-Length，做一次比对
                if clen is not None and clen.isdigit():
                    if int(clen) != size:
                        raise IOError(f"Size mismatch: got {size}, expect {clen}")
                with open(out_path, "wb") as f:
                    f.write(data)
                sha = hashlib.sha256(data).hexdigest()[:12]
                print(f"[ ok ] {out_path}  {human(size)}  sha256:{sha}\n")
                return True
            except (URLError, HTTPError, IOError) as e:
                last_err = e
                print(f"[warn] {type(e).__name__}: {e}")
                if attempt <= RETRIES:
                    time.sleep(1.2 * attempt)
                else:
                    print(f"[fail] mirror {mirror_idx+1} failed, trying next mirror...\n")
                    break
    print(f"[ERR ] give up {out_path}. Last error: {last_err}\n")
    return False

def main():
    ap = argparse.ArgumentParser(description="Download three.js r146 assets (non-module) + Draco decoders")
    ap.add_argument("--out", default=".", help="Output directory (default: current dir)")
    args = ap.parse_args()

    out_dir = os.path.abspath(args.out)
    os.makedirs(out_dir, exist_ok=True)
    print(f"Output directory: {out_dir}\n")

    ok_all = True
    for rel, urls in FILES.items():
        out_path = os.path.join(out_dir, rel)
        ok = download_one(out_path, urls)
        ok_all = ok_all and ok

    if ok_all:
        print("All files downloaded successfully.")
        print("\n使用提示：")
        print("1) 将生成的 HTML 与上述文件置于同一目录（含 ./draco/）。")
        print("2) 在代码中：dracoLoader.setDecoderPath('./draco/'); 并保持文件名一致。")
        print("3) 如需本地服务器：python -m http.server 8000")
        sys.exit(0)
    else:
        print("Some files failed to download. 请检查网络或稍后重试。")
        sys.exit(2)

if __name__ == "__main__":
    main()
