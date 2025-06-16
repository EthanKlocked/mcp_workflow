from abc import ABC, abstractmethod
from typing import Dict, Any, Callable, Optional
from core.logger import get_logger

logger = get_logger("crypto_research_roles")

class BaseRole(ABC):    
    def __init__(self, agent, step_callback: Optional[Callable] = None):
        self.agent = agent
        self.step_callback = step_callback
        self.role_name = self.__class__.__name__.lower()
    
    def _notify_step(self, step_name: str, data: Dict[str, Any]):
        if self.step_callback:
            self.step_callback(f"{self.role_name}_{step_name}", data)
    
    @abstractmethod
    async def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        pass