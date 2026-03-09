# Massive MCP Cheatsheet

## Overview
This is a **fork** of [massive-com/mcp_massive](https://github.com/massive-com/mcp_massive) with custom enhancements.

**Your Fork:** https://github.com/DeWiseOne/mcp_massive  
**Upstream:** https://github.com/massive-com/mcp_massive

---

## Local Development

### Run MCP Server Locally
```bash
cd /Users/pvir/vs-workspace/mcp-massive
MCP_TRANSPORT=streamable-http MASSIVE_API_KEY=your-key python entrypoint.py
```

**Access:** http://127.0.0.1:8000/mcp

### Environment Variables (Local)
```bash
MASSIVE_MCP_URL=http://127.0.0.1:8000/mcp
MASSIVE_MCP_LOG_LEVEL=INFO  # or DEBUG for verbose
MASSIVE_API_KEY=A9NpSWOG9TEM0DuuaIddkjJPPjVt8ZvV
```

---

## Azure VM Deployment

### Architecture
- **Deployment Type:** Git clone → Build on VM → Run container
- **Location:** `/home/azureuser/mcp-massive` on VM
- **Container Name:** `massive-mcp`
- **Docker Network:** `research-network`
- **Port Mapping:** Host `8000` → Container `8000`
- **Image:** `massive-mcp:latest` (built locally on VM)

### Docker Networking
```
docker network: research-network
├── research-assistant    → http://massive-mcp:8000/mcp  ✅ Can reach
├── microstructure-service → http://massive-mcp:8000/mcp ✅ Can reach
└── massive-mcp           → Listens on 0.0.0.0:8000
```

**Why it works:**
- All containers are on the same `research-network` Docker network
- Docker's built-in DNS resolves `massive-mcp` hostname to the container IP
- No need for `localhost` or VM public IP from within containers

**Container URL:** `http://massive-mcp:8000/mcp` (for research_assistant)  
**Host URL:** `http://52.149.157.34:8000/mcp` (external access)

---

## Deployment Commands

**Location:** `/Users/pvir/vs-workspace/research_assistant/infrastructure/azure_vm/`

### Install/Clone Repository on VM
```bash
cd /Users/pvir/vs-workspace/research_assistant/infrastructure/azure_vm
./vm_deploy.sh massive-install
```
This clones **your fork** (DeWiseOne/mcp_massive) to `/home/azureuser/mcp-massive`

### Update Code from Your Fork
```bash
./vm_deploy.sh massive-update
```
Runs `git pull` on VM → pulls latest from `origin` (your fork)

### Rebuild Image + Restart Container
```bash
./vm_deploy.sh massive-restart
```
**Does:**
1. Stops `massive-mcp` container
2. Builds Docker image on VM: `docker build -t massive-mcp:latest`
3. Starts container with:
   - Network: `research-network`
   - Port: `8000:8000`
   - Env file: `/home/azureuser/.env`
   - Environment: `MCP_TRANSPORT=streamable-http`, `PORT=8000`

### Check Status
```bash
./vm_deploy.sh massive-status
```
**Output:**
```
NAMES         STATUS       PORTS
massive-mcp   Up 2 minutes 0.0.0.0:8000->8000/tcp
```

### View Logs
```bash
./vm_deploy.sh massive-logs 50    # Last 50 lines
./vm_deploy.sh massive-logs 200   # Last 200 lines
```

### Stop Container
```bash
bash massive_deploy.sh vm-stop
```

### Build Image (without restart)
```bash
bash massive_deploy.sh vm-build
```

### Start Container (after stop)
```bash
bash massive_deploy.sh vm-start
```

---

## Fork Management

### Current Setup (on VM)
```bash
# Check remotes
ssh azureuser@52.149.157.34
cd /home/azureuser/mcp-massive
git remote -v
```

**Expected output:**
```
origin    https://github.com/DeWiseOne/mcp_massive.git (fetch)
origin    https://github.com/DeWiseOne/mcp_massive.git (push)
upstream  https://github.com/massive-com/mcp_massive.git (fetch)
upstream  https://github.com/massive-com/mcp_massive.git (push)
```

### Pull Updates from Upstream
```bash
ssh azureuser@52.149.157.34
cd /home/azureuser/mcp-massive
git fetch upstream
git merge upstream/master  # or: git rebase upstream/master
git push origin master
exit

# Rebuild container with merged changes
./vm_deploy.sh massive-restart
```

### Push Local Changes to Your Fork
```bash
cd /Users/pvir/vs-workspace/mcp-massive
git add .
git commit -m "feat: your change description"
git push origin master

# Then update VM
./vm_deploy.sh massive-update
./vm_deploy.sh massive-restart
```

---

## Update Image Workflow

### Full Update (Code + Container)
```bash
# 1. Update code from fork
./vm_deploy.sh massive-update

# 2. Rebuild + restart
./vm_deploy.sh massive-restart

# 3. Verify
./vm_deploy.sh massive-status
./vm_deploy.sh massive-logs 30
```

### Force Fresh Build (No Cache)
```bash
cd /Users/pvir/vs-workspace/research_assistant/infrastructure/azure_vm
bash massive_deploy.sh vm-stop
bash massive_deploy.sh --no-cache vm-build
bash massive_deploy.sh vm-start
```

### Quick Restart (No Code Update)
```bash
ssh azureuser@52.149.157.34
docker restart massive-mcp
```

---

## Troubleshooting

### Container Not Starting
```bash
# Check logs for errors
./vm_deploy.sh massive-logs 100

# Check if port is in use
ssh azureuser@52.149.157.34 "netstat -tulpn | grep 8000"

# Remove old container and recreate
ssh azureuser@52.149.157.34 "docker rm -f massive-mcp"
bash massive_deploy.sh vm-start
```

### Network Issues
```bash
# Verify research-network exists
ssh azureuser@52.149.157.34 "docker network ls | grep research"

# Verify all containers are on same network
ssh azureuser@52.149.157.34 "docker network inspect research-network"
```

### API Key Issues
```bash
# Check env file has key
ssh azureuser@52.149.157.34 "grep MASSIVE_API_KEY /home/azureuser/.env"

# Verify container has key
ssh azureuser@52.149.157.34 "docker exec massive-mcp env | grep MASSIVE"
```

### Test Connectivity from research-assistant
```bash
ssh azureuser@52.149.157.34
docker exec research-assistant curl -s http://massive-mcp:8000/mcp
```

**Expected:** JSON response from MCP server

---

## Configuration Files

### Deployment Scripts
- **Main:** `research_assistant/infrastructure/azure_vm/vm_deploy.sh`
- **MCP Specific:** `research_assistant/infrastructure/azure_vm/massive_deploy.sh`
- **Config:** `research_assistant/infrastructure/azure_vm/massive_config.sh`

### Container Settings (massive_config.sh)
```bash
MASSIVE_CONTAINER_NAME="massive-mcp"
MASSIVE_HOST_PORT="8000"
MASSIVE_CONTAINER_PORT="8000"
MASSIVE_VM_DIR="/home/azureuser/mcp-massive"
MASSIVE_IMAGE_NAME="massive-mcp"
MASSIVE_TAG="latest"
```

### Environment (research_assistant/.env)
```bash
# For local development
MASSIVE_MCP_URL=http://127.0.0.1:8000/mcp

# For container (auto-transformed by sync-env)
# MASSIVE_MCP_URL=http://massive-mcp:8000/mcp
```

---

## Custom Enhancements (Your Fork)

**Commits:**
- `dd23306` - docs: add fork management guide
- `46c760e` - feat: add stdio probe script and update .gitignore for .venv311
- `f5248d2` - refactor: clean up environment variable handling

**Features:**
1. **stdio probe script** - `scripts/mcp_massive_stdio_probe.py` for debugging
2. **Improved env handling** - Cleaner variable management
3. **Fork documentation** - Guidelines for managing fork vs upstream

---

## Quick Reference

| Task | Command |
|------|---------|
| Install on VM | `./vm_deploy.sh massive-install` |
| Update code | `./vm_deploy.sh massive-update` |
| Rebuild + restart | `./vm_deploy.sh massive-restart` |
| Check status | `./vm_deploy.sh massive-status` |
| View logs | `./vm_deploy.sh massive-logs 50` |
| SSH to VM | `./vm_deploy.sh ssh` |
| Test from container | `docker exec research-assistant curl http://massive-mcp:8000/mcp` |

**Network Test URL:** `http://massive-mcp:8000/mcp` (from any container on `research-network`)  
**External URL:** `http://52.149.157.34:8000/mcp` (from outside VM)