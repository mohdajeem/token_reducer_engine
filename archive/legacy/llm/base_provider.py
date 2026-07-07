from abc import ABC, abstractmethod

class BaseLLMProvider(ABC):
    @abstractmethod
    def invoke(self, prompt):
        pass