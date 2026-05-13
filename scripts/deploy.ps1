Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  LIBRARY MANAGEMENT SYSTEM - DEPLOY" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Step 1: Build
Write-Host "`n[1/3] Building Docker image..." -ForegroundColor Yellow
docker build -t final-project .
if ($LASTEXITCODE -ne 0) {
    Write-Host "Build failed!" -ForegroundColor Red
    exit 1
}

# Step 2: Clean
Write-Host "`n[2/3] Cleaning old containers..." -ForegroundColor Yellow
docker stop myapp 2>$null
docker rm myapp 2>$null

# Step 3: Run
Write-Host "`n[3/3] Starting application..." -ForegroundColor Yellow
docker run -d -p 5001:5001 --name myapp final-project

Write-Host "`n✅ App is running at http://localhost:5001" -ForegroundColor Green
Write-Host "📋 View logs: docker logs myapp" -ForegroundColor White
Write-Host "🛑 Stop app: docker stop myapp" -ForegroundColor White