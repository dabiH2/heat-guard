<#
    assemble.ps1 — stitch the nine pitch takes into one video.

    Put T1.mp4 ... T9.mp4 in this folder, then run:   .\assemble.ps1

    Tries a lossless stream copy first (instant, no quality loss). If the copy drifts —
    which happens when a screen recorder writes variable frame rate — it falls back to a
    normalising re-encode automatically. Output: heatguard-pitch.mp4

    Nothing here touches the app or spends FortyGuard credits.
#>

[CmdletBinding()]
param(
    [string]$Out      = "heatguard-pitch.mp4",
    [string]$ListFile = "takes.txt",
    [double]$Expected = 180.2,      # the script's timed length, from the rehearsal player
    [switch]$ForceReencode
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

function Fail($m) { Write-Host "`n  ERROR  $m" -ForegroundColor Red; exit 1 }
function Warn($m) { Write-Host "  warn   $m" -ForegroundColor Yellow }
function OK($m)   { Write-Host "  ok     $m" -ForegroundColor Green }
function Hms([double]$s) { "{0}:{1:00.0}" -f [math]::Floor($s / 60), ($s % 60) }

Write-Host "`nHeatGuard — assembling the pitch video" -ForegroundColor Cyan
Write-Host ("-" * 62)

# ---------------------------------------------------------------- prerequisites
foreach ($tool in "ffmpeg", "ffprobe") {
    if (-not (Get-Command $tool -ErrorAction SilentlyContinue)) {
        Fail "$tool is not on PATH.`n         Install with:  winget install Gyan.FFmpeg`n         then open a NEW terminal. Or use Clipchamp — see recording-plan.md."
    }
}
if (-not (Test-Path $ListFile)) { Fail "$ListFile not found in $PSScriptRoot" }

# ---------------------------------------------------------------- read the list
$takes = Get-Content $ListFile |
         Where-Object { $_ -match "^\s*file\s+'(.+?)'" } |
         ForEach-Object { $Matches[1] }

if ($takes.Count -eq 0) { Fail "No 'file' entries found in $ListFile" }

$missing = $takes | Where-Object { -not (Test-Path $_) }
if ($missing) {
    Write-Host ""
    Fail ("These takes are missing from this folder:`n         " + ($missing -join "`n         ") +
          "`n`n         Record them, or edit $ListFile if you named the files differently.")
}

# ---------------------------------------------------------------- probe each take
Write-Host "`nProbing $($takes.Count) takes`n" -ForegroundColor Cyan
"{0,-12} {1,>8} {2,>11} {3,>7} {4,-8} {5,-7}" -f "FILE","LENGTH","SIZE","FPS","VIDEO","AUDIO" | Write-Host
Write-Host ("-" * 62)

$info = @()
foreach ($f in $takes) {
    $json = & ffprobe -v error -print_format json -show_format -show_streams -- "$f" | ConvertFrom-Json
    $v = $json.streams | Where-Object { $_.codec_type -eq "video" } | Select-Object -First 1
    $a = $json.streams | Where-Object { $_.codec_type -eq "audio" } | Select-Object -First 1
    if (-not $v) { Fail "$f has no video stream." }

    $num, $den = ($v.r_frame_rate -split "/")
    $fps = if ([double]$den -ne 0) { [math]::Round([double]$num / [double]$den, 2) } else { 0 }

    $row = [pscustomobject]@{
        File = $f
        Dur  = [double]$json.format.duration
        Res  = "$($v.width)x$($v.height)"
        Fps  = $fps
        VCod = $v.codec_name
        ACod = if ($a) { $a.codec_name } else { "NONE" }
        Rate = if ($a) { $a.sample_rate } else { "-" }
    }
    $info += $row
    "{0,-12} {1,>8} {2,>11} {3,>7} {4,-8} {5,-7}" -f `
        $row.File, (Hms $row.Dur), $row.Res, $row.Fps, $row.VCod, $row.ACod | Write-Host
}

# ---------------------------------------------------------------- consistency checks
Write-Host ("-" * 62)
$total = ($info | Measure-Object -Property Dur -Sum).Sum
Write-Host ("{0,-12} {1,>8}" -f "TOTAL", (Hms $total))
Write-Host ""

$mismatch = $false
foreach ($prop in "Res", "Fps", "VCod", "ACod", "Rate") {
    $vals = $info.$prop | Select-Object -Unique
    if ($vals.Count -gt 1) {
        Warn "$prop differs across takes: $($vals -join ', ') — stream copy will likely fail."
        $mismatch = $true
    }
}
if ($info.ACod -contains "NONE") { Warn "At least one take has no audio track." }
if (-not $mismatch) { OK "All takes agree on resolution, frame rate and codecs." }

$drift = [math]::Abs($total - $Expected)
if ($drift -le 2.0) {
    OK ("Total {0} vs scripted {1} — within {2:N1}s." -f (Hms $total), (Hms $Expected), $drift)
} else {
    Warn ("Total {0} vs scripted {1} — off by {2:N1}s. See 'If a take runs long' in recording-plan.md." -f `
          (Hms $total), (Hms $Expected), $drift)
}

# ---------------------------------------------------------------- concat
if (Test-Path $Out) { Remove-Item $Out -Force }

$didCopy = $false
if (-not $ForceReencode -and -not $mismatch) {
    Write-Host "`nJoining (lossless stream copy)..." -ForegroundColor Cyan
    & ffmpeg -hide_banner -loglevel error -f concat -safe 0 -i $ListFile -c copy -movflags +faststart -- "$Out"
    if ($LASTEXITCODE -eq 0 -and (Test-Path $Out)) {
        $got = [double](& ffprobe -v error -show_entries format=duration -of csv=p=0 -- "$Out")
        if ([math]::Abs($got - $total) -le 1.0) {
            $didCopy = $true
            OK ("Stream copy clean — {0}" -f (Hms $got))
        } else {
            Warn ("Stream copy drifted ({0} vs expected {1}) — re-encoding instead." -f (Hms $got), (Hms $total))
            Remove-Item $Out -Force
        }
    } else {
        Warn "Stream copy failed — re-encoding instead."
        if (Test-Path $Out) { Remove-Item $Out -Force }
    }
}

if (-not $didCopy) {
    Write-Host "`nRe-encoding (normalises frame rate and audio; takes a minute)..." -ForegroundColor Cyan
    & ffmpeg -hide_banner -loglevel error -f concat -safe 0 -i $ListFile `
        -r 30 -vsync cfr -pix_fmt yuv420p `
        -c:v libx264 -preset medium -crf 19 `
        -c:a aac -b:a 192k -ar 48000 -ac 2 `
        -movflags +faststart -- "$Out"
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path $Out)) { Fail "Re-encode failed. Run ffmpeg by hand to see the error." }
}

# ---------------------------------------------------------------- report
$final = [double](& ffprobe -v error -show_entries format=duration -of csv=p=0 -- "$Out")
$mb    = [math]::Round((Get-Item $Out).Length / 1MB, 1)

Write-Host ("`n" + ("=" * 62)) -ForegroundColor Green
Write-Host ("  {0}" -f $Out) -ForegroundColor Green
Write-Host ("  {0}   {1} MB   {2}" -f (Hms $final), $mb, $(if ($didCopy) { "lossless copy" } else { "re-encoded" }))
Write-Host ("=" * 62) -ForegroundColor Green
Write-Host @"

  Before you upload, watch it once end to end and check:
    - no API key, .env, terminal or file path is visible in any frame
    - the red 13:00-20:00 band is legible at playback size
    - audio level is even across the tab switch (T6 -> T7), the one audible join
    - it opens on a number, not on a title card

"@
