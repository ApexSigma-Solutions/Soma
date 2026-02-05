Create a batch script (`run_omega_stack.bat`) that:

1. Runs `cleanup_before_start.ps1` to kill any existing Poetry and Hookdeck processes
2. Waits for cleanup to complete
3. Runs `start_full_stack.ps1` to launch the Capture Server and Hookdeck gateway

The script will:
- Use PowerShell execution to run both scripts in sequence
- Include error checking to ensure each script completes successfully
- Provide clear status messages during execution
- Stop if either script fails

File location: `d:\projects\OmegaKG\Omega_KG_stable\run_omega_stack.bat`