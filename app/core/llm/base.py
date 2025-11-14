from abc import ABC, abstractmethod
from typing import List, Dict, Any


class BaseLLMClient(ABC):
    @abstractmethod
    def generate_response(
            self, 
            messages: List[Dict[str, str]], 
            full_response: bool = False,
            **kwargs
        ) -> str|Any:
        pass
    
    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        pass