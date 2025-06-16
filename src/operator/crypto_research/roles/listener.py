# roles/listener.py
from typing import Dict, Any
import json
import re
from .base import BaseRole

# Logger
import logging
logger = logging.getLogger("crypto_research_workflow")

class Listener(BaseRole):    
    def __init__(self, agent, step_callback=None):
        super().__init__(agent, step_callback)
        self.step = "LISTEN"
    
    async def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        query = state["query"]
        
        logger.info(f"🎧 Listener process started for query: {query}")
        if self.step_callback: 
            self.step_callback(self.step, f"🎧 Analyzing crypto query: {query}")
        
        # Classification for crypto-specific queries
        classification_prompt = f"""
        Analyze the following cryptocurrency-related user input:
        "{query}"

        Determine if this request requires deep crypto research and comprehensive analysis:

        - research_question: If the query requires deep analytical thinking, market analysis, 
          integration of complex crypto data, or expert-level domain exploration
        - simple_query: If the query can be answered with simple price checks, basic facts, 
          or general knowledge without requiring in-depth analysis

        Crypto-specific classification criteria:
        1. Classify as research_question if:
        - Response requires integration of multiple data sources (onchain, social, technical, news)
        - Question needs systematic analysis of market movements, trends, or correlations
        - Query asks for patterns, whale behavior, or exchange flow analysis
        - Answer would benefit from technical indicator analysis or market sentiment evaluation
        - Question involves market prediction, trading strategy, or risk assessment
        - Request requires synthesizing information across different crypto domains
        - Query demands evaluation of complex market dynamics or implications

        2. Classify as simple_query if:
        - Request is for specific price information or basic crypto facts
        - Question can be answered with a single definitive response
        - Query is conversational or opinion-based about crypto
        - Request can be satisfied with general crypto knowledge
        - Answer doesn't require connecting multiple data points or analysis

        Examples of research_question:
        - "Analyze Bitcoin's current market situation using onchain and social sentiment data"
        - "What are the implications of recent whale movements on ETH price?"
        - "Analyze exchange flows and predict potential market direction"
        - "Comprehensive technical analysis of BTC with trading recommendations"
        - "How do current DeFi trends affect altcoin market dynamics?"

        Examples of simple_query:
        - "What is Bitcoin's current price?"
        - "How do I buy Ethereum?"
        - "What is DeFi?"
        - "Tell me about Binance exchange"

        Format: {{"classification": "research_question OR simple_query"}}
        """
        
        # Understanding crypto queries
        understanding_prompt = f"""
        # Cryptocurrency Query Analysis and Understanding
        
        Analyze the following crypto research question AS IS, without narrowing its scope:
        "{query}"
        
        Important guidelines:
        - DO NOT narrow the question's scope unless explicitly stated
        - DO NOT make assumptions about specific cryptocurrencies unless mentioned
        - MAINTAIN the original breadth and intent of the crypto question
        
        Focus on the following aspects:
        1. Core intent (what crypto analysis the user is explicitly asking for)
        2. Key crypto concepts and entities directly mentioned (BTC, ETH, DeFi, exchanges, etc.)
        3. Any explicitly stated scope, timeframes, or constraints
        4. Required data sources (onchain, technical, social, news, exchange)
        5. Analysis complexity level (basic, intermediate, advanced)
        6. A reformulation that preserves the original scope and intent
        
        Respond in the following JSON format:
        ```json
        {{
          "core_intent": "The main crypto analysis purpose as explicitly stated",
          "key_concepts": ["concept1", "concept2", "..."],
          "key_entities": ["BTC", "ETH", "exchange_name", "..."],
          "required_data_sources": ["onchain", "technical", "social", "news", "exchange"],
          "analysis_complexity": "basic/intermediate/advanced",
          "timeframe": "Explicitly stated temporal scope or 'not specified'",
          "scope": "Only explicitly stated limitations",
          "ambiguities": ["ambiguity1", "ambiguity2"],
          "clarified_question": "The question reformulated while preserving original scope",
          "domain": "Primary crypto domain (trading, defi, analysis, etc.)"
        }}
        ```
        """
        
        try:
            # Execute classification
            classification_result = await self.agent.ainvoke({"messages": classification_prompt})
            classification_content = classification_result["messages"][-1].content
            
            json_match = re.search(r'\{[\s\S]*\}', classification_content)
            if json_match:
                classification = json.loads(json_match.group(0))
                input_type = classification.get("classification", "research_question")
            else:
                input_type = "research_question"
            
            if input_type == "simple_query":
                state["should_continue"] = False
                if self.step_callback: 
                    self.step_callback(self.step, f"🎧 Classified as simple crypto query. Direct response needed.")
                return state
            
            logger.info(f"🎧 Query classification result: {input_type}")
            
            # Execute understanding
            understanding_result = await self.agent.ainvoke({"messages": understanding_prompt})
            understanding_content = understanding_result["messages"][-1].content
            
            # Extract JSON response
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', understanding_content)
            if json_match:
                understanding = json.loads(json_match.group(1))
            else:
                json_match = re.search(r'\{[\s\S]*\}', understanding_content)
                if json_match:
                    understanding = json.loads(json_match.group(0))
                else:
                    raise ValueError("JSON response not found")
            
            # Store results
            state["listener_result"] = {
                "understood_query": understanding.get("clarified_question", query),
                "core_intent": understanding.get("core_intent", ""),
                "key_concepts": understanding.get("key_concepts", []),
                "key_entities": understanding.get("key_entities", []),
                "required_data_sources": understanding.get("required_data_sources", []),
                "analysis_complexity": understanding.get("analysis_complexity", "intermediate"),
                "timeframe": understanding.get("timeframe", "not specified"),
                "scope": understanding.get("scope", ""),
                "ambiguities": understanding.get("ambiguities", []),
                "domain": understanding.get("domain", "general")
            }
            state["should_continue"] = True
            
            logger.info(f"🎧 Query understanding completed")
            logger.info(f"🎧 Required data sources: {understanding.get('required_data_sources', [])}")
            logger.info(f"🎧 Analysis complexity: {understanding.get('analysis_complexity', 'intermediate')}")
            
            if self.step_callback: 
                self.step_callback(self.step, f"🎧 Crypto query understood: {state['listener_result']['understood_query']}")
            
        except Exception as e:
            logger.error(f"🎧 Listener Error: {str(e)}")
            if self.step_callback: 
                self.step_callback("ERROR", f"🎧 Error understanding crypto query: {str(e)}")
            
            # Set default values
            state["listener_result"] = {
                "understood_query": query,
                "core_intent": "Crypto query understanding failed",
                "key_concepts": [],
                "key_entities": [],
                "required_data_sources": ["technical", "news"],
                "analysis_complexity": "intermediate",
                "error": str(e)
            }
            state["should_continue"] = True
            
        logger.info(f"🎧 Listener process completed, should_continue={state.get('should_continue', True)}")
        return state
    
    def _should_continue(self, state: Dict[str, Any]) -> str:
        if state.get("should_continue", True):
            return "continue"
        else:
            return "stop"