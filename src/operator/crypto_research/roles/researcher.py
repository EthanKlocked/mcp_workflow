# roles/researcher.py
import asyncio
from typing import Dict, Any, List, Tuple
from .base import BaseRole

# Logger
import logging
logger = logging.getLogger("crypto_research_workflow")

class Researcher(BaseRole):
    """Conducts comprehensive crypto data collection and analysis"""
    
    def __init__(self, agent, step_callback=None):
        super().__init__(agent, step_callback)
        self.step = "RESEARCH"
    
    async def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        planner_result = state.get("planner_result", {})
        
        logger.info(f"🔍 Researcher process started for query: {state.get('query', '')}")
        
        # Check if this is additional research
        is_additional = "re_research" in state.get("last_node", "") or state.get("iteration", 0) > 0
        
        # Get sub-questions from the plan
        sub_questions = planner_result.get("sub_questions", [])
        
        logger.info(f"🔍 Research mode: {'additional' if is_additional else 'initial'} with {len(sub_questions)} sub-questions")
        
        if is_additional:
            if self.step_callback: 
                self.step_callback(self.step, f"🔍 Performing additional crypto research for {len(sub_questions)} sub-questions")
            research_mode = "additional"
        else:
            if self.step_callback: 
                self.step_callback(self.step, f"🔍 Performing initial crypto research for {len(sub_questions)} sub-questions")
            research_mode = "initial"
        
        # Execute research tasks
        formatted_sub_questions = "\n".join(
            [f"{idx+1}. {sub_q.get('question', '')}" for idx, sub_q in enumerate(sub_questions)]
        )
        if self.step_callback:
            self.step_callback(
                self.step,
                f"🔍 Processing {len(sub_questions)} crypto sub-questions:\n{formatted_sub_questions}"
            )
        
        research_tasks = []
        for sq_index, sub_q in enumerate(sub_questions):
            task = self._research_sub_question(state, sub_q, sq_index, len(sub_questions))
            research_tasks.append(task)
        
        results = await asyncio.gather(*research_tasks, return_exceptions=True)
        collected_data = []
        
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"🔍 Error in crypto research task: {str(result)}")
                collected_data.append({
                    "question": "Error occurred",
                    "error": str(result),
                    "results": []
                })
            else:
                collected_data.append(result)
        
        logger.info(f"🔍 All crypto sub-questions researched")
        if self.step_callback: 
            self.step_callback(self.step, f"🔍 Collected crypto data from {len(collected_data)} sub-questions")
        
        # Analyze the collected crypto data
        await self._analyze_crypto_data(state, collected_data, research_mode)
        
        state["last_node"] = "research" if not is_additional else "re_research"
        
        logger.info(f"🔍 Crypto research process completed with {len(collected_data)} data points")
        
        return state
    
    async def _research_sub_question(self, state: Dict[str, Any], sub_q: Dict[str, Any], sq_index: int, total_questions: int) -> Dict[str, Any]:
        question_text = sub_q.get("question", "")
        tools = sub_q.get("tools", ["comprehensive_technical_analysis"])
        parameters = sub_q.get("parameters", {})
        priority = sub_q.get("priority", "Medium")
        research_direction = sub_q.get("research_direction", "")
        
        logger.info(f"🔍 Starting crypto research for sub-question {sq_index+1}/{total_questions}: {question_text}")
        
        try:
            research_prompt = f"""
            # Autonomous Cryptocurrency Research Task

            ## Today's Date
            Today is {state["current_date"]}

            ## Question to Research
            "{question_text}"

            ## Research Guidelines
            Priority: {priority}
            Research Direction: {research_direction}

            ## Suggested Approach
            Suggested Tools: {tools}
            Suggested Parameters: {parameters}
            
            ## Task
            As a crypto research expert, conduct comprehensive research on this question and deliver actionable insights.

            Your research approach should:
            1. Determine the most effective crypto research strategy for this specific question
            2. Use appropriate tools to gather relevant data:
               - For technical analysis: Use RSI, moving averages, Bollinger Bands tools
               - For onchain analysis: Use whale monitoring, exchange flow analysis
               - For social sentiment: Use Reddit sentiment, social trend analysis
               - For market data: Use price data, trading position tools
               - For news analysis: Use latest news, breaking news tools

            3. Strategic considerations:
               - High priority questions: Use comprehensive analysis with multiple data sources
               - Medium priority: Use balanced approach with key indicators
               - Low priority: Use focused, efficient analysis
               - Consider crypto market volatility and 24/7 trading nature
               - Account for correlation between different crypto assets

            4. After gathering data, provide analysis that:
               - Identifies key market insights, patterns, and trends
               - Evaluates reliability and significance of findings
               - Addresses limitations or gaps in data
               - Synthesizes comprehensive answer with actionable crypto insights

            ## Output Structure
            Provide your response in this format:
            1. **Research Approach**: Brief description of your strategy
            2. **Data Collection**: Summary of tools used and data gathered
            3. **Key Findings**: Main insights and patterns discovered
            4. **Analysis**: Comprehensive interpretation of the data
            5. **Conclusions**: Direct answer to the research question with actionable insights

            Focus on delivering high-quality crypto market insights rather than just collecting data.
            """
            
            research_result = await self.agent.ainvoke({"messages": research_prompt})
            research_content = research_result["messages"][-1].content
            
            # Get summary for callback
            if "Key Findings" in research_content:
                findings_section = research_content.split("Key Findings")[1].split("Analysis")[0] if "Analysis" in research_content else research_content.split("Key Findings")[1]
                summary = findings_section.strip()[:300] + "..." if len(findings_section) > 300 else findings_section.strip()
            else:
                summary = research_content[:300] + "..." if len(research_content) > 300 else research_content
            
            if self.step_callback:
                self.step_callback(
                    self.step,
                    f"💡 Sub-question {sq_index+1} insight: {summary}"
                )
            
            logger.info(f"🔍 Completed crypto research for sub-question {sq_index+1}")
            
            return {
                "question": question_text,
                "results": research_content,
                "priority": priority,
                "research_direction": research_direction
            }
            
        except Exception as e:
            logger.error(f"🔍 Error researching crypto sub-question {sq_index+1}: {str(e)}")
            if self.step_callback: 
                self.step_callback(self.step, f"🔍 Error in sub-question {sq_index+1}: {str(e)}")
            
            return {
                "question": question_text,
                "error": str(e),
                "results": f"Research failed for: {question_text}"
            }
    
    async def _analyze_crypto_data(self, state: Dict[str, Any], collected_data: List[Dict[str, Any]], research_mode: str) -> Dict[str, Any]:
        query = state["query"]
        planner_result = state.get("planner_result", {})
        main_question = planner_result.get("main_question", query)
        research_strategy = planner_result.get("research_strategy", "")
        
        logger.info(f"🔍 Starting analysis of {len(collected_data)} crypto data points for question: {main_question}")
        
        # For additional research, include previous analysis
        previous_analysis = ""
        if research_mode == "additional" and "researcher_result" in state:
            previous_analysis = state["researcher_result"].get("analysis", "")
        
        # Construct crypto analysis prompt
        analysis_prompt = f"""
        # Cryptocurrency Data Analysis and Synthesis
        
        ## Research Question
        Main Question: "{main_question}"
        Original Query: "{query}"
        
        ## Research Strategy Used
        {research_strategy}
        
        ## Collected Research Data
        """
        
        # Add each sub-question's research results
        for i, data in enumerate(collected_data, 1):
            analysis_prompt += f"""
        ### Sub-Question {i}: {data.get('question', 'Unknown')}
        Priority: {data.get('priority', 'Medium')}
        Research Direction: {data.get('research_direction', 'General')}
        
        Results:
        {data.get('results', 'No results available')}
        
        ---
        """
        
        analysis_prompt += f"""
        ## Task
        Analyze all the cryptocurrency research data collected and synthesize a comprehensive answer to the main research question.
        
        Your crypto analysis should:
        1. **Integrate Findings**: Connect insights from each sub-question into a coherent narrative
        2. **Identify Patterns**: Highlight key crypto market patterns, trends, and correlations
        3. **Assess Reliability**: Evaluate the quality and significance of the crypto data
        4. **Address Gaps**: Note any limitations or missing information in the analysis
        5. **Provide Insights**: Offer balanced, objective crypto market assessment
        6. **Consider Context**: Account for crypto-specific factors like volatility, 24/7 trading, market psychology
        7. **Actionable Conclusions**: Include practical insights for crypto investors/traders where appropriate
        
        Structure your analysis to flow logically from evidence to insights to implications.
        """
        
        if research_mode == "additional":
            analysis_prompt += f"""
        
        ## Previous Analysis
        {previous_analysis}
        
        **Important**: Build upon and improve the previous crypto analysis by incorporating the new research data.
        Highlight newly discovered insights or refined understanding of crypto market dynamics.
        """
        
        try:
            # Generate crypto analysis
            analysis_result = await self.agent.ainvoke({"messages": analysis_prompt})
            analysis_content = analysis_result["messages"][-1].content
            
            # Store results
            state["researcher_result"] = {
                "collected_data": collected_data,
                "analysis": analysis_content,
                "research_mode": research_mode,
                "data_quality": self._assess_data_quality(collected_data)
            }
            
            # Store in history for tracking
            analysis_history = state.get("analysis_history", [])
            analysis_history.append(analysis_content)
            state["analysis_history"] = analysis_history
            
            logger.info(f"🔍 Crypto analysis completed successfully ({len(analysis_content)} chars)")
            if self.step_callback: 
                self.step_callback(self.step, f"🔍 Crypto analysis synthesis completed")
                
        except Exception as e:
            logger.error(f"🔍 Error during crypto analysis: {str(e)}")
            if self.step_callback: 
                self.step_callback(self.step, f"🔍 Error analyzing crypto data: {str(e)}")
            
            # Create basic analysis in case of error
            error_analysis = f"Crypto analysis could not be completed due to an error: {str(e)}\n\nBasic summary of collected data:\n"
            for i, data in enumerate(collected_data, 1):
                if 'error' not in data:
                    error_analysis += f"{i}. {data.get('question', 'Unknown')}: Data collected successfully\n"
                else:
                    error_analysis += f"{i}. {data.get('question', 'Unknown')}: {data.get('error', 'Unknown error')}\n"
            
            state["researcher_result"] = {
                "collected_data": collected_data,
                "analysis": error_analysis,
                "error": str(e),
                "research_mode": research_mode,
                "data_quality": 0
            }
            
            # Store in history
            analysis_history = state.get("analysis_history", [])
            analysis_history.append(error_analysis)
            state["analysis_history"] = analysis_history
        
        return state
    
    def _assess_data_quality(self, collected_data: List[Dict]) -> int:
        """Assess overall data quality score (0-10)"""
        if not collected_data:
            return 0
        
        successful_collections = len([d for d in collected_data if 'error' not in d])
        total_collections = len(collected_data)
        
        # Base score from success rate
        success_rate = successful_collections / total_collections
        base_score = success_rate * 10
        
        # Adjust for data richness
        avg_content_length = 0
        if successful_collections > 0:
            total_length = sum(len(d.get('results', '')) for d in collected_data if 'error' not in d)
            avg_content_length = total_length / successful_collections
        
        # Bonus for comprehensive data
        if avg_content_length > 2000:
            base_score = min(base_score + 1, 10)
        elif avg_content_length < 500:
            base_score = max(base_score - 1, 0)
        
        return int(base_score)