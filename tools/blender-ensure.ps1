# 保证有一个可用的活动 Blender 通道；不通就自己拉一个新的（隐藏窗口）。
# 用法： powershell -File tools/blender-ensure.ps1
$ErrorActionPreference = "Continue"
$root = Split-Path -Parent $PSScriptRoot
$blender = if ($env:AXISBURST_BLENDER) { $env:AXISBURST_BLENDER } else { "D:\SteamLibrary\steamapps\common\Blender\blender.exe" }
$autostart = Join-Path $root "blender\live_scripts\autostart_mcp.py"

function Test-Channel {
    return (Test-NetConnection -ComputerName 127.0.0.1 -Port 9876 -InformationLevel Quiet -WarningAction SilentlyContinue)
}

if (Test-Channel) {
    Write-Output "CHANNEL ok (already listening)"
    exit 0
}

Write-Output "CHANNEL down -> launching a fresh Blender with autostart"
Start-Process -FilePath $blender -ArgumentList '--python', $autostart -WindowStyle Hidden

for ($i = 0; $i -lt 24; $i++) {
    Start-Sleep -Seconds 2
    if (Test-Channel) {
        Write-Output "CHANNEL ok (relaunched after $($i * 2 + 2)s)"
        exit 0
    }
}

Write-Output "CHANNEL fail (still not listening after 48s)"
exit 1
