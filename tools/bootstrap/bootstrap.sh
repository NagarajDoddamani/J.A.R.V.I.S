#!/bin/bash

# JARVIS Bootstrap Verification Script (Linux/macOS)
# JDOS v1.2 Compliance Check

NC='\033[0m'
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'

SUCCESS_COUNT=0
FAIL_COUNT=0
WARN_COUNT=0

write_header() {
    echo -e "\n${CYAN}=== $1 ===${NC}"
}

write_pass() {
    echo -e "${GREEN}[PASS] $1${NC}"
    ((SUCCESS_COUNT++))
}

write_fail() {
    echo -e "${RED}[FAIL] $1${NC}"
    if [ ! -z "$2" ]; then
        echo -e "       Instruction: $2"
    fi
    ((FAIL_COUNT++))
}

write_warn() {
    echo -e "${YELLOW}[WARN] $1${NC}"
    ((WARN_COUNT++))
}

write_header "Starting JARVIS Environment Verification"

# 1. Verify Core Runtimes
write_header "Checking Core Runtimes"

# Python 3.12
if command -v python3 &>/dev/null; then
    PYTHON_VERSION=$(python3 --version)
    if [[ $PYTHON_VERSION == *"Python 3.12"* ]]; then
        write_pass "Python 3.12 detected ($PYTHON_VERSION)"
    else
        write_fail "Python 3.12 missing or incorrect version ($PYTHON_VERSION)." "Install Python 3.12"
    fi
else
    write_fail "Python3 missing." "Install Python 3.12"
fi

# Node.js 22
if command -v node &>/dev/null; then
    NODE_VERSION=$(node --version)
    if [[ $NODE_VERSION == v22.* ]]; then
        write_pass "Node.js 22 detected ($NODE_VERSION)"
    else
        write_fail "Node.js 22 LTS missing or incorrect version ($NODE_VERSION)." "Install Node.js 22"
    fi
else
    write_fail "Node.js missing." "Install Node.js 22"
fi

# 2. Verify Package Managers
write_header "Checking Package Managers"

# uv
if command -v uv &>/dev/null; then
    write_pass "uv detected"
else
    write_fail "uv missing." "Install via: curl -LsSf https://astral.sh/uv/install.sh | sh"
fi

# pnpm
if command -v pnpm &>/dev/null; then
    write_pass "pnpm detected"
else
    write_fail "pnpm missing." "Install via: npm install -g pnpm"
fi

# 3. Verify Infrastructure
write_header "Checking Infrastructure"

# Git
if command -v git &>/dev/null; then
    write_pass "Git detected"
else
    write_fail "Git missing."
fi

# Docker
if command -v docker &>/dev/null; then
    write_pass "Docker detected"
    if docker info &>/dev/null; then
        write_pass "Docker daemon is running"
    else
        write_fail "Docker daemon is not running." "Start Docker service."
    fi
else
    write_fail "Docker missing." "Install Docker."
fi

# Docker Compose
if docker compose version &>/dev/null; then
    write_pass "Docker Compose detected"
elif command -v docker-compose &>/dev/null; then
    write_pass "Docker Compose (legacy) detected"
else
    write_fail "Docker Compose missing."
fi

# Ollama
if command -v ollama &>/dev/null; then
    write_pass "Ollama CLI detected"
    if curl -s http://localhost:11434/api/tags &>/dev/null; then
        write_pass "Ollama service is reachable"
    else
        write_fail "Ollama service unreachable." "Ensure Ollama is running on port 11434."
    fi
else
    write_fail "Ollama missing." "Install from https://ollama.com"
fi

# 4. Verify Project Configuration
write_header "Checking Project Configuration"

if [ -f ".env" ]; then
    write_pass ".env file found"
else
    write_warn ".env file missing. Creating from .env.example..."
    if [ -f ".env.example" ]; then
        cp .env.example .env
        write_pass ".env created"
    else
        write_fail ".env.example missing. Cannot create .env"
    fi
fi

REQUIRED_DIRS=("backend" "frontend" "shared" "tools" "docs")
for dir in "${REQUIRED_DIRS[@]}"; do
    if [ -d "$dir" ]; then
        write_pass "Directory '$dir' verified"
    else
        write_fail "Missing required directory: $dir"
    fi
done

# 5. Verify Ports
write_header "Checking Port Availability"
REQUIRED_PORTS=(5432 6379 6333 4222 11434 8000)
PORT_NAMES=("PostgreSQL" "Redis" "Qdrant" "NATS" "Ollama" "Backend API")

for i in "${!REQUIRED_PORTS[@]}"; do
    PORT=${REQUIRED_PORTS[$i]}
    NAME=${PORT_NAMES[$i]}
    if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null ; then
        write_warn "Port $PORT ($NAME) is already in use. This may conflict with Docker services."
    else
        write_pass "Port $PORT ($NAME) is available"
    fi
done

# 6. Verify Lockfiles (FND-001)
write_header "Checking Lockfiles (FND-001)"
if command -v python3 &>/dev/null; then
    LOCKFILE_RESULT=$(python3 -m tools.lockfile.verify 2>&1)
    LOCKFILE_EXIT=$?
    if [ $LOCKFILE_EXIT -eq 0 ]; then
        write_pass "Lockfiles in sync"
        echo -e "${CYAN}       $LOCKFILE_RESULT${NC}"
    else
        write_fail "Lockfiles are missing or stale." \
            "Run: cd backend && uv lock && cd .. && pnpm install --lockfile-only"
        echo -e "${YELLOW}       $LOCKFILE_RESULT${NC}"
    fi
else
    write_warn "python3 not found; skipping lockfile verification."
fi

# Summary
write_header "Verification Summary"
echo -e "${GREEN}Success: $SUCCESS_COUNT${NC}"
echo -e "${YELLOW}Warnings: $WARN_COUNT${NC}"
echo -e "${RED}Failures: $FAIL_COUNT${NC}"

if [ $FAIL_COUNT -eq 0 ]; then
    echo -e "\n${GREEN}[SUCCESS] Environment is JDOS v1.2 compliant!${NC}"
    exit 0
else
    echo -e "\n${RED}[FAILURE] Environment hardening required. Please address failures above.${NC}"
    exit 1
fi
