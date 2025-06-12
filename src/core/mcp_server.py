import os
import json
from dotenv import load_dotenv
from fastmcp import FastMCP
from ability.module.bitget_trader import BitgetAPI  
from core.mcp_tools.bitget_tools import register_bitget_tools
from core.mcp_tools.technical_analysis_tools import register_technical_analysis_tools
from core.mcp_tools.crypto_news_tools import register_free_crypto_news_tools
load_dotenv()

mcp = FastMCP("mcp-tools-server", stateless_http=True)

register_bitget_tools(mcp)
register_technical_analysis_tools(mcp)
register_free_crypto_news_tools(mcp)
    
if __name__ == "__main__":
    server_host = os.getenv("MCP_SERVER_HOST", "localhost")
    server_port = int(os.getenv("MCP_SERVER_PORT", "8000"))
    mcp.run(
        transport="streamable-http",
        host=server_host,
        port=server_port                     
    )