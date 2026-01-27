# Create Windows Task Scheduler job for daily lifecycle enforcement

$action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-WindowStyle Hidden -Command `"cd C:\Users\steyn\OneDrive\ApexSigma\Omega_KG; poetry run python -m omega_kg.lifecycle`""

$trigger = New-ScheduledTaskTrigger `
    -Daily `
    -At 9am

$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable

Register-ScheduledTask `
    -TaskName "Omega_KG_Lifecycle" `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Description "Daily task lifecycle enforcement for Omega_KG"

Write-Host "✓ Scheduled task created: Omega_KG_Lifecycle (runs daily at 9 AM)"
