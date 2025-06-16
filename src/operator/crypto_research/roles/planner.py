# roles/planner.py
from typing import Dict, Any, List
import json
import re
from .base import BaseRole
from datetime import datetime

# Logger
import logging
logger = logging.getLogger("crypto_research_workflow")

class Planner(BaseRole):
    """Creates comprehensive crypto research plans"""
    
    def __init__(self, agent, step_callback=None):
        super().__init__(agent, step_callback)
        self.step = "PLAN"
    
    async def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        query = state["query"]
        logger.info(f"📝 Planner process started for query: {query}")
        
        # Check if this is re-planning
        is_replanning = "re_plan" in state.get("last_node", "") or state.get("iteration", 0) > 0
        
        if is_replanning:
            logger.info(f"📝 Re-planning detected (iteration: {state.get('iteration', 0)})")
            return await self._replan(state)
        else:
            logger.info(f"📝 Initial planning phase started")
            return await self._initial_plan(state)
    
    async def _initial_plan(self, state: Dict[str, Any]) -> Dict[str, Any]:
        query = state["query"]
        listener_result = state.get("listener_result", {})
        
        if self.step_callback: 
            self.step_callback(self.step, f"generating crypto research plans")
        
        # Extract information from listener results
        understood_query = listener_result.get("understood_query", query)
        core_intent = listener_result.get("core_intent", "")
        key_concepts = listener_result.get("key_concepts", [])
        key_entities = listener_result.get("key_entities", [])
        required_data_sources = listener_result.get("required_data_sources", [])
        analysis_complexity = listener_result.get("analysis_complexity", "intermediate")
        domain = listener_result.get("domain", "general")
        timeframe = listener_result.get("timeframe", "not specified")
        
        # Planning prompt for crypto research
        planning_prompt = f"""
        # Cryptocurrency Research Planning

        ## Today's Date
        Today is {state["current_date"]}

        ## Question Information
        Original Question: "{query}"
        Understood Question: "{understood_query}"
        Core Intent: "{core_intent}"
        Key Concepts: {", ".join(key_concepts)}
        Key Entities: {", ".join(key_entities)}
        Required Data Sources: {", ".join(required_data_sources)}
        Analysis Complexity: {analysis_complexity}
        Domain: {domain}
        Timeframe: {timeframe}

        ## Available Crypto Analysis Tools
        - analyze_rsi: Technical analysis using RSI indicator
        - analyze_moving_averages: Moving average analysis and cross signals
        - analyze_bollinger_bands: Volatility analysis using Bollinger Bands
        - comprehensive_technical_analysis: Complete technical analysis with multiple indicators
        - monitor_whale_transactions: Track large cryptocurrency transactions
        - detect_large_transfers: Identify significant fund movements
        - analyze_exchange_flows: Monitor exchange inflow/outflow patterns
        - get_network_health_metrics: Blockchain network health analysis
        - analyze_reddit_crypto_sentiment: Social sentiment from Reddit communities
        - monitor_crypto_social_trends: Track social media trends and discussions
        - detect_social_anomalies: Identify unusual social activity patterns
        - get_latest_crypto_news: Latest cryptocurrency news and analysis
        - monitor_breaking_news: Real-time news monitoring
        - get_trending_crypto_info: Trending cryptocurrencies and topics
        - get_bitget_account_info: Trading account information
        - get_bitget_positions: Current trading positions
        - get_bitget_price: Real-time price data
        - place_bitget_order: Execute trading orders (use with extreme caution)
        - get_bitget_candles: Historical price and volume data

        ## Task
        Create a comprehensive crypto research plan to answer this question effectively.

        Your plan should include:
        1. A main research question (reformulated for clarity if needed)
        2. 3-6 sub-questions that break down the main question systematically
        3. For each sub-question:
        - Strategic tool selection from available crypto tools
        - Specific parameters for each tool (symbols, timeframes, thresholds)
        - Priority level (High/Medium/Low) based on importance
        - Research direction indicating key aspects to explore
        - Expected data type and analysis approach

        4. Overall research strategy with rationale

        ## Tool Selection Guidelines for Crypto Analysis
        - Technical Analysis: Use RSI, moving averages, Bollinger Bands for price action analysis
        - Onchain Analysis: Use whale monitoring, large transfers, exchange flows for market movement insights
        - Social Analysis: Use Reddit sentiment, social trends, anomaly detection for market psychology
        - News Analysis: Use latest news, breaking news, trending info for fundamental analysis
        - Trading Analysis: Use Bitget tools for real-time market data and position analysis

        ## Research Strategy Guidelines
        - Prioritize data sources based on query requirements
        - Consider temporal aspects (recent vs historical analysis)
        - Balance technical, fundamental, and sentiment analysis
        - Account for market volatility and crypto-specific factors
        - Plan for iterative analysis refinement

        ## Output Format
        Respond with a JSON object structured as follows:
        ```json
        {{
        "main_question": "Clear version of the main crypto research question",
        "sub_questions": [
            {{
            "question": "Sub-question 1",
            "tools": ["tool1", "tool2"],
            "parameters": {{"symbol": "BTCUSDT", "timeframe": "1h", "threshold": 1000000}},
            "priority": "High/Medium/Low",
            "research_direction": "Specific crypto aspects to focus on",
            "expected_data": "Type of data and analysis approach",
            "rationale": "Reasoning for this sub-question"
            }}
        ],
        "research_strategy": "Description of overall crypto analysis approach and prioritization"
        }}
        ```
        """
        
        try:
            # Execute planning
            planning_result = await self.agent.ainvoke({"messages": planning_prompt})
            planning_content = planning_result["messages"][-1].content
            
            # Extract JSON response
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', planning_content)
            if json_match:
                plan = json.loads(json_match.group(1))
            else:
                json_match = re.search(r'\{[\s\S]*\}', planning_content)
                if json_match:
                    plan = json.loads(json_match.group(0))
                else:
                    raise ValueError("JSON response not found")
            
            # Store results
            state["planner_result"] = {
                "main_question": plan.get("main_question", understood_query),
                "sub_questions": plan.get("sub_questions", []),
                "research_strategy": plan.get("research_strategy", ""),
                "is_initial_plan": True
            }
            
            logger.info(f"📝 Initial plan created: main_question='{state['planner_result']['main_question']}'")
            logger.info(f"📝 Plan sub-questions: {len(state['planner_result']['sub_questions'])}")
            
            if self.step_callback:
                research_strategy = plan.get("research_strategy", "")
                short_strategy = research_strategy[:60] + "..." if len(research_strategy) > 60 else research_strategy
                message = f"📝 Initial crypto research plan created | Strategy: {short_strategy}"
                self.step_callback(self.step, message)
            
        except Exception as e:
            logger.error(f"📝 Error creating initial plan: {str(e)}")
            if self.step_callback: 
                self.step_callback("ERROR", f"📝 Error creating crypto research plan: {str(e)}")
            
            # Set default values for crypto analysis
            state["planner_result"] = {
                "main_question": understood_query,
                "sub_questions": [
                    {
                        "question": understood_query,
                        "tools": ["comprehensive_technical_analysis", "get_latest_crypto_news"],
                        "parameters": {"symbol": "BTCUSDT", "interval": "1h"},
                        "priority": "High",
                        "research_direction": "Basic crypto market analysis",
                        "rationale": "Default approach due to planning error"
                    }
                ],
                "research_strategy": "Basic technical and news analysis strategy",
                "error": str(e),
                "is_initial_plan": True
            }
        
        state["last_node"] = "plan"
        logger.info(f"📝 Initial planning completed with {len(state['planner_result'].get('sub_questions', []))} sub-questions")
        
        return state
    
    async def _replan(self, state: Dict[str, Any]) -> Dict[str, Any]:
        query = state["query"]
        listener_result = state.get("listener_result", {})
        original_plan = state.get("planner_result", {})
        reviewer_result = state.get("reviewer_result", {})
        
        logger.info(f"📝 Re-planning started for iteration {state.get('iteration', 0)}")
        
        # Extract feedback and evaluation
        feedback = reviewer_result.get("feedback", "No specific feedback provided")
        evaluation = reviewer_result.get("evaluation", {})
        weaknesses = evaluation.get("weaknesses", [])
        suggestions = evaluation.get("suggestions", [])
        
        logger.info(f"📝 Re-planning with feedback - Weaknesses: {weaknesses}")
        
        if self.step_callback:
            iteration = state.get("iteration", 0)
            message = f"📝 Re-planning crypto analysis based on feedback for cycle {iteration}"
            if weaknesses:
                short_weakness = weaknesses[0][:50] + "..." if len(weaknesses[0]) > 50 else weaknesses[0]
                message += f" | Issue: {short_weakness}"
            self.step_callback(self.step, message)
        
        understood_query = listener_result.get("understood_query", query)
        
        # Replanning prompt for crypto analysis
        replanning_prompt = f"""
        # Crypto Research Plan Adjustment

        ## Original Research Question
        "{understood_query}"

        ## Current Research Plan
        {json.dumps(original_plan, ensure_ascii=False, indent=2)}

        ## Feedback from Review
        Feedback: {feedback}

        Weaknesses identified:
        {chr(10).join([f"- {w}" for w in weaknesses])}

        Suggestions:
        {chr(10).join([f"- {s}" for s in suggestions])}

        ## Available Crypto Analysis Tools
        - Technical: analyze_rsi, analyze_moving_averages, analyze_bollinger_bands, comprehensive_technical_analysis
        - Onchain: monitor_whale_transactions, detect_large_transfers, analyze_exchange_flows, get_network_health_metrics
        - Social: analyze_reddit_crypto_sentiment, monitor_crypto_social_trends, detect_social_anomalies
        - News: get_latest_crypto_news, monitor_breaking_news, get_trending_crypto_info
        - Trading: get_bitget_account_info, get_bitget_positions, get_bitget_price, get_bitget_candles

        ## Task
        Adjust the crypto research plan based on the feedback provided. You can:
        1. Add new sub-questions to address gaps in crypto analysis
        2. Modify existing sub-questions to be more precise or effective
        3. Remove or replace sub-questions that are less relevant
        4. Change tools, parameters, or analysis approaches
        5. Refine the overall research strategy for better crypto insights
        6. Adjust priority levels and research directions

        Focus on creating the most effective crypto analysis plan possible.

        ## Output Format
        Respond with a JSON object structured as follows:
        ```json
        {{
        "main_question": "Clear version of the main crypto research question",
        "sub_questions": [
            {{
            "question": "Sub-question 1",
            "tools": ["tool1", "tool2"],
            "parameters": {{"symbol": "BTCUSDT", "timeframe": "1h"}},
            "priority": "High/Medium/Low",
            "research_direction": "Specific crypto aspects to focus on",
            "expected_data": "Type of crypto data and analysis approach",
            "rationale": "Reasoning for this sub-question",
            "status": "new/modified/unchanged"
            }}
        ],
        "research_strategy": "Description of overall crypto analysis approach",
        "adjustment_reasoning": "Explanation of key adjustments made based on feedback"
        }}
        ```
        """
        
        try:
            # Execute replanning
            replanning_result = await self.agent.ainvoke({"messages": replanning_prompt})
            replanning_content = replanning_result["messages"][-1].content
            
            # Extract JSON response
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', replanning_content)
            if json_match:
                adjusted_plan = json.loads(json_match.group(1))
            else:
                json_match = re.search(r'\{[\s\S]*\}', replanning_content)
                if json_match:
                    adjusted_plan = json.loads(json_match.group(0))
                else:
                    raise ValueError("JSON response not found")
            
            # Store results
            state["planner_result"] = {
                "main_question": adjusted_plan.get("main_question", original_plan.get("main_question", understood_query)),
                "sub_questions": adjusted_plan.get("sub_questions", original_plan.get("sub_questions", [])),
                "research_strategy": adjusted_plan.get("research_strategy", original_plan.get("research_strategy", "")),
                "adjustment_reasoning": adjusted_plan.get("adjustment_reasoning", ""),
                "is_adjusted_plan": True,
                "previous_plan": original_plan
            }
            
            new_questions = [q for q in adjusted_plan.get("sub_questions", []) if q.get("status", "") == "new"]
            modified_questions = [q for q in adjusted_plan.get("sub_questions", []) if q.get("status", "") == "modified"]
            
            logger.info(f"📝 Plan adjusted: {len(adjusted_plan.get('sub_questions', []))} sub-questions")
            logger.info(f"📝 Question status: new={len(new_questions)}, modified={len(modified_questions)}")
            
            if self.step_callback:
                message = f"📝 Crypto research plan adjusted based on feedback"
                self.step_callback(self.step, message)
            
        except Exception as e:
            logger.error(f"📝 Error during re-planning: {str(e)}")
            if self.step_callback: 
                self.step_callback("ERROR", f"📝 Error adjusting crypto research plan: {str(e)}")
            
            # Keep original plan with error note
            state["planner_result"] = {
                **original_plan,
                "error": str(e),
                "is_adjusted_plan": True,
                "adjustment_reasoning": "Failed to adjust plan due to error"
            }
        
        state["last_node"] = "re_plan"
        return state