# Script para resetear la base de datos
# IMPORTANTE: Cierra el servidor de Django antes de ejecutar este script

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  RESET DE BASE DE DATOS" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Verificar si el archivo existe
if (Test-Path "db.sqlite3") {
    Write-Host "Eliminando base de datos antigua..." -ForegroundColor Yellow
    try {
        Remove-Item -Path "db.sqlite3" -Force
        Write-Host "✓ Base de datos eliminada correctamente" -ForegroundColor Green
    } catch {
        Write-Host "✗ Error: La base de datos está en uso. Cierra el servidor de Django primero." -ForegroundColor Red
        Write-Host "  Presiona Ctrl+C en la terminal donde corre el servidor y vuelve a intentar." -ForegroundColor Yellow
        exit 1
    }
} else {
    Write-Host "No se encontró base de datos existente." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Aplicando migraciones..." -ForegroundColor Yellow
python manage.py migrate

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Migraciones aplicadas correctamente" -ForegroundColor Green
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "  CREAR SUPERUSUARIO" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Ahora ejecuta:" -ForegroundColor Yellow
    Write-Host "  python manage.py createsuperuser" -ForegroundColor White
    Write-Host ""
} else {
    Write-Host "✗ Error al aplicar migraciones" -ForegroundColor Red
    exit 1
}







