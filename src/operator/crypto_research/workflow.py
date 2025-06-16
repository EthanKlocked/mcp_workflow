import os
from datetime import datetime
from core.langchain_agent import LangChainAgent
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from langgraph.graph import StateGraph
from typing import Dict, Any
from roles.listener import Listener
from roles.planner import Planner
from roles.replier import Replier
from roles.researcher import Researcher
from roles.reviewer import Reviewer
from roles.reporter import Reporter

# Logger
import logging
logger = logging.getLogger("crypto_research_workflow")

class DeepResearchService:
    """Cryptocurrency Deep Research Workflow Service"""
    
    def __init__(self, model_key: str = "gpt41", step_callback=None):
        self.langchain_client = LangChainAgent(model_key=model_key)
        self.step_callback = step_callback
        self.session = None
        
        # Role agents - initialized in execute()
        self.listener = None
        self.planner = None
        self.replier = None
        self.researcher = None
        self.reviewer = None
        self.reporter = None
        
    async def _initialize_agents(self, session: ClientSession):
        """Initialize all role agents with MCP session"""
        try:
            logger.info("🔧 Initializing crypto research agents...")
            
            # Create agents for each role
            listener_agent = await self.langchain_client.create_agent(session, "listener_agent")
            planner_agent = await self.langchain_client.create_agent(session, "planner_agent")
            replier_agent = await self.langchain_client.create_agent(session, "replier_agent")
            researcher_agent = await self.langchain_client.create_agent(session, "researcher_agent")
            reviewer_agent = await self.langchain_client.create_agent(session, "reviewer_agent")
            reporter_agent = await self.langchain_client.create_agent(session, "reporter_agent")
            
            # Validate agents
            agents = [listener_agent, planner_agent, replier_agent, researcher_agent, reviewer_agent, reporter_agent]
            if not all(agents):
                raise ValueError("Failed to create one or more agents")
            
            # Initialize role objects
            self.listener = Listener(listener_agent, step_callback=self.step_callback)
            self.planner = Planner(planner_agent, step_callback=self.step_callback)
            self.replier = Replier(replier_agent, step_callback=self.step_callback)
            self.researcher = Researcher(researcher_agent, step_callback=self.step_callback)
            self.reviewer = Reviewer(reviewer_agent, step_callback=self.step_callback)
            self.reporter = Reporter(reporter_agent, step_callback=self.step_callback)
            
            logger.info("✅ All crypto research agents initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize agents: {str(e)}")
            raise
    
    def _build_workflow(self) -> StateGraph:
        """Build the crypto research workflow graph"""
        logger.info("🔗 Building crypto research workflow...")
        
        workflow = StateGraph(Dict[str, Any])
        
        # Add workflow nodes
        workflow.add_node("listen", self.listener.process)
        workflow.add_node("reply", self.replier.process)
        workflow.add_node("plan", self.planner.process)
        workflow.add_node("research", self.researcher.process)
        workflow.add_node("review", self.reviewer.process)
        workflow.add_node("report", self.reporter.process)
        
        # Add re-iteration nodes
        workflow.add_node("re_plan", self.planner.process)
        workflow.add_node("re_research", self.researcher.process)
        
        # Define workflow edges
        workflow.add_conditional_edges(
            "listen",
            self.listener._should_continue,
            {
                "continue": "plan",
                "stop": "reply"
            }
        )
        
        # Main workflow path
        workflow.add_edge("plan", "research")
        workflow.add_edge("research", "review")
        
        # Review decision point
        workflow.add_conditional_edges(
            "review",
            self.reviewer._should_improve,
            {
                "improve": "re_plan",
                "finalize": "report"
            }
        )
        
        # Re-iteration path
        workflow.add_edge("re_plan", "re_research")
        workflow.add_edge("re_research", "review")
        
        # Set entry point
        workflow.set_entry_point("listen")
        
        logger.info("✅ Crypto research workflow built successfully")
        return workflow
    
    async def execute(self, query: str) -> Dict[str, Any]:
        """
        Execute the cryptocurrency deep research workflow
        
        Args:
            query: User's crypto research query
            
        Returns:
            Comprehensive analysis results
        """
        try:
            logger.info(f"🚀 Starting crypto research workflow for query: {query}")
            
            # MCP server connection
            mcp_server_url = f"http://{os.getenv('MCP_SERVER_HOST', 'localhost')}:{os.getenv('MCP_SERVER_PORT', '8000')}/mcp"
            
            # Create session and execute workflow
            async with streamablehttp_client(mcp_server_url) as (read, write, _):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    logger.info("✅ MCP session initialized")
                    
                    # Initialize all agents
                    await self._initialize_agents(session)
                    
                    # Build and compile workflow
                    workflow = self._build_workflow()
                    graph = workflow.compile()
                    
                    # Prepare initial state
                    initial_state = {
                        "query": query,
                        "session": session,  # Pass session to roles
                        "iteration": 0,
                        "max_iterations": 3,
                        "current_date": datetime.now().strftime('%Y-%m-%d'),
                        
                        # Results storage
                        "listener_result": {},
                        "planner_result": {},
                        "researcher_result": {},
                        "reviewer_result": {},
                        "reporter_result": {},
                        
                        # History tracking
                        "analysis_history": [],
                        "feedback_history": [],
                        "scores_history": [],
                        "tools_used": []
                    }
                    
                    # Execute workflow
                    logger.info("🔄 Executing crypto research workflow...")
                    result = await graph.ainvoke(initial_state)
                    
                    # Format final results
                    final_result = {
                        "status": "success",
                        "query": query,
                        "final_result": result.get("final_result", "No result generated"),
                        "iterations": result.get("iteration", 0),
                        "execution_time": datetime.now().isoformat(),
                        
                        # Analysis details
                        "analysis_details": {
                            "research_plan": result.get("planner_result", {}).get("main_question", ""),
                            "collected_data": result.get("researcher_result", {}).get("collected_data", []),
                            "final_evaluation": result.get("reviewer_result", {}).get("evaluation", {}),
                            "tools_used": result.get("tools_used", [])
                        },
                        
                        # Process history
                        "history": {
                            "analysis_history": result.get("analysis_history", []),
                            "feedback_history": result.get("feedback_history", []),
                            "scores_history": result.get("scores_history", [])
                        }
                    }
                    
                    logger.info(f"✅ Crypto research workflow completed successfully ({result.get('iteration', 0)} iterations)")
                    return final_result
                    
        except Exception as e:
            logger.error(f"❌ Error in crypto research workflow: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "message": f"Error in crypto research workflow: {str(e)}",
                "query": query,
                "timestamp": datetime.now().isoformat()
            }

# Helper functions
async def run_crypto_research(query: str, model_key: str = "gpt41", step_callback=None) -> Dict[str, Any]:
    """
    Execute cryptocurrency deep research analysis
    
    Args:
        query: Crypto research query
        model_key: Model to use for analysis
        step_callback: Progress callback function
        
    Returns:
        Analysis results
    """
    service = DeepResearchService(model_key=model_key, step_callback=step_callback)
    return await service.execute(query)

# Test function
async def test_crypto_research():
    """Test cryptocurrency research workflow"""
    test_queries = [
        "비트코인의 현재 시장 상황을 온체인 데이터와 소셜 sentiment를 통해 종합 분석해줘",
        "지난 7일간 주요 거래소들의 자금 흐름과 고래 거래 패턴을 분석해줘",
        "이더리움의 기술적 지표와 네트워크 건전성을 분석하고 투자 전략을 제시해줘"
    ]
    
    def progress_callback(step: str, message: str):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {step}: {message}")
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n{'='*60}")
        print(f"🧪 테스트 {i}/{len(test_queries)}: {query}")
        print(f"{'='*60}")
        
        try:
            result = await run_crypto_research(query, step_callback=progress_callback)
            
            if result["status"] == "success":
                print(f"\n✅ 분석 성공!")
                print(f"🔄 반복 횟수: {result['iterations']}")
                print(f"⏱️ 완료 시간: {result['execution_time']}")
                
                # Show result preview
                final_result = result['final_result']
                preview = final_result[:500] + "..." if len(final_result) > 500 else final_result
                print(f"\n📊 결과 미리보기:\n{preview}")
                
            else:
                print(f"\n❌ 분석 실패: {result['message']}")
                
        except Exception as e:
            print(f"\n💥 테스트 오류: {str(e)}")
        
        if i < len(test_queries):
            print(f"\n⏸️ 다음 테스트까지 3초 대기...")
            import asyncio
            await asyncio.sleep(3)

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_crypto_research())