# roles/reviewer.py
from typing import Dict, Any
import json
import re
from .base import BaseRole

# Logger
import logging
logger = logging.getLogger("crypto_research_workflow")

class Reviewer(BaseRole):
    """Reviews and evaluates crypto analysis quality"""
    
    def __init__(self, agent, step_callback=None):
        super().__init__(agent, step_callback)
        self.step = "REVIEW"
    
    async def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        query = state["query"]
        planner_result = state.get("planner_result", {})
        researcher_result = state.get("researcher_result", {})
        
        logger.info(f"⭐ Reviewer process started for query: {query}")
        
        # Get the current analysis to review
        analysis = researcher_result.get("analysis", "")
        main_question = planner_result.get("main_question", query)
        sub_questions = planner_result.get("sub_questions", [])
        data_quality = researcher_result.get("data_quality", 0)
        
        logger.info(f"⭐ Reviewing crypto analysis for main question: '{main_question}'")
        logger.info(f"⭐ Analysis length: {len(analysis)} chars, data quality: {data_quality}/10")
        
        # Get iteration information
        iteration = state.get("iteration", 0)
        research_mode = researcher_result.get("research_mode", "initial")
        
        logger.info(f"⭐ Current iteration: {iteration}, research mode: {research_mode}")
        if self.step_callback: 
            self.step_callback(self.step, f"reviewing crypto research result [CYCLE : {iteration + 1}]")
        
        # Construct crypto-specific review prompt
        review_prompt = f"""
        # Cryptocurrency Analysis Review and Evaluation
        
        ## Research Context
        Main Question: "{main_question}"
        Original Query: "{query}"
        Research Iteration: {iteration + 1}
        Data Quality Score: {data_quality}/10
        
        ## Sub-Questions Addressed
        {json.dumps([sq.get("question") for sq in sub_questions], ensure_ascii=False, indent=2)}
        
        ## Crypto Analysis to Review
        {analysis}
        
        ## Task
        Critically evaluate the quality and completeness of this cryptocurrency analysis. 
        Your review should be thorough, balanced, and constructive, considering crypto-specific factors.
        
        Evaluation Criteria:

        1. **Technical Accuracy (1-10)**: 
        - Are crypto technical analysis and market data accurate?
        - Are trading concepts and terminology used correctly?
        - Do the conclusions align with the presented data?

        2. **Market Comprehensiveness (1-10)**:
        - Does it address all aspects of the crypto research question?
        - Are important crypto market factors considered?
        - Is the scope appropriate for the complexity of the question?

        3. **Analysis Depth (1-10)**:
        - Does it provide meaningful crypto market insights?
        - Are market dynamics and correlations properly analyzed?
        - Is there sufficient exploration of cause-and-effect relationships?

        4. **Clarity & Structure (1-10)**:
        - Is the crypto analysis well-organized and easy to follow?
        - Do conclusions flow logically from the evidence?
        - Is technical jargon explained appropriately?

        5. **Evidence Quality (1-10)**:
        - Are crypto claims supported by reliable data sources?
        - Is there appropriate use of multiple data types (technical, onchain, social, news)?
        - Are limitations and uncertainties acknowledged?
        
        ## Output Format
        Provide your evaluation in JSON format:
        ```json
        {{
          "scores": {{
            "technical_accuracy": 0,
            "market_comprehensiveness": 0,
            "analysis_depth": 0,
            "clarity_structure": 0,
            "evidence_quality": 0
          }},
          "average_score": 0.0,
          "strengths": [
            "Specific crypto analysis strength 1",
            "Specific crypto analysis strength 2"
          ],
          "weaknesses": [
            "Specific crypto analysis weakness 1", 
            "Specific crypto analysis weakness 2"
          ],
          "suggestions": [
            "Specific improvement suggestion 1",
            "Specific improvement suggestion 2"
          ],
          "missing_aspects": [
            "Important crypto aspect not covered 1",
            "Important crypto aspect not covered 2"
          ],
          "overall_assessment": "Summary of the crypto analysis quality and recommendations"
        }}
        ```
        
        After the JSON, provide detailed constructive feedback explaining your reasoning and offering 
        specific suggestions for improving the crypto analysis quality.
        """
        
        try:
            # Generate review
            review_result = await self.agent.ainvoke({"messages": review_prompt})
            review_content = review_result["messages"][-1].content
            
            logger.info(f"⭐ Crypto review generated, parsing results")
            
            # Extract JSON evaluation
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', review_content)
            if json_match:
                evaluation = json.loads(json_match.group(1))
            else:
                json_match = re.search(r'\{[\s\S]*\}', review_content)
                if json_match:
                    evaluation = json.loads(json_match.group(0))
                else:
                    raise ValueError("JSON evaluation not found in crypto review response")
            
            # Extract detailed feedback
            detailed_feedback = review_content
            if json_match:
                json_end_pos = review_content.find("```", json_match.end()) + 3
                if json_end_pos < 3:
                    detailed_feedback = review_content[json_match.end():]
                else:
                    detailed_feedback = review_content[json_end_pos:]
            
            # Calculate average score
            scores = evaluation.get("scores", {})
            score_values = [
                scores.get("technical_accuracy", 0),
                scores.get("market_comprehensiveness", 0),
                scores.get("analysis_depth", 0),
                scores.get("clarity_structure", 0),
                scores.get("evidence_quality", 0)
            ]
            average_score = sum(score_values) / len(score_values) if score_values else 0
            
            if "average_score" not in evaluation or evaluation["average_score"] == 0:
                evaluation["average_score"] = average_score
            
            logger.info(f"⭐ Crypto review scores - technical: {scores.get('technical_accuracy', 0)}, comprehensiveness: {scores.get('market_comprehensiveness', 0)}")
            logger.info(f"⭐ Average crypto analysis score: {average_score}")
            
            # Format the feedback
            formatted_feedback = f"""
            # Crypto Analysis Review (Iteration {iteration + 1})
            
            ## Overall Score: {evaluation.get('average_score', 0):.1f}/10
            
            ### Detailed Scores
            - Technical Accuracy: {scores.get('technical_accuracy', 0)}/10
            - Market Comprehensiveness: {scores.get('market_comprehensiveness', 0)}/10
            - Analysis Depth: {scores.get('analysis_depth', 0)}/10
            - Clarity & Structure: {scores.get('clarity_structure', 0)}/10
            - Evidence Quality: {scores.get('evidence_quality', 0)}/10
            
            ### Crypto Analysis Strengths
            {chr(10).join([f"✅ {s}" for s in evaluation.get('strengths', [])])}
            
            ### Areas for Improvement
            {chr(10).join([f"⚠️ {w}" for w in evaluation.get('weaknesses', [])])}
            
            ### Improvement Suggestions
            {chr(10).join([f"💡 {s}" for s in evaluation.get('suggestions', [])])}
            
            ### Missing Crypto Market Aspects
            {chr(10).join([f"❓ {m}" for m in evaluation.get('missing_aspects', [])])}
            
            ## Overall Assessment
            {evaluation.get('overall_assessment', 'No assessment provided')}
            
            ## Detailed Review Feedback
            {detailed_feedback.strip()}
            """
            
            # Store results
            state["reviewer_result"] = {
                "evaluation": evaluation,
                "feedback": formatted_feedback,
                "average_score": evaluation.get("average_score", average_score),
                "iteration": iteration,
                "research_mode": research_mode
            }
            
            # Store in history
            feedback_history = state.get("feedback_history", [])
            feedback_history.append(formatted_feedback)
            state["feedback_history"] = feedback_history
            
            scores_history = state.get("scores_history", [])
            scores_history.append({
                "iteration": iteration + 1,
                "average_score": average_score,
                "scores": scores,
                "data_quality": data_quality
            })
            state["scores_history"] = scores_history
            
            state["average_score"] = evaluation.get("average_score", average_score)
            
            logger.info(f"⭐ Crypto review completed successfully with score {average_score:.1f}/10")
            if self.step_callback: 
                self.step_callback(self.step, f"⭐ Crypto analysis review completed with score {average_score:.1f}/10")
                
        except Exception as e:
            logger.error(f"⭐ Error during crypto review: {str(e)}")
            if self.step_callback: 
                self.step_callback(self.step, f"⭐ Error reviewing crypto analysis: {str(e)}")
            
            # Create default evaluation for crypto analysis
            default_evaluation = {
                "scores": {
                    "technical_accuracy": 5,
                    "market_comprehensiveness": 5,
                    "analysis_depth": 5,
                    "clarity_structure": 5,
                    "evidence_quality": 5
                },
                "average_score": 5.0,
                "strengths": ["Unable to properly evaluate crypto analysis due to error"],
                "weaknesses": ["Review process encountered an error"],
                "suggestions": ["Try to improve overall crypto analysis quality"],
                "overall_assessment": f"Crypto review failed: {str(e)}"
            }
            
            error_feedback = f"""
            # Crypto Analysis Review (Iteration {iteration + 1})
            
            ## Review Error
            The crypto analysis review encountered an error: {str(e)}
            
            ## Default Assessment
            - Average Score: 5.0/10 (default due to error)
            - Data Quality: {data_quality}/10
            
            ## Recommendations
            - Consider simplifying the crypto analysis approach
            - Ensure all sub-questions are clearly addressed
            - Verify that conclusions are supported by crypto market data
            """
            
            state["reviewer_result"] = {
                "evaluation": default_evaluation,
                "feedback": error_feedback,
                "average_score": 5.0,
                "error": str(e),
                "iteration": iteration,
                "research_mode": research_mode
            }
            
            # Store in history
            feedback_history = state.get("feedback_history", [])
            feedback_history.append(error_feedback)
            state["feedback_history"] = feedback_history
            
            scores_history = state.get("scores_history", [])
            scores_history.append({
                "iteration": iteration + 1,
                "average_score": 5.0,
                "scores": default_evaluation["scores"],
                "error": True,
                "data_quality": data_quality
            })
            state["scores_history"] = scores_history
            
            state["average_score"] = 5.0
        
        # Increment iteration counter
        state["iteration"] = iteration + 1
        state["last_node"] = "review"
        
        next_step = self._should_improve(state)
        logger.info(f"⭐ Crypto review process completed for iteration {iteration}, next step: {next_step}")
        
        return state
    
    def _should_improve(self, state: Dict[str, Any]) -> str:
        iteration = state.get("iteration", 0)
        max_iterations = state.get("max_iterations", 3)
        average_score = state.get("average_score", 0)
        
        # Decision logic for crypto analysis
        if iteration >= max_iterations:
            return "finalize"
        elif average_score >= 8.5:
            return "finalize"
        else:
            return "improve"