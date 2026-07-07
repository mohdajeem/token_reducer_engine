import os
from abc import ABC, abstractmethod

class TokenEstimator(ABC):
    @abstractmethod
    def estimate_tokens(self, text: str) -> int:
        """
        Estimates the number of tokens in the given text.
        """
        pass

class CharBasedTokenEstimator(TokenEstimator):
    def estimate_tokens(self, text: str) -> int:
        """
        Standard chars // 4 token approximation.
        """
        if not text:
            return 0
        return len(text) // 4

class GeminiCompatibleEstimator(TokenEstimator):
    def __init__(self):
        self.api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
        self.client = None
        if self.api_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.api_key)
                self.client = genai.GenerativeModel("gemini-1.5-flash")
            except Exception as e:
                # Silent fallback
                pass

    def estimate_tokens(self, text: str) -> int:
        if not text:
            return 0
        if self.client:
            try:
                response = self.client.count_tokens(text)
                return response.total_tokens
            except Exception as e:
                pass
        # High-fidelity offline fallback: characters / 3.75 for typical code
        return max(1, int(len(text) / 3.75))

class GroqLlamaEstimator(TokenEstimator):
    def estimate_tokens(self, text: str) -> int:
        if not text:
            return 0
        # High-fidelity Llama 3 offline heuristic: Llama 3 tokenizer has 128k vocab, 
        # which yields about 3.25 characters per token for typical code.
        return max(1, int(len(text) / 3.25))

class AutoEstimator(TokenEstimator):
    def __init__(self, provider: str = "gemini"):
        self.provider = provider.lower() if provider else "gemini"
        if self.provider == "gemini":
            self.estimator = GeminiCompatibleEstimator()
            self.estimator_type = "gemini"
        elif self.provider == "groq":
            self.estimator = GroqLlamaEstimator()
            self.estimator_type = "groq_llama"
        else:
            self.estimator = CharBasedTokenEstimator()
            self.estimator_type = "char_fallback"

    def estimate_tokens(self, text: str) -> int:
        return self.estimator.estimate_tokens(text)
