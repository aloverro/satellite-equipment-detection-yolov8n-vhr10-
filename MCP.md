# MCP Server for Object Detection

Core structure:
```
main.py                # Starts the MCP server
src/
  tools.py           # MCP tools
  auth.py            # Simple API key authentication
  data_models/
    reusable.py      # These models are meant to be imported and used in output.py
    output.py        # These should correspond 1:1 to tools
```

## Get Started (Local Development)
1. Install dependencies:
```bash
  mamba create -n intel-agent-mcp python=3.12
  mamba activate intel-agent-mcp
  pip install -r requirements.txt
```
2. Run the server: `python main.py`
3. Point your MCP‑aware client (e.g., Copilot / inspector) at http://localhost:8000/mcp


## Containerized Run (Local)

You can also build and run the MCP server in a Docker container (this mirrors what will run in Azure App Service for Containers):

```bash
docker build -t intel-agent-mcp:local .
docker run -p 8000:8000 -e ENV=local intel-agent-mcp:local
```

Then point your client to: http://localhost:8000/mcp


## Authentication
- **Local dev (ENV=local or development)**: If `MCP_API_KEY` is not set, a temporary key is generated and logged with a `[DEV ONLY]` prefix.
- **Non-local (hackathon/production)**: `MCP_API_KEY` MUST be set at startup; the process will exit if missing.
- **Client headers (either works)**:
  - `Authorization: Bearer <your-api-key>` (preferred)
  - `X-API-Key: <your-api-key>` (alternative for systems that cannot set Authorization)
- **Protected paths**: Any path starting with `/mcp` (except `/health`, docs, and root) requires a valid key.
- **Environment variable**: `ENV=local|development|hackathon|production`
- **Rotation**: Update the `MCP_API_KEY` environment variable and restart the container/process.


## MCP Inspector for Debugging
```bash
npx -y @modelcontextprotocol/inspector --transport streamable-http http://localhost:8000/mcp
```
or in deployment
```bash
npx -y @modelcontextprotocol/inspector --transport streamable-http https://intel-agent-server.azurewebsites.net/mcp
# and then paste the API key in the Bearer Token Field under API Token Authentication
```
