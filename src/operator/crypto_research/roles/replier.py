# roles/replier.py
from typing import Dict, Any
from .base import BaseRole

# Logger
import logging
logger = logging.getLogger("crypto_research_workflow")

class Replier(BaseRole):
    """Provides quick responses to simple crypto queries"""
    
    def __init__(self, agent, step_callback=None):
        super().__init__(agent, step_callback)
        self.step = "REPLY"
    
    async def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        query = state["query"]
        
        logger.info(f"💬 Replier process started for query: {query}")
        
        response_prompt = f"""
        Today's Date: {state["current_date"]}
        
        Your task is to answer this cryptocurrency query directly and accurately:
        "{query}"

        Follow these guidelines:
        1. For crypto market data, price information, or technical questions:
        - Use appropriate crypto analysis tools to get real-time data
        - Consider using tools like get_bitget_price for current prices
        - Use technical analysis tools for chart-based questions
        - Use news tools for recent developments
        - Use social sentiment tools for community insights

        2. For general crypto knowledge, basic concepts, or educational topics:
        - Answer directly using your knowledge
        - Keep responses helpful and educational
        - Provide context and explanations for crypto terminology
        - No need to use tools for basic crypto education

        3. Response should be:
        - Direct and to the point
        - Accurate and factual
        - Easy to understand for the user's level
        - Include relevant context where helpful

        First determine if the query requires real-time crypto data (use tools) or general crypto knowledge (answer directly),
        then provide a clear, helpful response.
        """
        
        try:
            logger.info(f"💬 Generating simple crypto response")
            if self.step_callback: 
                self.step_callback(self.step, f"💬 generating simple answer for crypto query")
            
            response_result = await self.agent.ainvoke({"messages": response_prompt})
            simple_response = response_result["messages"][-1].content
            
            logger.info(f"💬 Simple crypto response generated successfully ({len(simple_response)} chars)")
            
            state["final_result"] = simple_response
            
        except Exception as e:
            logger.error(f"💬 Error generating crypto response: {str(e)}")
            if self.step_callback: 
                self.step_callback("ERROR", f"💬 Error generating response: {str(e)}")
            
            state["final_result"] = f"I understand your crypto question. How can I help you further with cryptocurrency analysis?"
            
        logger.info(f"💬 Replier process completed")
        return state