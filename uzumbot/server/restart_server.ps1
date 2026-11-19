# Botni to'liq qayta ishga tushirish (osilib qolgan eski nusxalar bilan birga). ADMINISTRATOR sifatida:
#   powershell -ExecutionPolicy Bypass -File server\restart_server.ps1
$root = Split-Path -Parent $PSScriptRoot
Stop-ScheduledTask -TaskName "UzumBot" -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2
Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='pythonw.exe' OR Name='cloudflared.exe'" |
    Where-Object { $_.CommandLine -like "*uzumbot*" -or $_.CommandLine -like "*127.0.0.1:8088*" } |
    ForEach-Object { Write-Host "To'xtatildi: $($_.Name) $($_.ProcessId)"; Stop-Process -Id $_.ProcessId -Force -Confirm:$false -ErrorAction SilentlyContinue }
Start-Sleep -Seconds 3
Start-ScheduledTask -TaskName "UzumBot"
Write-Host "Bot qayta ishga tushdi. 1 daqiqadan keyin Telegramda tekshiring. Log: $root\data\bot.log" -ForegroundColor Green
Read-Host "Enter — oynani yopish" | Out-Null