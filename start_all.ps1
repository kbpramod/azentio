# Starts the whole VaaniDesk stack on Windows, each part in its own window.
#   .\start_all.ps1                 # server on 8000
#   .\start_all.ps1 -ServerPort 8010   # if port 8000 is busy
# Needs once: ai/.env and server/.env (copy from .env.example), venvs installed, `npm install` in client,
# and Ollama with: ollama pull qwen2.5:1.5b
param(
    [int]$ServerPort = 8000,
    [string]$AiPython = ""   # optional path to the Python that has the ai/ requirements
)
$root = $PSScriptRoot

function Find-Python($dir, $override) {
    if ($override) { return $override }
    foreach ($p in @("$dir\.venv\Scripts\python.exe", "$root\..\ai_backend\.venv\Scripts\python.exe")) {
        if (Test-Path $p) { return (Resolve-Path $p).Path }
    }
    return "python"
}

$busy = Get-NetTCPConnection -LocalPort $ServerPort -State Listen -ErrorAction SilentlyContinue
if ($busy) { Write-Warning "Port $ServerPort is already in use (process $($busy.OwningProcess)). Re-run with -ServerPort 8010."; exit 1 }

# 1. local LLM (Ollama) - optional; the agent falls back to rules if it is not running
try { Invoke-WebRequest -UseBasicParsing -TimeoutSec 2 http://127.0.0.1:11434/api/version | Out-Null; Write-Host "Ollama: running" }
catch {
    $ollama = "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe"
    if (Test-Path $ollama) { Start-Process $ollama -ArgumentList "serve" -WindowStyle Minimized; Write-Host "Ollama: started" }
    else { Write-Warning "Ollama not installed - intent detection will use rules only." }
}

$aiPy = Find-Python "$root\ai" $AiPython
$srvPy = Find-Python "$root\server" ""

# 2. AI service (port 8001)
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\ai'; `$env:PYTHONIOENCODING='utf8'; & '$aiPy' -m uvicorn app.main:app --port 8001"
# 3. team server
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\server'; `$env:PORT='$ServerPort'; & '$srvPy' run.py"
# 4. frontend (proxies /api to the server)
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\client'; `$env:VITE_API_TARGET='http://127.0.0.1:$ServerPort'; npm run dev"

Write-Host "`nStarting... open http://localhost:5173 in Chrome in ~20 seconds."
Write-Host "Check: http://127.0.0.1:8001/health (AI)   http://127.0.0.1:$ServerPort/docs (server)"
