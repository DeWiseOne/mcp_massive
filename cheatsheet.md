Requirements
MCP Server must be running separately:
cd mcp-massive && MCP_TRANSPORT=streamable-http python entrypoint.py

Environment variable (optional):
MASSIVE_MCP_URL=http://127.0.0.1:8000  # default
MASSIVE_MCP_LOG_LEVEL=DEBUG            # or DEBUG for verbose