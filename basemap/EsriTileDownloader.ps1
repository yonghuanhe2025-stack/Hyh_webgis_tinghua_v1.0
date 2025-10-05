<#
  EsriTileDownloader_optimized.ps1
  Purpose: Download Esri World_Imagery tiles to {Out}\{z}\{x}\{y}.jpg

  Works on:
    - Windows PowerShell 5.1+（PS7+ 支持并行 ForEach-Object -Parallel）

  Features:
    - Resume-friendly: 跳过已存在且非空的文件
    - 自动重试 + 指数退避；失败 URL 存入 failed_tiles.txt
    - 进度条（Write-Progress）+ 简易速率估计
    - 可选并行（PS7+：-Concurrency）
    - 可选 Y 翻转（-FlipY）适配 TMS
    - 经纬度范围裁剪（-West -South -East -North），未提供则默认整个地球（高等级极不建议）
    - PS5 使用 Invoke-WebRequest -UseBasicParsing，避免兼容性问题

  Example (建议小范围 + 高级别):
    powershell -ExecutionPolicy Bypass -File .\EsriTileDownloader_optimized.ps1 `
      -Out Esri_map -MinZ 16 -MaxZ 19 -Concurrency 8 -Retry 3 -DelayMs 30 `
      -West 120.6457 -South 31.4615 -East 120.6502 -North 31.4654
#>

param(
  [string]$UserAgent = 'YourProject/1.0',
  [string]$Out = 'Esri_map',
  [int]$MinZ = 0,
  [int]$MaxZ = 5,
  [int]$Retry = 3,
  [int]$DelayMs = 20,
  [int]$Concurrency = 8,
  [switch]$FlipY,

  # 可选：经纬度范围（WGS84，度），四个都给才生效；否则下载全世界
  [double]$West,
  [double]$South,
  [double]$East,
  [double]$North
)

# ---- Global setup ----
try { [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12 } catch {}
try {
  [System.Net.ServicePointManager]::DefaultConnectionLimit =
    [math]::Max([System.Net.ServicePointManager]::DefaultConnectionLimit, 256)
} catch {}

$IsPS7 = $PSVersionTable.PSVersion.Major -ge 7
$UseBasicParsing = $PSVersionTable.PSVersion.Major -lt 6

# Esri World_Imagery URL template (XYZ schema)
function Get-TileUrl([int]$z,[int]$x,[int]$y){
  "https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/$z/$y/$x"
}

# Ensure directory exists
function Ensure-Dir([string]$path){
  if(-not (Test-Path -LiteralPath $path)){
    New-Item -ItemType Directory -Force -Path $path | Out-Null
  }
}

Ensure-Dir -path $Out

# lon/lat -> XYZ tile indices
function Get-TileX {
  param([double]$lon, [int]$z)
  return [int][math]::Floor( ($lon + 180.0) / 360.0 * [math]::Pow(2,$z) )
}
function Get-TileY {
  param([double]$lat, [int]$z)
  $latRad = $lat * [math]::PI / 180.0
  $n = [math]::Pow(2,$z)
  $val = (1.0 - [math]::Log( [math]::Tan($latRad) + 1.0/[math]::Cos($latRad) ) / [math]::PI) / 2.0 * $n
  # clamp
  $val = [math]::Max(0, [math]::Min($val, $n-1))
  return [int][math]::Floor($val)
}

# ---- Build job list (支持全世界 / 经纬度裁剪 / 跨国际换日线拆段) ----
$jobs = New-Object System.Collections.Generic.List[object]

$HasBBox = ($PSBoundParameters.ContainsKey('West') -and
            $PSBoundParameters.ContainsKey('South') -and
            $PSBoundParameters.ContainsKey('East') -and
            $PSBoundParameters.ContainsKey('North'))

for($z=$MinZ; $z -le $MaxZ; $z++){
  $n = [math]::Pow(2,$z)

  if($HasBBox){
    # 处理经度跨 180 度：East < West 视为跨线，拆成两段 [West..180] + [-180..East]
    $segments = @()
    if($East -ge $West){
      $segments += @{ West=$West; East=$East }
    } else {
      $segments += @{ West=$West; East=180.0 }
      $segments += @{ West=-180.0; East=$East }
    }

    # 计算 Y 范围（纬度反向：北->小Y，南->大Y）
    $yMin = Get-TileY -lat $North -z $z
    $yMax = Get-TileY -lat $South -z $z
    if($yMin -gt $yMax){ $t=$yMin; $yMin=$yMax; $yMax=$t }

    foreach($seg in $segments){
      $xMin = Get-TileX -lon $seg.West -z $z
      $xMax = Get-TileX -lon $seg.East -z $z

      # clamp + 排序
      $xMin = [int][math]::Max(0, [math]::Min($xMin, $n-1))
      $xMax = [int][math]::Max(0, [math]::Min($xMax, $n-1))
      if($xMin -gt $xMax){ $t=$xMin; $xMin=$xMax; $xMax=$t }

      for($x=$xMin; $x -le $xMax; $x++){
        for($y=$yMin; $y -le $yMax; $y++){
          $yy  = if($FlipY){ [int]($n-1-$y) } else { $y }
          $dir = Join-Path $Out (Join-Path $z $x)
          $file= Join-Path $dir ("{0}.jpg" -f $yy)
          $url = Get-TileUrl -z $z -x $x -y $y
          $jobs.Add([pscustomobject]@{ Z=$z; X=$x; Y=$y; YY=$yy; Dir=$dir; File=$file; Url=$url }) | Out-Null
        }
      }
    }
  }
  else{
    # 没有范围 => 全世界（注意：高等级瓦片数量极其巨大，不建议）
    for($x=0; $x -lt $n; $x++){
      for($y=0; $y -lt $n; $y++){
        $yy  = if($FlipY){ [int]($n-1-$y) } else { $y }
        $dir = Join-Path $Out (Join-Path $z $x)
        $file= Join-Path $dir ("{0}.jpg" -f $yy)
        $url = Get-TileUrl -z $z -x $x -y $y
        $jobs.Add([pscustomobject]@{ Z=$z; X=$x; Y=$y; YY=$yy; Dir=$dir; File=$file; Url=$url }) | Out-Null
      }
    }
  }
}

$total  = $jobs.Count
$start  = Get-Date
$failed = New-Object System.Collections.Concurrent.ConcurrentBag[string]
$script:done = 0

# ---- Download function ----
function Invoke-Download {
  param([pscustomobject]$job, [string]$UserAgent, [bool]$UseBasicParsing, [bool]$IsPS7, [int]$DelayMs, [int]$Retry)

  try { Ensure-Dir -path $job.Dir } catch {}

  # Skip existing non-empty file
  if(Test-Path -LiteralPath $job.File){
    try {
      $info = Get-Item -LiteralPath $job.File -ErrorAction SilentlyContinue
      if($info -and $info.Length -gt 0){ return $true }
    } catch {}
  }

  $ok = $false
  for($attempt=1; $attempt -le [Math]::Max(1,$Retry); $attempt++){
    try{
      $splat = @{
        Uri = $job.Url
        OutFile = $job.File
        Headers = @{ 'User-Agent' = $UserAgent }
        TimeoutSec = 30
        ErrorAction = 'Stop'
      }
      if($UseBasicParsing){ Invoke-WebRequest @splat -UseBasicParsing } else { Invoke-WebRequest @splat }
      $ok = $true; break
    }catch{
      if($attempt -lt $Retry){
        $backoff = [int][math]::Min(5000, 150 * [math]::Pow(2, $attempt-1))
        Start-Sleep -Milliseconds $backoff
      }
    }
  }

  if(-not $ok){
    $failed.Add($job.Url) | Out-Null
  }

  if($DelayMs -gt 0 -and -not $IsPS7){
    Start-Sleep -Milliseconds $DelayMs   # 顺序模式的小延时，减轻压力
  }
  return $ok
}

# ---- Execute downloads ----
if($IsPS7 -and $Concurrency -gt 1){
  $throttle = [Math]::Max(1,$Concurrency)
  $jobs | ForEach-Object -Parallel {
    # 每个并行 runspace 都有自己的作用域，参数通过 $using: 传入
    $null = Invoke-Download -job $_ -UserAgent $using:UserAgent -UseBasicParsing $using:UseBasicParsing `
                            -IsPS7 $using:IsPS7 -DelayMs $using:DelayMs -Retry $using:Retry
    [System.Threading.Interlocked]::Increment([ref]$using:script:done) | Out-Null
    if(($using:script:done % 127) -eq 0){
      $pct = [int](100 * $using:script:done / $using:total)
      $elapsed = (Get-Date) - $using:start
      $rate = if($elapsed.TotalSeconds -gt 0){ [int]($using:script:done / $elapsed.TotalSeconds) } else { 0 }
      Write-Progress -Activity "Downloading Esri tiles (parallel)" `
        -Status ("{0}/{1}  {2}%  ~{3}/s" -f $using:script:done, $using:total, $pct, $rate) `
        -PercentComplete $pct
    }
  } -ThrottleLimit $throttle
}
else{
  foreach($j in $jobs){
    $null = Invoke-Download -job $j -UserAgent $UserAgent -UseBasicParsing $UseBasicParsing `
                            -IsPS7 $IsPS7 -DelayMs $DelayMs -Retry $Retry
    $script:done++
    if(($script:done % 64) -eq 0){
      $pct = [int](100 * $script:done / $total)
      $elapsed = (Get-Date) - $start
      $rate = if($elapsed.TotalSeconds -gt 0){ [int]($script:done / $elapsed.TotalSeconds) } else { 0 }
      Write-Progress -Activity "Downloading Esri tiles (sequential)" `
        -Status ("{0}/{1}  {2}%  ~{3}/s" -f $script:done, $total, $pct, $rate) `
        -PercentComplete $pct
    }
  }
}

# ---- Finish ----
if($failed.Count -gt 0){
  $failPath = Join-Path $Out "failed_tiles.txt"
  $failed | Sort-Object -Unique | Out-File -FilePath $failPath -Encoding UTF8
  Write-Host ("Completed with {0} failed tiles. List saved to: {1}" -f $failed.Count, (Resolve-Path $failPath)) -ForegroundColor Yellow
}else{
  Write-Host ("All done. Output directory: {0}" -f (Resolve-Path -LiteralPath $Out)) -ForegroundColor Green
}
