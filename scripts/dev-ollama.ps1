param(
    [int]$Port = 8010,
    [string]$Model = 'qwen2.5:0.5b',
    [int]$TimeoutSeconds = 180,
    [switch]$Reload
)

Set-Location -Path (Join-Path $PSScriptRoot '..')

$env:PYTHONPATH = 'app'
$env:HOIKU_PLAN_AI_ENABLE_ANNUAL_PREVIEW = 'true'
$env:HOIKU_PLAN_AI_ENABLE_MONTHLY_PREVIEW = 'true'
$env:HOIKU_PLAN_AI_PROVIDER = 'ollama'
$env:HOIKU_PLAN_AI_MODEL = $Model
$env:HOIKU_PLAN_AI_BASE_URL = 'http://127.0.0.1:11434'
$env:HOIKU_PLAN_AI_TIMEOUT_SECONDS = [string]$TimeoutSeconds

$args = @('-m', 'uvicorn', 'hoiku_plan_writer.main:app', '--host', '127.0.0.1', '--port', $Port)
if ($Reload) {
    $args += '--reload'
}

& '.\.venv\Scripts\python.exe' @args
