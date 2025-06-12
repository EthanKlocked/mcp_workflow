import os
import asyncio
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel
from langgraph.prebuilt import create_react_agent
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from langchain_mcp_adapters.tools import load_mcp_tools

load_dotenv()

MODEL_CONFIG = {
    "gpt4mini": {
        "type": "openai", 
        "name": "gpt-4o-mini", 
        "API_KEY": "OPENAI_API_KEY"
    },
    "gpt4": {
        "type": "openai", 
        "name": "gpt-4", 
        "API_KEY": "OPENAI_API_KEY"
    },
    "claude3s": {
        "type": "anthropic",
        "name": "claude-3-sonnet-20240229",
        "API_KEY": "ANTHROPIC_API_KEY"
    }
}

class LangChainAgent:    
    def __init__(
        self,
        model_key: str = None,
        temperature: float = 0.7,
        llm: Optional[BaseChatModel] = None
    ):
        self.temperature = temperature        
        if llm is not None:
            self.llm = llm
            return        
        self.model_key = model_key or os.getenv("AI_MODEL", "gpt4mini")
        self._initialize_model()
        self.agents = {}
    
    def _initialize_model(self):
        if self.model_key not in MODEL_CONFIG:
            print(f"Invalid key for model '{self.model_key}'. Set model gpt4mini as default.")
            self.model_key = "gpt4mini"        
        model_config = MODEL_CONFIG[self.model_key]
        self.model_type = model_config["type"]
        self.model_name = model_config["name"]
        api_key_env = model_config["API_KEY"]
        api_key = os.getenv(api_key_env, "")        
        if not api_key:
            raise ValueError(f"Need to set {api_key_env} as API KEY")        
        if self.model_type == "openai":
            self.llm = ChatOpenAI(
                model=self.model_name,
                temperature=self.temperature,
                api_key=api_key,
            )
        elif self.model_type == "anthropic":
            self.llm = ChatAnthropic(
                model=self.model_name,
                temperature=self.temperature,
                anthropic_api_key=api_key,
            )
        else:
            raise ValueError(f"Unsupported model: {self.model_type}")
    
    def switch_model(self, model_key: str, temperature: Optional[float] = None):
        self.model_key = model_key
        if temperature is not None:
            self.temperature = temperature
        self._initialize_model()
        return self
    
    async def create_agent(self, session: ClientSession, name: str = "default", tool_filter: Optional[List[str]] = None):
        try:
            all_tools = await load_mcp_tools(session)
            filtered_tools = all_tools
            if tool_filter:
                filtered_tools = [tool for tool in all_tools if tool.name in tool_filter]            
            if not filtered_tools:
                return None
            for tool in filtered_tools:
                print(f"  - {tool.name}: {tool.description[:50]}...")
            agent = create_react_agent(self.llm, filtered_tools)
            self.agents[name] = agent
            return agent        
        except Exception as e:
            return None
    
    async def ask_agent(self, question: str, agent_name: str = "default") -> str:
        if agent_name not in self.agents:
            return f"Can not found agent '{agent_name}'"        
        try:            
            agent = self.agents[agent_name]
            response = await agent.ainvoke({
                "messages": [("user", question)]
            })            
            answer = response["messages"][-1].content
            return answer            
        except Exception as e:
            error_msg = f"Agent execution error: {str(e)}"
            return error_msg
    
    async def generate_response(self, text: str, **kwargs) -> str:
        try:
            response = await self.llm.ainvoke(text, **kwargs)
            return response.content
        except Exception as e:
            print(f"Error: {e}")
            raise
    
    async def run_prompt_template(
        self, 
        template: str, 
        input_variables: Dict[str, Any]
    ) -> str:
        try:
            prompt = PromptTemplate.from_template(template)
            chain = LLMChain(llm=self.llm, prompt=prompt)
            response = await chain.ainvoke(input_variables)
            return response["text"]
        except Exception as e:
            raise
    
    async def batch_generate(self, texts: List[str], **kwargs) -> List[str]:
        try:
            tasks = [self.generate_response(text, **kwargs) for text in texts]
            responses = await asyncio.gather(*tasks)
            return responses
        except Exception as e:
            raise
    
    def generate_response_sync(self, text: str, **kwargs) -> str:
        return asyncio.run(self.generate_response(text, **kwargs))
    
    def run_prompt_template_sync(
        self, 
        template: str, 
        input_variables: Dict[str, Any]
    ) -> str:
        return asyncio.run(self.run_prompt_template(template, input_variables))
    
    def batch_generate_sync(self, texts: List[str], **kwargs) -> List[str]:
        return asyncio.run(self.batch_generate(texts, **kwargs))