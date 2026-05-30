# Agent Builder Console Setup

## Prerequisites
- Sentinel backend deployed to Cloud Run (Phase 8)
- Note your Cloud Run URL: https://sentinel-XXXX-uc.a.run.app

## Steps

### 1. Create the agent
- Go to: https://console.cloud.google.com/vertex-ai/agents
- Click "Create Agent"
- Display name: `Sentinel`
- Region: `us-central1`
- Model: `gemini-3.5-flash`

### 2. Set the system prompt
- Click "Agent" → "Instructions"
- Paste the contents of `agent_config/system_prompt.txt`
- Click Save

### 3. Add tools
For each tool in `agent_config/tool_definitions.json`:
- Click "Tools" → "Create Tool"
- Type: "OpenAPI"
- Paste the tool's `name`, `description`, and `parameters`
- Endpoint: your Cloud Run URL + the endpoint path
  Example: `https://sentinel-XXXX-uc.a.run.app/api/tools/log-field-report`
- Click Save

### 4. Add MongoDB MCP Server
- Click "Tools" → "Add MCP Server"
- Server URL: your deployed mongodb-mcp-server URL
- (See mcp/README.md for deployment instructions)

### 5. Test
- Click "Test Agent"
- Type: "What is the current operational status?"
- Agent should call detect_operational_collapse and get_morning_brief