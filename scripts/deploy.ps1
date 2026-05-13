Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  LIBRARY MANAGEMENT SYSTEM - DEPLOY" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Step 1: Build
Write-Host ""
Write-Host "[1/3] Building Docker image..." -ForegroundColor Yellow
docker build -t final-project .
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Build failed!" -ForegroundColor Red
    exit 1
}
Write-Host "      Image built successfully!" -ForegroundColor Green

# Step 2: Clean old containers
Write-Host ""
Write-Host "[2/3] Cleaning old containers..." -ForegroundColor Yellow
docker stop myapp 2>$null
docker rm myapp 2>$null
Write-Host "      Cleanup complete!" -ForegroundColor Green

# Step 3: Run container
Write-Host ""
Write-Host "[3/3] Starting application..." -ForegroundColor Yellow
docker run -d -p 5001:5001 --name myapp final-project

if ($LASTEXITCODE -eq 0) {
    Write-Host "      Container started!" -ForegroundColor Green
} else {
    Write-Host "ERROR: Container failed to start!" -ForegroundColor Red
    exit 1
}

# Wait for app to start
Start-Sleep -Seconds 5

# Verify
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  DEPLOYMENT COMPLETE!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  App URL : http://localhost:5001" -ForegroundColor White
Write-Host "  Logs    : docker logs myapp" -ForegroundColor White
Write-Host "  Stop    : docker stop myapp" -ForegroundColor White
Write-Host ""