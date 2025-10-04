# build_tiles_from_sentinel.py
import os, sys, subprocess, tempfile
from pathlib import Path
from shapely.geometry import box
from datetime import datetime
from tqdm import tqdm

from pystac_client import Client
import planetary_computer as pc
import rasterio
from rasterio.merge import merge

# ======== 可改参数 ========
OUT_DIR = r"C:\Users\hyh14\Desktop\xzdxbl_webgis_20251002\basemap"  # 瓦片输出根目录
# 苏州小范围（来自你之前日志，可自行扩大/缩小）
BBOX = (120.6456661, 31.4615233, 120.6501724, 31.4653913)  # W, S, E, N
TIME = "2024-05-01/2024-08-31"   # 时间范围
CLOUDY = 20                      # 云量上限（%）
Z_MIN, Z_MAX = 16, 20            # 切瓦片层级（高缩放谨慎）
RESAMPLING = "bilinear"          # gdal2tiles 重采样：nearest/bilinear/cubic/lanczos
IMG_EXT = ".png"                 # 输出瓦片格式（由 gdal2tiles 决定后缀；保持 .png）
# =========================

def ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)

def run(cmd):
    print("> " + " ".join(map(str, cmd)))
    subprocess.check_call(cmd)

def download_visual_assets(tmp_dir: Path):
    client = Client.open("https://planetarycomputer.microsoft.com/api/stac/v1")
    geom = box(*BBOX)
    search = client.search(
        collections=["sentinel-2-l2a"],
        intersects=geom.__geo_interface__,
        datetime=TIME,
        query={"eo:cloud_cover": {"lt": CLOUDY}}
    )
    items = list(search.get_items())
    if not items:
        print("No Sentinel-2 items matched your query."); sys.exit(2)

    out_paths = []
    for it in tqdm(items, desc="Downloading S2 visual assets"):
        signed = pc.sign(it)
        if "visual" not in signed.assets:
            continue
        href = signed.assets["visual"].href
        out_tif = tmp_dir / f"{it.id}_visual.tif"
        run(["gdal_translate", href, str(out_tif), "-of", "GTiff"])
        out_paths.append(out_tif)
    if not out_paths:
        print("Found items but no 'visual' assets."); sys.exit(3)
    return out_paths

def mosaic_to_geotiff(inputs, mosaic_path):
    srcs = [rasterio.open(p) for p in inputs]
    mosaic, transform = merge(srcs)
    meta = srcs[0].meta.copy()
    meta.update(driver="GTiff", height=mosaic.shape[1], width=mosaic.shape[2], transform=transform)
    with rasterio.open(mosaic_path, "w", **meta) as dst:
        dst.write(mosaic)
    for s in srcs: s.close()

def gdal2tiles_xyz(src_tif: Path, out_dir: Path, zmin: int, zmax: int, resampling: str):
    ensure_dir(out_dir)
    # --xyz 强制 XYZ（非 TMS）；某些 GDAL 旧版本没有该参数，如报错请升级 GDAL。
    cmd = [
        "gdal2tiles.py",
        "-z", f"{zmin}-{zmax}",
        "-r", resampling,
        "--xyz",
        "-w", "none",
        str(src_tif),
        str(out_dir)
    ]
    run(cmd)

def main():
    ensure_dir(Path(OUT_DIR))
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        # 1) 下载 visual 真彩
        files = download_visual_assets(tmp)
        # 2) 拼接
        mosaic_tif = tmp / "mosaic.tif"
        print("Mosaicking ...")
        mosaic_to_geotiff(files, mosaic_tif)
        # 3) 切瓦片（XYZ）
        print(f"Tiling → {OUT_DIR} (z={Z_MIN}..{Z_MAX}) ...")
        gdal2tiles_xyz(mosaic_tif, Path(OUT_DIR), Z_MIN, Z_MAX, RESAMPLING)
    print("Done. Tiles at:", OUT_DIR)

if __name__ == "__main__":
    main()
