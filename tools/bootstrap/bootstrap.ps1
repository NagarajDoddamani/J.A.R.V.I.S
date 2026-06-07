# JARVIS Bootstrap Verification Script (Windows)
# JDOS v1.2 Compliance Check

$ErrorActionPreference = "SilentlyContinue"
$SuccessCount = 0
$FailCount = 0
$WarnCount = 0

function Write-Header ($text) {
    Write-Host "`n=== $text ===" -ForegroundColor Cyan
}

function Write-Pass ($text) {
    Write-Host "[PASS] $text" -ForegroundColor Green
    $script:SuccessCount++
}

function Write-Fail ($text, $instruction) {
    Write-Host "[FAIL] $text" -ForegroundColor Red
    if ($instruction) { Write-Host "       Instruction: $instruction" -ForegroundColor Gray }
    $script:FailCount++
}

function Write-Warn ($text) {
    Write-Host "[WARN] $text" -ForegroundColor Yellow
    $script:WarnCount++
}

Write-Header "Starting JARVIS Environment Verification"

# 1. Verify Core Runtimes
Write-Header "Checking Core Runtimes"

# Python 3.12
$pythonVersion = & python --version 2>&1
if ($pythonVersion -match "Python 3\.12") {
    Write-Pass "Python 3.12 detected ($pythonVersion)"
} else {
    Write-Fail "Python 3.12 missing or incorrect version." "Install Python 3.12 from https://python.org"
}

# Node.js 22
$nodeVersion = & node --version 2>&1
if ($nodeVersion -match "v22\.") {
    Write-Pass "Node.js 22 detected ($nodeVersion)"
} else {
    Write-Fail "Node.js 22 LTS missing or incorrect version." "Install Node.js 22 from https://nodejs.org"
}

# 2. Verify Package Managers
Write-Header "Checking Package Managers"

# uv
if (Get-Command uv) {
    Write-Pass "uv detected"
} else {
    Write-Fail "uv missing." "Install via: powershell -ExecutionPolicy ByPass -c `"irm https://astral.sh/uv/install.ps1 | iex`""
}

# pnpm
if (Get-Command pnpm) {
    Write-Pass "pnpm detected"
} else {
    Write-Fail "pnpm missing." "Install via: corepack enable pnpm"
}

# 3. Verify Infrastructure
Write-Header "Checking Infrastructure"

# Git
if (Get-Command git) {
    Write-Pass "Git detected"
} else {
    Write-Fail "Git missing." "Install from https://git-scm.com"
}

# Docker
if (Get-Command docker) {
    Write-Pass "Docker detected"
    $dockerInfo = & docker info 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Pass "Docker daemon is running"
    } else {
        Write-Fail "Docker daemon is not running." "Start Docker Desktop."
    }
} else {
    Write-Fail "Docker missing." "Install Docker Desktop from https://docker.com"
}

# Docker Compose
if (Get-Command docker-compose) {
    Write-Pass "Docker Compose detected"
} else {
    Write-Warn "docker-compose (V1) missing. Checking for 'docker compose' (V2)..."
    $composeV2 = & docker compose version 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Pass "Docker Compose V2 detected"
    } else {
        Write-Fail "Docker Compose missing." "Ensure Docker Desktop includes Compose."
    }
}

# Ollama
if (Get-Command ollama) {
    Write-Pass "Ollama CLI detected"
    try {
        $ollamaResponse = Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -Method Get -TimeoutSec 2
        Write-Pass "Ollama service is reachable"
    } catch {
        Write-Fail "Ollama service unreachable." "Ensure Ollama is running on port 11434."
    }
} else {
    Write-Fail "Ollama missing." "Install from https://ollama.com"
}

# 4. Verify Project Configuration
Write-Header "Checking Project Configuration"

if (Test-Path ".env") {
    Write-Pass ".env file found"
} else {
    Write-Warn ".env file missing. Creating from .env.example..."
    if (Test-Path ".env.example") {
        Copy-Item ".env.example" ".env"
        Write-Pass ".env created"
    } else {
        Write-Fail ".env.example missing. Cannot create .env"
    }
}

$requiredDirs = @("backend", "frontend", "shared", "tools", "docs")
foreach ($dir in $requiredDirs) {
    if (Test-Path $dir) {
        Write-Pass "Directory '$dir' verified"
    } else {
        Write-Fail "Missing required directory: $dir"
    }
}

# 5. Verify Ports
Write-Header "Checking Port Availability"
$requiredPorts = @{
    5432 = "PostgreSQL"
    6379 = "Redis"
    6333 = "Qdrant"
    4222 = "NATS"
    11434 = "Ollama"
    8000 = "Backend API"
}

$activeConnections = Get-NetTCPConnection -State Listen
foreach ($port in $requiredPorts.Keys) {
    $portName = $requiredPorts[$port]
    $occupied = $activeConnections | Where-Object { $_.LocalPort -eq $port }
    if ($occupied) {
        Write-Warn "Port $port ($portName) is already in use. This may conflict with Docker services."
    } else {
        Write-Pass "Port $port ($portName) is available"
    }
}

# 6. Verify Lockfiles (FND-001)
Write-Header "Checking Lockfiles (FND-001)"
if (Get-Command python) {
    $lockfileOutput = & python -m tools.lockfile.verify 2>&1
    $lockfileExit = $LASTEXITCODE
    if ($lockfileExit -eq 0) {
        Write-Pass "Lockfiles in sync"
        foreach ($line in $lockfileOutput) {
            Write-Host "       $line" -ForegroundColor Cyan
        }
    } else {
        Write-Fail "Lockfiles are missing or stale." "Run: cd backend; uv lock; cd ..; pnpm install --lockfile-only"
        foreach ($line in $lockfileOutput) {
            Write-Host "       $line" -ForegroundColor Yellow
        }
    }
} else {
    Write-Warn "python not found; skipping lockfile verification."
}

# Summary
Write-Header "Verification Summary"
Write-Host "Success: $SuccessCount" -ForegroundColor Green
Write-Host "Warnings: $WarnCount" -ForegroundColor Yellow
Write-Host "Failures: $FailCount" -ForegroundColor Red

if ($FailCount -eq 0) {
    Write-Host "`n[SUCCESS] Environment is JDOS v1.2 compliant!" -ForegroundColor Green
    exit 0
} else {
    Write-Host "`n[FAILURE] Environment hardening required. Please address failures above." -ForegroundColor Red
    exit 1
}
