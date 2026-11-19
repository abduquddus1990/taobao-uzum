# Kompyuterni (noutbuk yoki uy kompyuteri) bot serveri qilish. ADMINISTRATOR sifatida bir marta:
#   powershell -ExecutionPolicy Bypass -File server\setup_server.ps1        (savollar bilan)
#   powershell -ExecutionPolicy Bypass -File server\setup_server.ps1 -Yes   (savolsiz, darhol ishga tushiradi)
#
# Nima qiladi:
#  1) Kompyuter uxlamaydi (rozetkada ham, batareyada ham). Ekran o'chishi mumkin.
#  2) "UzumBot" vazifasini yaratadi: Windows yoqilishi bilan (hech kim kirmasa ham) bot yashirin ishga tushadi.
#     Bot qulasa — supervisor.py qayta yoqadi; vazifa o'zi to'xtasa — Windows 1 daqiqadan keyin qayta yoqadi.
#  3) Qo'lda ishga tushirilgan eski bot nusxasini to'xtatadi (bitta token — bitta bot).
#  Natija logi: data\setup.log.  Bekor qilish: server\remove_server.ps1
param([switch]$Yes)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
New-Item -ItemType Directory -Force (Join-Path $root "data") | Out-Null
Start-Transcript -Path (Join-Path $root "data\setup.log") -Force | Out-Null

try {
    $admin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
        [Security.Principal.WindowsBuiltInRole]::Administrator)
    if (-not $admin) { throw "Administrator sifatida ishga tushiring!" }
    if (-not (Test-Path (Join-Path $root ".env"))) { throw ".env fayli yo'q — avval uni to'ldiring" }

    # --- Python: haqiqiy exe (WindowsApps yorlig'i fon rejimida ishlamasligi mumkin) ---
    $venv = Join-Path $root ".venv\Scripts\pythonw.exe"
    if (Test-Path $venv) { $pyw = $venv }
    else {
        $exe = (& python -c "import sys; print(sys.executable)").Trim()
        $pyw = Join-Path (Split-Path $exe) "pythonw.exe"
    }
    if (-not (Test-Path $pyw)) { throw "pythonw.exe topilmadi: $pyw" }
    Write-Host "Python: $pyw"

    # --- 1) Uyqu rejimi ---
    powercfg /change standby-timeout-ac 0
    powercfg /change standby-timeout-dc 0
    powercfg /change hibernate-timeout-ac 0
    Write-Host "Uyqu rejimi o'chirildi." -ForegroundColor Green

    # --- 2) Vazifa ---
    $action = New-ScheduledTaskAction -Execute $pyw -Argument "`"$root\supervisor.py`"" -WorkingDirectory $root
    $trigger = New-ScheduledTaskTrigger -AtStartup
    $trigger.Delay = "PT60S"   # internet ulanishini kutish
    $principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType S4U -RunLevel Limited
    $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
        -StartWhenAvailable -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) `
        -ExecutionTimeLimit ([TimeSpan]::Zero) -MultipleInstances IgnoreNew
    Register-ScheduledTask -TaskName "UzumBot" -Action $action -Trigger $trigger -Principal $principal `
        -Settings $settings -Description "Taobao-Uzum Telegram bot (supervisor.py)" -Force | Out-Null
    Write-Host "'UzumBot' vazifasi yaratildi." -ForegroundColor Green

    $start = $Yes
    if (-not $Yes) { $start = (Read-Host "Hozir ishga tushiraymi? (ha/yo'q)") -match "^h" }
    if ($start) {
        # qo'lda ishlab turgan nusxani to'xtatish: 8088 portdagi server va uning tunneli
        $port = (Get-Content (Join-Path $root ".env") | Where-Object { $_ -match "^WEBAPP_PORT=(\d+)" } |
                 ForEach-Object { $Matches[1] }) | Select-Object -First 1
        if (-not $port) { $port = "8088" }
        Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue |
            ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
        Get-CimInstance Win32_Process -Filter "Name='cloudflared.exe'" |
            Where-Object { $_.CommandLine -like "*127.0.0.1:$port*" } |
            ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
        Start-Sleep -Seconds 3
        Start-ScheduledTask -TaskName "UzumBot"
        Write-Host "Ishga tushdi. Log: $root\data\bot.log" -ForegroundColor Green
    }

    Write-Host ""
    Write-Host "QOLGAN QADAMLAR (qo'lda):" -ForegroundColor Yellow
    Write-Host " - Noutbuk: qopqoqni YOPMANG, zaryadlovchiga ulab qo'ying"
    Write-Host " - Windows Update: 'Faol soatlar' — qayta yuklash tunda bo'lsin (bot o'zi qayta yonadi)"
    Write-Host " - Boshqa kompyuterda bir vaqtda shu botni YOQMANG (bitta token — bitta bot)"
    Write-Host "SETUP_OK"
}
catch {
    Write-Host "XATO: $_" -ForegroundColor Red
    Write-Host "SETUP_FAIL"
}
finally {
    Stop-Transcript | Out-Null
    if (-not $Yes) { Read-Host "Enter — oynani yopish" | Out-Null }
}
