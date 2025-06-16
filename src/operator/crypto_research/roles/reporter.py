# roles/reporter.py
from typing import Dict, Any
from .base import BaseRole

# Logger
import logging
logger = logging.getLogger("crypto_research_workflow")

class Reporter(BaseRole):
    """Generates comprehensive crypto analysis reports"""
    
    def __init__(self, agent, step_callback=None):
        super().__init__(agent, step_callback)
        self.step = "REPORT"
    
    async def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        logger.info(f"📊 Reporter process started for query: {state.get('query', '')}")
        if self.step_callback: 
            self.step_callback(self.step, f"started to generate final crypto report")
        
        query = state["query"]
        listener_result = state.get("listener_result", {})
        planner_result = state.get("planner_result", {})
        researcher_result = state.get("researcher_result", {})
        reviewer_result = state.get("reviewer_result", {})
        
        # Get important information
        main_question = planner_result.get("main_question", query)
        core_intent = listener_result.get("core_intent", "")
        domain = listener_result.get("domain", "crypto_general")
        required_data_sources = listener_result.get("required_data_sources", [])
        data_quality = researcher_result.get("data_quality", 0)
        
        # Get analysis history and feedback
        analysis_history = state.get("analysis_history", [])
        feedback_history = state.get("feedback_history", [])
        scores_history = state.get("scores_history", [])
        
        # Get current analysis and evaluation
        analysis = researcher_result.get("analysis", "")
        average_score = reviewer_result.get("average_score", 0)
        iterations = state.get("iteration", 0)
        
        logger.info(f"📊 Generating crypto report for question: '{main_question}'")
        logger.info(f"📊 Report context - domain: {domain}, iterations: {iterations}, final score: {average_score}/10")
        
        # Construct crypto reporting prompt
        report_prompt = f"""
        # Final Cryptocurrency Analysis Report Generation

        ## Today's Date  
        Today is {state["current_date"]}

        ## Research Context
        Original Query: "{query}"
        Main Research Question: "{main_question}"
        Core Intent: "{core_intent}"
        Domain: {domain}
        Required Data Sources: {", ".join(required_data_sources)}
        Data Quality Score: {data_quality}/10

        ## Analysis Process Summary
        - Research cycles completed: {iterations}
        - Final analysis quality: {average_score:.1f}/10
        - Research approach: Multi-agent iterative analysis with expert review

        ## Latest Comprehensive Analysis
        {analysis}

        ## Analysis Evolution Summary
        The analysis has undergone {iterations} refinement cycles with progressive improvements:
        {chr(10).join([f"Cycle {i+1}: Quality {score.get('average_score', 0):.1f}/10" for i, score in enumerate(scores_history)])}

        ## Expert Review Insights
        Key improvement areas identified across iterations:
        {chr(10).join([f"Review {i+1}: {feedback[:200]}..." for i, feedback in enumerate(feedback_history)])}

        ## Task
        Create a comprehensive, professional cryptocurrency analysis report that effectively answers the user's query.

        Your report should:

        ### Structure & Content
        1. **Executive Summary**: Key findings and main conclusions (2-3 paragraphs)
        2. **Comprehensive Analysis**: Detailed examination of all relevant crypto market aspects
        3. **Supporting Evidence**: Specific data points, market indicators, and trends
        4. **Risk Assessment**: Potential risks and opportunities identified
        5. **Actionable Insights**: Practical recommendations for crypto investors/traders
        6. **Market Outlook**: Short-term and medium-term perspective
        7. **Conclusion**: Clear, direct answer to the original question

        ### Quality Guidelines
        - **Data-Driven**: Use specific numbers, percentages, and concrete examples
        - **Balanced**: Present both opportunities and risks objectively
        - **Actionable**: Include practical insights for decision-making
        - **Professional**: Maintain analytical rigor and clear communication
        - **Crypto-Specific**: Address unique aspects of cryptocurrency markets

        ### Technical Considerations
        - If original query was in non-English, provide the ENTIRE report in that language
        - Use proper Markdown formatting for readability
        - Include relevant crypto terminology with context
        - Cite specific market conditions and timeframes where applicable
        - Avoid exposing internal process details or system references

        ### Evidence Integration
        - Extract the strongest insights from all analysis iterations
        - Synthesize findings into coherent, non-repetitive narrative
        - Build logical flow from evidence to insights to implications
        - Focus on crypto market dynamics and investor implications

        ### Target Audience
        Crypto investors, traders, and analysts who need evidence-based information for cryptocurrency decision-making.

        ## Important Notes
        - This is the final deliverable - make it comprehensive and professional
        - Do not mention the multi-agent research process or internal iterations
        - Focus on crypto market insights and actionable intelligence
        - Include appropriate disclaimers about market risks and volatility
        """
        
        try:
            # Generate comprehensive crypto report
            report_result = await self.agent.ainvoke({"messages": report_prompt})
            report_content = report_result["messages"][-1].content
            
            logger.info(f"📊 Crypto report generated successfully ({len(report_content)} chars)")
            
            # Add disclaimer if not already present
            if "disclaimer" not in report_content.lower():
                report_content += "\n\n---\n**Disclaimer**: This analysis is for educational purposes only. Cryptocurrency trading involves significant risk. Always conduct your own research and consider consulting with a financial advisor before making investment decisions."
            
            # Store results
            state["reporter_result"] = {
                "final_report": report_content,
                "iterations": iterations,
                "final_score": average_score,
                "data_quality": data_quality,
                "data_sources_analyzed": required_data_sources,
                "report_length": len(report_content)
            }
            
            # Store as final result
            state["final_result"] = report_content
            
            logger.info(f"📊 Final crypto report generated after {iterations} iterations")
            if self.step_callback: 
                self.step_callback(self.step, f"📊 Final crypto report generated ({len(report_content)} chars, score: {average_score:.1f}/10)")
            
        except Exception as e:
            logger.error(f"📊 Error generating final crypto report: {str(e)}")
            if self.step_callback: 
                self.step_callback(self.step, f"📊 Error generating final crypto report: {str(e)}")
            
            # Create fallback report
            fallback_report = f"""
            # Cryptocurrency Analysis Report

            ## Research Question
            {main_question}

            ## Executive Summary
            This report was generated following a {iterations}-cycle research process with a final quality score of {average_score:.1f}/10.

            ## Analysis Summary
            {analysis[:1000]}{"..." if len(analysis) > 1000 else ""}

            ## Key Findings
            - Research completed through {iterations} iterative cycles
            - Data quality score: {data_quality}/10
            - Analysis focused on: {", ".join(required_data_sources)}

            ## Limitations
            The complete report generation encountered an error: {str(e)}

            ## Disclaimer
            This analysis is for educational purposes only. Cryptocurrency trading involves significant risk. Always conduct your own research and consider consulting with a financial advisor before making investment decisions.
            """
            
            # Store fallback results
            state["reporter_result"] = {
                "final_report": fallback_report,
                "error": str(e),
                "iterations": iterations,
                "final_score": average_score,
                "data_quality": data_quality,
                "report_length": len(fallback_report)
            }
            
            # Store as final result
            state["final_result"] = fallback_report
        
        # Track completion
        state["last_node"] = "report"
        
        success_status = 'success' if 'error' not in state['reporter_result'] else 'error'
        logger.info(f"📊 Reporter process completed with {success_status}")
        logger.info(f"📊 Crypto research workflow finished: {iterations} iterations, score {average_score:.1f}/10, data quality {data_quality}/10")
        
        return state