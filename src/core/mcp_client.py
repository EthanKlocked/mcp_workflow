import asyncio
import aiohttp
import json
import os
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv
load_dotenv()

class MCPClient:
    def __init__(self, server_url: Optional[str] = None):
        self.server_url = server_url or f"http://{os.getenv('MCP_SERVER_HOST', 'localhost')}:{os.getenv('MCP_SERVER_PORT', '8080')}"
        self.session = None
        self.connected = False
    
    async def connect(self) -> bool:
        if self.connected:
            return True        
        try:
            timeout = aiohttp.ClientTimeout(total=10)
            self.session = aiohttp.ClientSession(timeout=timeout)
            self.connected = True
            return True
        except Exception as e:
            return False
    
    def _get_headers(self) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "Cache-Control": "no-cache"
        }
    
    async def _parse_response(self, response: aiohttp.ClientResponse) -> Optional[Dict[str, Any]]:
        try:
            content_type = response.headers.get('content-type', '').lower()            
            if 'text/event-stream' in content_type:
                async for line in response.content:
                    line_text = line.decode('utf-8').strip()
                    if line_text.startswith('data: '):
                        data_part = line_text[6:]
                        if data_part and data_part != '[DONE]':
                            return json.loads(data_part)
            else:
                text = await response.text()
                if text.strip():
                    return json.loads(text)            
            return None
        except Exception as e:
            return None
    
    async def list_tools(self) -> List[Dict[str, Any]]:
        if not self.connected:
            await self.connect()        
        try:
            payload = {
                "jsonrpc": "2.0",
                "id": "list_tools",
                "method": "tools/list",
                "params": {}
            }            
            async with self.session.post(
                f"{self.server_url}/mcp",
                json=payload,
                headers=self._get_headers()
            ) as response:                
                if response.status == 200:
                    result = await self._parse_response(response)
                    if result:
                        if "result" in result and "tools" in result["result"]:
                            tools = result["result"]["tools"]
                            return tools
                        else:
                            return []
                    else:
                        return []
                else:
                    error_text = await response.text()
                    print(f"HTTP {response.status}: {error_text}")
                    return []        
        except Exception as e:
            print(e)
            return []
    
    async def call_tool(self, tool_name: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        if not self.connected:
            await self.connect()        
        if params is None:
            params = {}        
        try:
            payload = {
                "jsonrpc": "2.0",
                "id": f"call_{tool_name}",
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": params
                }
            }            
            async with self.session.post(
                f"{self.server_url}/mcp",
                json=payload,
                headers=self._get_headers()
            ) as response:                
                if response.status == 200:
                    result = await self._parse_response(response)
                    if result:
                        return result.get("result", result)
                    else:
                        return None
                else:
                    return None        
        except Exception as e:
            return None
    
    async def get_server_info(self) -> Dict[str, Any]:
        tools = await self.list_tools()
        return {
            "server_url": self.server_url,
            "connected": self.connected,
            "tools_count": len(tools),
            "tools": [{"name": t.get("name"), "description": t.get("description", "")[:100]} for t in tools]
        }
    
    async def disconnect(self):
        if self.session:
            await self.session.close()
            self.session = None
        self.connected = False