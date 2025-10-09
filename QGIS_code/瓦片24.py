# === Paste & Run (QGIS Python Console) ===
import os, sys, subprocess, time, math
from pathlib import Path
from datetime import datetime

# ---- 修改这里 ----
input_tif = r"F:\外包\xzdxbl_webgis_20251002\无人机采集样本\DOM01\DOM_DOM.tif"
out_dir   = r"F:\外包\xzdxbl_webgis_20251002\map\test"
zoom      = "0-19"          # 验证用 24；没问题再改 "20-24" 或 "0-24"
tile_driver = "PNG"      # 或 "PNG"
# -------------------

tile_size   = "256"
resampling  = "bilinear"
processes   = "0"
resume      = True
webviewer   = "none"
use_xyz     = True
s_srs       = None        # 例如 "EPSG:4490"；无则留 None
poll_s      = 1.0

def resolve_qgis_python() -> str:
    exe = Path(sys.executable)
    nm = exe.name.lower()
    if nm.endswith("qgis-ltr-bin.exe") or nm.endswith("qgis-bin.exe"):
        py = exe.with_name("python3.exe")
        if py.exists(): return str(py)
        bat = exe.with_name("python-qgis-ltr.bat")
        if bat.exists(): return str(bat)
    return str(sys.executable)

def parse_zoom(zs:str):
    zs = str(zs).strip()
    if "-" in zs:
        a,b = zs.split("-",1); a=int(a); b=int(b)
        return list(range(min(a,b), max(a,b)+1))
    return [int(zs)]

def estimate_total_tiles(tif_path:Path, zooms):
    try:
        from osgeo import gdal, osr
        ds = gdal.Open(str(tif_path))
        if ds is None: return None
        gt = ds.GetGeoTransform(); w,h = ds.RasterXSize, ds.RasterYSize
        x0,y0 = gt[0],gt[3]; x1 = x0+gt[1]*w+gt[2]*h; y1 = y0+gt[4]*w+gt[5]*h
        minx,maxx=min(x0,x1),max(x0,x1); miny,maxy=min(y0,y1),max(y0,y1)
        s=osr.SpatialReference(); wkt=ds.GetProjection()
        if not wkt: return None
        s.ImportFromWkt(wkt); t=osr.SpatialReference(); t.ImportFromEPSG(4326)
        ct=osr.CoordinateTransformation(s,t)
        def clamp_lat(lat): return max(min(lat,85.05112878),-85.05112878)
        corners=[(minx,miny),(minx,maxy),(maxx,miny),(maxx,maxy)]
        lls=[]
        for x,y in corners:
            lon,lat,_=ct.TransformPoint(float(x),float(y))
            lat=clamp_lat(lat); lon=((lon+180)%360)-180; lls.append((lon,lat))
        min_lon=min(p[0] for p in lls); max_lon=max(p[0] for p in lls)
        min_lat=min(p[1] for p in lls); max_lat=max(p[1] for p in lls)
        def lonlat_to_tilexy(lon,lat,z):
            n=2**z; x=int((lon+180.0)/360.0*n); lr=math.radians(lat)
            y=int((1.0-math.log(math.tan(lr)+1/math.cos(lr))/math.pi)/2.0*n)
            return max(0,min(n-1,x)), max(0,min(n-1,y))
        total=0
        for z in zooms:
            x0,y0=lonlat_to_tilexy(min_lon,max_lat,z)
            x1,y1=lonlat_to_tilexy(max_lon,min_lat,z)
            xmin,xmax=min(x0,x1),max(x0,x1); ymin,ymax=min(y0,y1),max(y0,y1)
            total += max(0,xmax-xmin+1)*max(0,ymax-ymin+1)
        return total
    except Exception:
        return None

def count_tiles(d:Path, ext:str):
    c=0; ext=ext.lower()
    for root,_,files in os.walk(d):
        for f in files:
            if f.lower().endswith("."+ext): c+=1
    return c

def progress_line(done,total,elapsed,rate):
    if total and total>0:
        pct=done/total*100; width=30; filled=int(width*pct/100)
        bar="█"*filled+"·"*(width-filled)
        hh=int(elapsed//3600); mm=int((elapsed%3600)//60); ss=int(elapsed%60)
        s=f"\r[{bar}] {pct:5.1f}%  tiles {done}/{total}  {rate:6.1f}/s  elapsed {hh:02d}:{mm:02d}:{ss:02d}"
    else:
        sp="⠋⠙⠸⠴⠦⠇"; ch=sp[int(elapsed*5)%len(sp)]
        hh=int(elapsed//3600); mm=int((elapsed%3600)//60); ss=int(elapsed%60)
        s=f"\r{ch} tiles {done}  {rate:6.1f}/s  elapsed {hh:02d}:{mm:02d}:{ss:02d}"
    print(s, end="", flush=True)

# --- 准备 ---
tif=Path(input_tif); out=Path(out_dir); out.mkdir(parents=True, exist_ok=True)
if not tif.exists(): raise SystemExit(f"输入影像不存在：{tif}")
log=out/"gdal2tiles_log.txt"; lock=out/".dom2tile.lock"
if lock.exists(): raise SystemExit(f"检测到锁文件：{lock} （若上次已结束，删除它再运行）")
lock.write_text(f"PID={os.getpid()}\nTIME={datetime.now():%Y-%m-%d %H:%M:%S}\n", encoding="utf-8")

py = resolve_qgis_python()
cmd=[py,"-m","osgeo_utils.gdal2tiles","-z",str(zoom)]
if use_xyz: cmd.append("--xyz")
cmd+=["--tiledriver",tile_driver,"--processes",str(processes),
      "--resampling",resampling,"--tilesize",str(tile_size),
      "--webviewer",webviewer]
if resume: cmd.append("--resume")
if s_srs:  cmd+=["--s_srs",str(s_srs)]
cmd+=[str(tif),str(out)]

zooms=parse_zoom(zoom); total_est=estimate_total_tiles(tif,zooms)
print("i Estimated total tiles:" , total_est if total_est is not None else "unknown")
with open(log,"a",encoding="utf-8") as lf:
    lf.write(f"\n[{datetime.now():%Y-%m-%d %H:%M:%S}] ===== Run Start =====\n")
    lf.write("PY:  "+py+"\n"); lf.write("CMD: "+" ".join(cmd)+"\n")

print("▶ Launching gdal2tiles ...")
print("PY:",py); print("CMD:"," ".join(cmd))

start=time.time(); last_time=start; last_count=0; last_poll=0.0
ext="jpg" if tile_driver.upper()=="JPEG" else "png"
ret=1
try:
    with open(log,"a",encoding="utf-8") as lf:
        proc=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                              text=True,encoding="utf-8",errors="replace")
        while True:
            line=proc.stdout.readline()
            now=time.time()
            if line:
                msg=line.rstrip("\r\n"); lf.write(msg+"\n")
                if any(k in msg for k in ("Generating","Tile","Overview","Base","ERROR","WARNING")):
                    print("\n"+msg)
            if (now-last_poll)>=poll_s:
                done=count_tiles(out,ext)
                dt=max(1e-6, now-last_time); rate=(done-last_count)/dt
                progress_line(done,total_est, now-start, rate)
                last_poll=now; last_time=now; last_count=done
            if proc.poll() is not None:
                done=count_tiles(out,ext)
                dt=max(1e-6, time.time()-last_time); rate=(done-last_count)/dt
                progress_line(done,total_est, time.time()-start, rate)
                print()
                ret=proc.returncode; break
    if ret==0:
        print("✅ Done. Output:", out)
        print(fr"Example (XYZ): {out}\24\X\Y.{ext}")
    else:
        print(f"❌ gdal2tiles failed (exit {ret}). See log:", log)
finally:
    try: lock.unlink(missing_ok=True)
    except Exception: pass
