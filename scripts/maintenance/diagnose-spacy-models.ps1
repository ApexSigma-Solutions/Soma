# Spacy Model Installation Diagnostic Script
# Purpose: Identify why Spacy models installed to user site-packages are not found by Poetry application

Write-Host "`n=== Spacy Model Installation Diagnostic ===`n" -ForegroundColor Cyan

# Step 1: Identify current Python interpreter
Write-Host "[1] Current Python Interpreter:" -ForegroundColor Yellow
$pythonExe = Get-Command python -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source
if ($pythonExe) {
    Write-Host "    Python: $pythonExe" -ForegroundColor Green
    & python --version
} else {
    Write-Host "    ERROR: Python not found in PATH" -ForegroundColor Red
}

# Step 2: Check if running in Poetry environment
Write-Host "`n[2] Poetry Environment Status:" -ForegroundColor Yellow
$poetryEnv = $env:VIRTUAL_ENV
if ($poetryEnv) {
    Write-Host "    Virtual Environment: $poetryEnv" -ForegroundColor Green
    Write-Host "    Poetry active: YES" -ForegroundColor Green
} else {
    Write-Host "    Virtual Environment: NOT ACTIVE" -ForegroundColor Yellow
    Write-Host "    Poetry active: NO" -ForegroundColor Yellow
}

# Step 3: Check Poetry environment details
Write-Host "`n[3] Poetry Environment Details:" -ForegroundColor Yellow
try {
    $poetryEnvPath = & poetry env info --path 2>$null
    if ($poetryEnvPath) {
        Write-Host "    Poetry env path: $poetryEnvPath" -ForegroundColor Green
        $poetryPython = Join-Path $poetryEnvPath "Scripts\python.exe"
        if (Test-Path $poetryPython) {
            Write-Host "    Poetry Python: $poetryPython" -ForegroundColor Green
            & $poetryPython --version
        }
    } else {
        Write-Host "    Poetry environment not found" -ForegroundColor Yellow
    }
} catch {
    Write-Host "    Error checking Poetry: $_" -ForegroundColor Red
}

# Step 4: Check site-packages locations
Write-Host "`n[4] Site-Packages Locations:" -ForegroundColor Yellow

# System site-packages
try {
    $systemSitePackages = & python -c "import site; print(site.getsitepackages()[0])" 2>$null
    if ($systemSitePackages) {
        Write-Host "    System site-packages: $systemSitePackages" -ForegroundColor Cyan
    }
} catch {
    Write-Host "    Could not determine system site-packages" -ForegroundColor Yellow
}

# User site-packages
try {
    $userSitePackages = & python -c "import site; print(site.getusersitepackages())" 2>$null
    if ($userSitePackages) {
        Write-Host "    User site-packages: $userSitePackages" -ForegroundColor Cyan
    }
} catch {
    Write-Host "    Could not determine user site-packages" -ForegroundColor Yellow
}

# Poetry site-packages (if active)
if ($poetryEnv) {
    try {
        $poetrySitePackages = & python -c "import site; print(site.getsitepackages()[0])" 2>$null
        if ($poetrySitePackages) {
            Write-Host "    Poetry site-packages: $poetrySitePackages" -ForegroundColor Green
        }
    } catch {
        Write-Host "    Could not determine Poetry site-packages" -ForegroundColor Yellow
    }
}

# Step 5: Check where Spacy models are installed
Write-Host "`n[5] Spacy Model Locations:" -ForegroundColor Yellow

$models = @("en_core_web_sm", "en_core_web_md", "en_core_web_trf")

foreach ($model in $models) {
    Write-Host "    Checking $model..." -ForegroundColor Cyan
    
    # Check in current Python environment
    try {
        $modelPath = & python -c "import spacy; print(spacy.util.find_package($model))" 2>$null
        if ($modelPath) {
            Write-Host "      Found in current env: $modelPath" -ForegroundColor Green
        } else {
            Write-Host "      NOT FOUND in current env" -ForegroundColor Red
        }
    } catch {
        Write-Host "      ERROR checking: $_" -ForegroundColor Red
    }
    
    # Check in user site-packages directly
    if ($userSitePackages) {
        $modelDir = Join-Path $userSitePackages $model
        if (Test-Path $modelDir) {
            Write-Host "      Found in user site-packages: $modelDir" -ForegroundColor Green
        } else {
            Write-Host "      NOT FOUND in user site-packages" -ForegroundColor Yellow
        }
    }
}

# Step 6: Check Spacy configuration
Write-Host "`n[6] Spacy Configuration:" -ForegroundColor Yellow
try {
    & python -c "import spacy; print('Spacy version:', spacy.__version__); print('Data path:', spacy.util.get_data_path())" 2>$null
} catch {
    Write-Host "    ERROR: $_" -ForegroundColor Red
}

# Step 7: Check PYTHONPATH
Write-Host "`n[7] PYTHONPATH Environment Variable:" -ForegroundColor Yellow
if ($env:PYTHONPATH) {
    Write-Host "    PYTHONPATH: $env:PYTHONPATH" -ForegroundColor Cyan
} else {
    Write-Host "    PYTHONPATH: NOT SET" -ForegroundColor Yellow
}

# Step 8: Test model loading with current Python
Write-Host "`n[8] Test Model Loading:" -ForegroundColor Yellow
foreach ($model in $models) {
    Write-Host "    Testing $model..." -ForegroundColor Cyan
    try {
        $result = & python -c "import spacy; nlp = spacy.load('$model'); print('SUCCESS')" 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "      ✓ Model loads successfully" -ForegroundColor Green
        } else {
            Write-Host "      ✗ FAILED: $result" -ForegroundColor Red
        }
    } catch {
        Write-Host "      ✗ EXCEPTION: $_" -ForegroundColor Red
    }
}

# Step 9: Test model loading with Poetry Python
if ($poetryPython -and (Test-Path $poetryPython)) {
    Write-Host "`n[9] Test Model Loading with Poetry Python:" -ForegroundColor Yellow
    foreach ($model in $models) {
        Write-Host "    Testing $model..." -ForegroundColor Cyan
        try {
            $result = & $poetryPython -c "import spacy; nlp = spacy.load('$model'); print('SUCCESS')" 2>&1
            if ($LASTEXITCODE -eq 0) {
                Write-Host "      ✓ Model loads successfully" -ForegroundColor Green
            } else {
                Write-Host "      ✗ FAILED: $result" -ForegroundColor Red
            }
        } catch {
            Write-Host "      ✗ EXCEPTION: $_" -ForegroundColor Red
        }
    }
}

Write-Host "`n=== Diagnostic Complete ===`n" -ForegroundColor Cyan
Write-Host "RECOMMENDATIONS:" -ForegroundColor Yellow
Write-Host "1. If models found in user site-packages but not in Poetry env:" -ForegroundColor White
Write-Host "   Run: poetry run python -m spacy download <model_name>" -ForegroundColor Green
Write-Host "`n2. If Poetry env not active:" -ForegroundColor White
Write-Host "   Run: poetry shell" -ForegroundColor Green
Write-Host "   Then: python -m spacy download <model_name>" -ForegroundColor Green
Write-Host "`n3. To verify Poetry environment:" -ForegroundColor White
Write-Host "   Run: poetry env info" -ForegroundColor Green
