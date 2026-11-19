# Avtomatik ishga tushishni bekor qilish (Administrator sifatida):
#   powershell -ExecutionPolicy Bypass -File server\remove_server.ps1
Stop-ScheduledTask -TaskName "UzumBot" -ErrorAction SilentlyContinue
Unregister-ScheduledTask -TaskName "UzumBot" -Confirm:$false -ErrorAction SilentlyContinue
Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='pythonw.exe' OR Name='cloudflared.exe'" |
    Where-Object { $_.CommandLine -like "*uzumbot*" -or $_.CommandLine -like "*127.0.0.1:8088*" } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -Confirm:$false }
Write-Host "UzumBot vazifasi o'chirildi. Uyqu sozlamalarini qaytarish: Sozlamalar > Tizim > Quvvat."
