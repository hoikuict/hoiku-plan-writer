param(
    [int]$Port = 8002,
    [int]$SessionTtlMinutes = 120,
    [int]$InputLimitBytes = 65536,
    [int]$MaxRequestBodyBytes = 16384,
    [switch]$Reload
)

$env:PYTHONPATH = 'app'
$env:PUBLIC_DEMO_MODE = '1'
$env:DEMO_RUNTIME_DIR = 'runtime'
$env:DEMO_SESSION_TTL_MINUTES = "$SessionTtlMinutes"
$env:DEMO_SESSION_INPUT_LIMIT_BYTES = "$InputLimitBytes"
$env:DEMO_MAX_REQUEST_BODY_BYTES = "$MaxRequestBodyBytes"
$env:DEMO_SECURE_COOKIES = '0'

$python = 'C:\python\open-hoikuict\venv\Scripts\python.exe'
$args = @('-m', 'uvicorn', 'hoiku_plan_writer.main:app', '--port', "$Port")
if ($Reload) {
    $args += '--reload'
}

& $python @args