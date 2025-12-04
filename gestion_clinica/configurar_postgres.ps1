# Script para configurar PostgreSQL
# Ejecuta este script ANTES de aplicar migraciones

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  CONFIGURACIÓN DE POSTGRESQL" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Solicitar información al usuario
$dbName = Read-Host "Nombre de la base de datos [clinica_db]"
if ([string]::IsNullOrWhiteSpace($dbName)) { $dbName = "clinica_db" }

$dbUser = Read-Host "Usuario de PostgreSQL [postgres]"
if ([string]::IsNullOrWhiteSpace($dbUser)) { $dbUser = "postgres" }

$dbPassword = Read-Host "Contraseña de PostgreSQL" -AsSecureString
$dbPasswordPlain = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($dbPassword))

$dbHost = Read-Host "Host [localhost]"
if ([string]::IsNullOrWhiteSpace($dbHost)) { $dbHost = "localhost" }

$dbPort = Read-Host "Puerto [5432]"
if ([string]::IsNullOrWhiteSpace($dbPort)) { $dbPort = "5432" }

# Configurar variables de entorno
$env:DB_ENGINE = "postgresql"
$env:DB_NAME = $dbName
$env:DB_USER = $dbUser
$env:DB_PASSWORD = $dbPasswordPlain
$env:DB_HOST = $dbHost
$env:DB_PORT = $dbPort

Write-Host ""
Write-Host "✓ Variables de entorno configuradas" -ForegroundColor Green
Write-Host ""
Write-Host "Ahora ejecuta:" -ForegroundColor Yellow
Write-Host "  python manage.py migrate" -ForegroundColor White
Write-Host ""







