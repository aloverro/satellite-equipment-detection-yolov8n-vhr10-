# Deployment Guide

This project now supports two deployment paths:

1. **Option A: Azure App Service (simple, built-in HTTPS)** – Good for moderate compute. (Original instructions retained.)
2. **Option B: Azure Container Instances (ACI) + Front Door (or App Gateway) for HTTPS** – Required when you need explicit large compute like **8 vCPU / 32 GB RAM** without paying for a permanently scaled App Service Plan or when you want more direct container resource sizing.

> Requirement: This container needs **8 vCPU and 32 GB RAM**. App Service can technically meet this only on higher Premium/Isolated SKUs (e.g., P3v3 ~ 8 vCPU / 32 GB) which are more costly and coupled to the plan. ACI lets us request exactly the CPU/RAM per container group. However, **ACI exposes only HTTP (no TLS) directly**; to get an HTTPS public endpoint you must front it with another Azure service (Front Door, Application Gateway, API Management, or an App Service reverse proxy). Below we document an Azure Front Door approach for HTTPS.

---

## Shared Step 1: Build and Push Container

### 1. Build and Push Container (All Options)
```bash
# Build the image
# Option 1: If you're buildling locally only, or building on an AMD64 machine
docker build -t object-detection-mcp -f ./Dockerfile .

# Option 2: If you're building on an ARM64 and need to move to the cloud:
az acr build --registry mpcprohackathon --image object-detection-mcp:latest --platform linux/amd64 -f ./Dockerfile .

# Tag for Azure Container Registry
docker tag object-detection-mcp mpcprohackathon.azurecr.io/object-detection-mcp:latest

# Login to Azure first
az login

# Login to your Azure Container Registry 
az acr login --name mpcprohackathon

# Push to registry
docker push mpcprohackathon.azurecr.io/object-detection-mcp:latest
```

---

## Option A: Azure App Service (Simpler, auto HTTPS)

Choose this if you can live with the compute limits/pricing of an App Service Plan SKU. To meet 8 vCPU / 32 GB you would need at least `P3v3` (adjust `--sku`). Example below still shows a smaller SKU; change it if you need the higher compute.

### 2A. Create Azure App Service
```bash
# Create App Service plan
az appservice plan create \
  --name geocatalog-plan \
  --resource-group hackathon-2025 \
  --sku B1 \
  --is-linux

# Create App Service
az webapp create \
  --name object-detection-mcp-server \
  --resource-group hackathon-2025 \
  --plan geocatalog-plan \
  --deployment-container-image-name mpcprohackathon.azurecr.io/object-detection-mcp:latest
```

### 3A. Configure Environment Variables
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
  --name object-detection-mcp-server \
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

### 4A. Watch the logs to see if the app got deployed correctly
```bash
az webapp log tail --name object-detection-mcp-server --resource-group hackathon-2025
```

**⚠️ IMPORTANT**: 
- The `MCP_API_KEY` is REQUIRED for non-local environments. The server will refuse to start without it in production.
- **Save the generated API key** - you'll need to share it with the team!

### 5A. Your API Endpoints Will Be:
- **Health Check**: `https://object-detection-mcp-server.azurewebsites.net/health`
- **MCP Endpoint**: `https://object-detection-mcp-server.azurewebsites.net/mcp`
- **API Docs**: `https://object-detection-mcp-server.azurewebsites.net/docs`

---

## Option B: High Compute with Azure Container Instances (8 vCPU / 32GB) + HTTPS Front Door

### Why ACI?
* Directly specify `--cpu 8 --memory 32` for the container group.
* Pay per-second for what runs instead of keeping an App Service Plan always up-sized.
* Fast iteration for container-only workloads.

### Trade-offs
* ACI gives only an HTTP endpoint (no TLS). We add Azure Front Door for HTTPS + global edge.
* Front Door adds a (small) additional resource + config.
* Cold start can be longer than App Service for first request after inactivity (if you stop/start groups).

### 2B. Generate API Key (same as before)
```bash
API_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")
echo "Generated API Key: $API_KEY"

# Enable and fetch ACR credentials if not already done
az acr update -n mpcprohackathon --admin-enabled true
ACR_JSON=$(az acr credential show --name mpcprohackathon)
ACR_USER=$(echo "$ACR_JSON" | jq -r '.username')
ACR_PASS=$(echo "$ACR_JSON" | jq -r '.passwords[0].value')
```

### 3B. Create ACI Container Group (Public DNS Label)
```bash
RESOURCE_GROUP="hackathon-2025"
ACI_NAME="object-detection-mcp-aci"
DNS_LABEL="object-detection-mcp-api"   # must be globally unique within region
IMAGE="mpcprohackathon.azurecr.io/object-detection-mcp:latest"
LOCATION="northcentralus"                      # change as needed

az container create \
  --resource-group $RESOURCE_GROUP \
  --name $ACI_NAME \
  --image $IMAGE \
  --registry-login-server mpcprohackathon.azurecr.io \
  --registry-username $ACR_USER \
  --registry-password $ACR_PASS \
  --cpu 4 --memory 16 \
  --ports 8000 \
  --os-type Linux \
  --environment-variables \
      WEBSITES_PORT=8000 \
      PORT=8000 \
      HOST=0.0.0.0 \
      ENV=hackathon \
      DEBUG=true \
      MCP_API_KEY="$API_KEY" \
  --dns-name-label $DNS_LABEL \
  --location $LOCATION
```

The public (HTTP only) endpoint will be:
```
http://$DNS_LABEL.$LOCATION.azurecontainer.io:8000
```

Test health:
```bash
curl http://$DNS_LABEL.$LOCATION.azurecontainer.io:8000/health
```

### 4B. Add Azure Front Door for HTTPS
Front Door will terminate TLS and forward to the ACI origin over HTTP.

```bash
FD_NAME="object-detection-mcp-fd"
az network front-door create \
  --resource-group $RESOURCE_GROUP \
  --name $FD_NAME \
  --accepted-protocols Http Https \
  --frontend-endpoints name=$FD_NAME-frontend host-name=$FD_NAME.azurefd.net \
  --backend-pool name=aci-backend \
      backends=object-detection-mcp-origin:$(az container show -g $RESOURCE_GROUP -n $ACI_NAME --query "ipAddress.fqdn" -o tsv) \
      load-balancing-settings=loadBalancingSettings1 \
      health-probe-settings=healthProbeSettings1 \
  --backend-pool-load-balancing name=loadBalancingSettings1 \
  --backend-pool-health-probe name=healthProbeSettings1 \
  --routing-rule name=http-route \
      frontend-endpoints=$FD_NAME-frontend \
      accepted-protocols=Http Https \
      patterns-to-match="/*" \
      forwarding-protocol=HttpOnly \
      backend-pool=aci-backend
```

The HTTPS endpoint will be:
```
https://$FD_NAME.azurefd.net
```

API paths:
```
https://$FD_NAME.azurefd.net/health
https://$FD_NAME.azurefd.net/mcp
https://$FD_NAME.azurefd.net/docs
```

> You can later map a custom domain + certificate to Front Door if desired.

### 5B. Logs & Troubleshooting
```bash
# ACI logs
az container logs -g $RESOURCE_GROUP -n $ACI_NAME --follow

# Show container status
az container show -g $RESOURCE_GROUP -n $ACI_NAME -o table
```

### 6B. Cleanup (ACI + Front Door)
```bash
az container delete -g $RESOURCE_GROUP -n $ACI_NAME --yes
az network front-door delete -g $RESOURCE_GROUP -n $FD_NAME --yes
```

---

## Team Authentication Setup (All Options)

Share this with the team:
```
API Key: [the key generated above]
MCP Endpoint: https://object-detection-mcp-server.azurewebsites.net/mcp
Authorization: Bearer [the key generated above]
```

## For API Management or Gateway Integration

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