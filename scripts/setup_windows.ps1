# Setup script for Windows server

Write-Host "==================================" -ForegroundColor Green
Write-Host "VPN Tunnel Server Setup (Windows)" -ForegroundColor Green
Write-Host "==================================" -ForegroundColor Green
Write-Host ""

# Check if running as Administrator
$currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host "Error: Please run PowerShell as Administrator" -ForegroundColor Red
    exit 1
}

# Check Python
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "Error: Python is required" -ForegroundColor Red
    Write-Host "Download from: https://www.python.org/downloads/" -ForegroundColor Yellow
    exit 1
}

Write-Host "Python version:"
python --version
Write-Host ""

# Install dependencies
Write-Host "Installing Python dependencies..." -ForegroundColor Yellow
Write-Host "Note: Using simplified requirements for Windows server" -ForegroundColor Cyan
pip install -r requirements-server.txt

# Enable IP forwarding
Write-Host ""
Write-Host "Enabling IP forwarding..." -ForegroundColor Yellow
Set-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Services\Tcpip\Parameters" -Name "IPEnableRouter" -Value 1

Write-Host ""
Write-Host "==================================" -ForegroundColor Green
Write-Host "Setup completed!" -ForegroundColor Green
Write-Host "==================================" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. Open Windows Firewall and allow port 8888 (or your chosen port)"
Write-Host ""
Write-Host "2. Generate encryption key (if not already done):"
Write-Host "   python scripts\generate_key.py" -ForegroundColor Yellow
Write-Host ""
Write-Host "3. Start the server (use simple version - no TUN drivers required):"
Write-Host "   python server\server_simple.py --key <HEX_KEY>" -ForegroundColor Yellow
Write-Host ""
Write-Host "Example:" -ForegroundColor Cyan
Write-Host "   python server\server_simple.py --key abc123..." -ForegroundColor Yellow
Write-Host ""
Write-Host "Note: server_simple.py doesn't require pytun or TUN drivers!" -ForegroundColor Green
Write-Host ""
