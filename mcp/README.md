# Sentinel — MongoDB MCP Server Integration

## How it works

Sentinel connects Google Cloud Agent Builder (Gemini 3.5 Flash) to the
official `mongodb-mcp-server` via the Model Context Protocol (MCP).

At runtime, Gemini performs an MCP tool discovery handshake and receives
the full list of available MongoDB operations. It then orchestrates these
alongside Sentinel's 6 custom business-logic tools to execute multi-step
outbreak coordination tasks.

## Local development

```bash
# Install Node.js 18+ if not already installed
node --version

# Run the MCP server locally (connects to your Atlas cluster)
MONGO_URI="your_connection_string" npx -y mongodb-mcp-server@latest
```

## Agent Builder configuration

In the Google Cloud Agent Builder console:
1. Navigate to your agent → Tools → Add Tool → MCP Server
2. Enter the MCP server URL (Cloud Run deployment URL from Phase 8)
3. Agent Builder performs automatic tool discovery
4. Gemini 3.5 Flash can now call `aggregate`, `find`, etc. directly

## Architecture

```
CHW submits report
       ↓
Agent Builder (Gemini 3.5 Flash)
       ↓
MCP Tool Discovery (runtime)
  ├── mongodb-mcp-server tools: aggregate, find, insertOne, updateOne...
  └── Sentinel custom tools: log_field_report, detect_cluster, detect_operational_collapse...
       ↓
Multi-step reasoning + autonomous action
       ↓
MongoDB Atlas (sentinel database)
```