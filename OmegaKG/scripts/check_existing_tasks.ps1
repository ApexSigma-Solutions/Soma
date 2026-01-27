# Check existing OmegaKG tasks configuration
Write-Host "=== Existing OmegaKG Tasks ===" -ForegroundColor Cyan

$taskNames = @(
    "OmegaKG_Capture_Stable",
    "Omega_KG_CaptureServer",
    "Omega_KG_Lifecycle",
    "OmegaKG Neo4j Backup"
)

foreach ($taskName in $taskNames) {
    Write-Host "`n--- Task: $taskName ---" -ForegroundColor Yellow

    try {
        $task = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
        if ($task) {
            # Get task info
            $info = Get-ScheduledTaskInfo -TaskName $taskName
            Write-Host "  Last Run: $($info.LastRunTime)" -ForegroundColor White
            Write-Host "  Next Run: $($info.NextRunTime)" -ForegroundColor White

            # Get actions
            $actions = $task.Actions
            Write-Host "  Actions:" -ForegroundColor White
            $actions | ForEach-Object {
                Write-Host "    - Execute: $($_.Execute)" -ForegroundColor Gray
                if ($_.Arguments) {
                    Write-Host "      Args: $($_.Arguments)" -ForegroundColor Gray
                }
                if ($_.WorkingDirectory) {
                    Write-Host "      Working Dir: $($_.WorkingDirectory)" -ForegroundColor Gray
                }
            }

            # Get triggers
            $triggers = $task.Triggers
            if ($triggers) {
                Write-Host "  Triggers:" -ForegroundColor White
                $triggers | ForEach-Object {
                    if ($_.Id -eq "AtLogOn") {
                        Write-Host "    - At Log On" -ForegroundColor Green
                    } elseif ($_.Daily) {
                        Write-Host "    - Daily at $($_.StartBoundary)" -ForegroundColor Green
                    } else {
                        Write-Host "    - $($_.Id)" -ForegroundColor Green
                    }
                }
            }
        } else {
            Write-Host "  Task not found!" -ForegroundColor Red
        }
    } catch {
        Write-Host "  Error: $($_.Exception.Message)" -ForegroundColor Red
    }
}

# Check if Poetry path is in system PATH
Write-Host "`n=== System PATH Check ===" -ForegroundColor Cyan
$poetryPath = "C:\Users\steyn\AppData\Roaming\Python\Python312\Scripts"
if (Test-Path $poetryPath) {
    Write-Host "Poetry directory exists: $poetryPath" -ForegroundColor Green
    $poetryInPath = $false
    $env:Path -split ';' | ForEach-Object {
        if ($_ -eq $poetryPath) {
            $poetryInPath = $true
        }
    }
    if ($poetryInPath) {
        Write-Host "  ✓ Poetry path IS in PATH" -ForegroundColor Green
    } else {
        Write-Host "  ✗ Poetry path NOT in PATH" -ForegroundColor Red
        Write-Host "  Solution: Add '$poetryPath' to system PATH" -ForegroundColor Yellow
    }
} else {
    Write-Host "Poetry directory NOT found!" -ForegroundColor Red
}
