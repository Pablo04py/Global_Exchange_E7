# Global Exchange - Inicio de produccion LOCAL en Windows
# Ejecutar desde la raiz del proyecto (donde esta docker-compose.prod.yml).
# Modo normal: inicia los contenedores, valida Stripe y abre otra terminal webhook.
# Uso: powershell -NoProfile -ExecutionPolicy Bypass -File .\iniciar-globalexchange-prodlocal.ps1
# Para reconstruir la imagen web: agregar -Build

param(
    [switch]$SoloWebhook,
    [switch]$Build
)

$ErrorActionPreference = 'Stop'
$webhookUrl = 'http://localhost/operaciones/pagos/stripe/webhook/'

if ($SoloWebhook) {
    Set-Location -LiteralPath $PSScriptRoot
    Write-Host '==============================================' -ForegroundColor Cyan
    Write-Host '  STRIPE WEBHOOK - GLOBAL EXCHANGE (TEST)' -ForegroundColor Cyan
    Write-Host '==============================================' -ForegroundColor Cyan
    Write-Host "Destino: $webhookUrl"
    Write-Host 'No cierres esta ventana mientras pruebes pagos con tarjeta.' -ForegroundColor Yellow
    Write-Host ''
    & stripe listen --events payment_intent.succeeded --forward-to $webhookUrl
    if ($LASTEXITCODE -ne 0) {
        throw 'Stripe CLI se detuvo con un error. Revisa stripe login y la conexion.'
    }
    return
}

Set-Location -LiteralPath $PSScriptRoot
$composeFile = Join-Path $PSScriptRoot 'docker-compose.prod.yml'
if (-not (Test-Path -LiteralPath $composeFile)) {
    throw 'No se encontro docker-compose.prod.yml junto a este script. Guardalo en la raiz del proyecto.'
}

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw 'No se encontro docker. Inicia Docker Desktop o revisa el PATH.'
}
if (-not (Get-Command stripe -ErrorAction SilentlyContinue)) {
    throw 'No se encontro Stripe CLI. Instalalo y ejecuta stripe login.'
}

Write-Host '[1/5] Verificando Docker Compose...' -ForegroundColor Cyan
& docker compose -f 'docker-compose.prod.yml' config --quiet
if ($LASTEXITCODE -ne 0) {
    throw 'La configuracion docker-compose.prod.yml tiene errores.'
}

Write-Host '[2/5] Obteniendo el secreto local de firma de Stripe (no se mostrara)...' -ForegroundColor Cyan
$stripeOutput = (& stripe listen --print-secret 2>&1 | Out-String)
if ($LASTEXITCODE -ne 0) {
    throw 'Stripe CLI no pudo recuperar el secreto. Ejecuta stripe login antes de continuar.'
}
$matchSecret = [regex]::Match($stripeOutput, 'whsec_[A-Za-z0-9]+')
if (-not $matchSecret.Success) {
    throw 'Stripe CLI no devolvio un secreto whsec_. Verifica que stripe listen --print-secret funcione.'
}
$cliSecret = $matchSecret.Value

Write-Host '[3/5] Iniciando PostgreSQL, Keycloak, Django/Gunicorn y Nginx...' -ForegroundColor Cyan
$upArgs = @('compose', '-f', 'docker-compose.prod.yml', 'up', '-d', '--wait')
if ($Build) { $upArgs += '--build' }
& docker @upArgs
if ($LASTEXITCODE -ne 0) {
    throw 'Docker Compose no pudo iniciar todos los servicios. Revisa docker compose -f docker-compose.prod.yml logs.'
}

Write-Host '[4/5] Verificando las claves de Stripe configuradas en Django...' -ForegroundColor Cyan
$pyCode = "import hashlib; from django.conf import settings; print('WEBHOOK_SHA256=' + hashlib.sha256(settings.STRIPE_WEBHOOK_SECRET.encode('utf-8')).hexdigest()); print('STRIPE_TEST_MODE=' + str(settings.STRIPE_SECRET_KEY.startswith('sk_test_') and settings.STRIPE_PUBLISHABLE_KEY.startswith('pk_test_')))"
$djangoOutput = (& docker compose -f 'docker-compose.prod.yml' exec -T web python manage.py shell -c $pyCode 2>&1 | Out-String)
if ($LASTEXITCODE -ne 0) {
    Write-Host $djangoOutput
    throw 'No se pudo comprobar la configuracion de Django dentro del contenedor web.'
}

$matchHash = [regex]::Match($djangoOutput, 'WEBHOOK_SHA256=([a-f0-9]{64})')
if (-not $matchHash.Success) {
    throw 'No se pudo leer la huella de STRIPE_WEBHOOK_SECRET desde Django.'
}
if ($djangoOutput -notmatch 'STRIPE_TEST_MODE=True') {
    throw 'Este script es para pruebas locales: Django debe usar claves sk_test_ y pk_test_, no claves LIVE.'
}

$sha = [System.Security.Cryptography.SHA256]::Create()
try {
    $digest = $sha.ComputeHash([System.Text.Encoding]::UTF8.GetBytes($cliSecret))
    $localHash = ([BitConverter]::ToString($digest)).Replace('-', '').ToLowerInvariant()
} finally {
    $sha.Dispose()
}
$cliSecret = $null

if ($localHash -ne $matchHash.Groups[1].Value) {
    Write-Warning 'El secreto STRIPE_WEBHOOK_SECRET usado por Django NO coincide con el de Stripe CLI.'
    Write-Host 'Los contenedores estan iniciados, pero NO se abrira el listener para evitar pagos sin confirmar.' -ForegroundColor Yellow
    Write-Host 'Actualiza el secreto whsec_ del Stripe CLI en el archivo de entorno realmente usado por web y recrea web.' -ForegroundColor Yellow
    Write-Host 'Luego vuelve a ejecutar este script. No confundas el secreto CLI con el webhook del Dashboard.' -ForegroundColor Yellow
    exit 1
}

Write-Host '[5/5] Abriendo otra terminal con Stripe CLI...' -ForegroundColor Cyan
$quotedPath = '"' + $PSCommandPath + '"'
$commandArgs = '-NoExit -NoProfile -ExecutionPolicy Bypass -File ' + $quotedPath + ' -SoloWebhook'
Start-Process -FilePath 'powershell.exe' -ArgumentList $commandArgs -WorkingDirectory $PSScriptRoot

Write-Host ''
Write-Host '==============================================' -ForegroundColor Green
Write-Host '  GLOBAL EXCHANGE PRODUCCION LOCAL INICIADA' -ForegroundColor Green
Write-Host '==============================================' -ForegroundColor Green
Write-Host 'Aplicacion: http://localhost/'
Write-Host 'Keycloak:   http://localhost:8080/'
Write-Host 'Webhook:    http://localhost/operaciones/pagos/stripe/webhook/'
Write-Host 'Stripe CLI: se abrio otra terminal (dejala abierta).' -ForegroundColor Green
Write-Host 'Firma del webhook: coincide con la configuracion de Django.' -ForegroundColor Green
Write-Host ''
& docker compose -f 'docker-compose.prod.yml' ps
Write-Host ''
Write-Host 'IMPORTANTE: este es el entorno de produccion LOCAL con HTTP, no un despliegue publico seguro.' -ForegroundColor Yellow
