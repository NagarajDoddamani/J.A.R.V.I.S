# JARVIS Bootstrap System

This directory contains scripts to verify and prepare the local development environment for JARVIS, ensuring full compliance with JDOS v1.2 requirements.

## Overview

The bootstrap system provides automated verification of:
- **Core Runtimes:** Python 3.12+ and Node.js 22 LTS.
- **Package Managers:** `uv` (Python) and `pnpm` (Node.js).
- **Infrastructure:** Docker Desktop, Docker Compose, and Ollama.
- **Project Configuration:** Environment variables (`.env`), folder structure, and dependencies.
- **Resource Availability:** Required ports (PostgreSQL, Redis, Qdrant, NATS, Ollama, API).

## Usage

### Windows (Primary)
Open a PowerShell terminal as an Administrator (preferred for port checking) and run:
```powershell
.\tools\bootstrap\bootstrap.ps1
```

### Linux (Secondary)
Open a terminal and run:
```bash
chmod +x ./tools/bootstrap/bootstrap.sh
./tools/bootstrap/bootstrap.sh
```

## Expected Output
The script will perform a series of checks and output results in a colored format:
- `[PASS]` (Green): Requirement met.
- `[WARN]` (Yellow): Optional or minor issue detected.
- `[FAIL]` (Red): Critical dependency missing or version mismatch.

At the end of the run, a summary will indicate if the environment is ready for development.

## Troubleshooting

### Python 3.12 Missing
Download and install from [python.org](https://www.python.org/downloads/). Ensure "Add Python to PATH" is checked.

### Node.js 22 Missing
Install using [nvm-windows](https://github.com/coreybutler/nvm-windows) or [nvm](https://github.com/nvm-sh/nvm):
```bash
nvm install 22
nvm use 22
```

### Docker Issues
Ensure Docker Desktop is running. If on Windows, ensure WSL2 is correctly configured.

### Port Conflicts
If a port check fails (e.g., 5432 for PostgreSQL), ensure no other local services are using those ports. JARVIS requires these ports for its containerized infrastructure.

### Ollama Not Reachable
Ensure Ollama is installed and the background service is running. Visit [ollama.com](https://ollama.com) for installation instructions.
