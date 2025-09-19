# Azure App Service Deployment - Simple Instructions

## Quick Deploy to Azure

### 1. Build and Push Container
```bash
# Build the image
# Option 1: If you're buildling locally only, or building on an AMD64 machine
docker build -t intel-agent-mcp -f agent_team/Dockerfile agent_team

# Option 2: If you're building on an ARM64 and need to move to the cloud:
az acr build --registry mpcprohackathon --image intel-agent-mcp:latest --platform linux/amd64 -f agent_team/Dockerfile agent_team

# Tag for Azure Container Registry
docker tag intel-agent-mcp mpcprohackathon.azurecr.io/intel-agent-mcp:latest

# Login to Azure first
az login

# Login to your Azure Container Registry 
az acr login --name mpcprohackathon

# Push to registry
docker push mpcprohackathon.azurecr.io/intel-agent-mcp:latest
```

### 2. Create Azure App Service
```bash
# Create App Service plan
az appservice plan create \
  --name geocatalog-plan \
  --resource-group hackathon-2025 \
  --sku B1 \
  --is-linux

# Create App Service
az webapp create \
  --name intel-agent-mcp-server \
  --resource-group hackathon-2025 \
  --plan geocatalog-plan \
  --deployment-container-image-name mpcprohackathon.azurecr.io/intel-agent-mcp:latest
```

### 3. Configure Environment Variables
```bash
# First, generate a secure API key
API_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")
echo "Generated API Key: $API_KEY"

# Then, get credentials for ACR 
az acr update -n mpcprohackathon --admin-enabled true
az acr credential show --name mpcprohackathon
```

Copy one of the passwords displayed above and replace [YOUR_PASSWORD] below.

```bash
# Set required environment variables
az webapp config appsettings set \
  --name intel-agent-mcp-server \
  --resource-group hackathon-2025 \
  --settings \
    WEBSITES_PORT=8000 \
    PORT=8000 \
    HOST=0.0.0.0 \
    ENV=hackathon \
    DEBUG=true \
    MCP_API_KEY="$API_KEY" \
    DOCKER_REGISTRY_SERVER_USERNAME="mpcprohackathon" \
    DOCKER_REGISTRY_SERVER_PASSWORD="[YOUR_PASSWORD]"
```

### 4. Watch the logs to see if the app got deployed correctly
```bash
az webapp log tail --name intel-agent-mcp-server --resource-group hackathon-2025
```

**⚠️ IMPORTANT**: 
- The `MCP_API_KEY` is REQUIRED for non-local environments. The server will refuse to start without it in production.
- **Save the generated API key** - you'll need to share it with the team!

### 5. Your API Endpoints Will Be:
- **Health Check**: `https://intel-agent-mcp-server.azurewebsites.net/health`
- **MCP Endpoint**: `https://intel-agent-mcp-server.azurewebsites.net/mcp`
- **API Docs**: `https://intel-agent-mcp-server.azurewebsites.net/docs`

## Team Authentication Setup

Share this with the team:
```
API Key: [the key generated above]
MCP Endpoint: https://intel-agent-mcp-server.azurewebsites.net/mcp
Authorization: Bearer [the key generated above]
```

## For API Management Integration

Add one of these headers to your API Management policy (replace with your actual API key):
```xml
<set-header name="Authorization" exists-action="override">
  <value>Bearer [your-generated-api-key]</value>
</set-header>
<!-- OR -->
<set-header name="X-API-Key" exists-action="override">
  <value>[your-generated-api-key]</value>
</set-header>
```