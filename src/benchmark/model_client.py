import os
import sys
from abc import ABC, abstractmethod

class ModelClient(ABC):
    """
    Abstract base class for all AI Model Clients.
    Provides a unified interface for patch generation.
    """
    def __init__(self, model_name: str, temperature: float = 0.2, max_tokens: int = 2000):
        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens

    @abstractmethod
    def generate_patch(self, system_prompt: str, user_prompt: str) -> str:
        """
        Sends the prompts to the model and returns the generated patch content.
        """
        pass


class OpenAIClient(ModelClient):
    """
    Client for OpenAI models (GPT-4o, GPT-3.5, etc.)
    """
    def generate_patch(self, system_prompt: str, user_prompt: str) -> str:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set.")
            
        try:
            import openai
        except ImportError:
            raise ImportError("The 'openai' library is not installed. Run 'pip install openai' to use OpenAIClient.")
            
        client = openai.OpenAI(api_key=api_key)
        
        response = client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=self.temperature,
            max_tokens=self.max_tokens
        )
        return response.choices[0].message.content


class ClaudeClient(ModelClient):
    """
    Client for Anthropic Claude models (Claude 3.5 Sonnet, etc.)
    """
    def generate_patch(self, system_prompt: str, user_prompt: str) -> str:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable is not set.")
            
        try:
            import anthropic
        except ImportError:
            raise ImportError("The 'anthropic' library is not installed. Run 'pip install anthropic' to use ClaudeClient.")
            
        client = anthropic.Anthropic(api_key=api_key)
        
        response = client.messages.create(
            model=self.model_name,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_prompt}
            ]
        )
        return response.content[0].text


class GeminiClient(ModelClient):
    """
    Client for Google Gemini models (Gemini 1.5 Pro, Flash, etc.)
    """
    def generate_patch(self, system_prompt: str, user_prompt: str) -> str:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is not set.")
            
        try:
            # Try newer google-genai client first
            from google import genai
            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model=self.model_name,
                contents=f"{system_prompt}\n\n{user_prompt}",
                config={"temperature": self.temperature, "max_output_tokens": self.max_tokens}
            )
            return response.text
        except ImportError:
            # Fall back to google-generativeai client
            try:
                import google.generativeai as genai
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel(self.model_name)
                # Combine system prompt with contents
                response = model.generate_content(
                    f"System Directives:\n{system_prompt}\n\nUser Request:\n{user_prompt}",
                    generation_config={"temperature": self.temperature, "max_output_tokens": self.max_tokens}
                )
                return response.text
            except ImportError:
                raise ImportError(
                    "Neither 'google-genai' nor 'google-generativeai' library is installed. "
                    "Run 'pip install google-genai' to use GeminiClient."
                )


class GroqClient(ModelClient):
    """
    Client for Groq API using Llama-3.1-8b-instant.
    """
    def __init__(self, model_name: str = "llama-3.1-8b-instant", temperature: float = 0.1, max_tokens: int = 1500):
        super().__init__(model_name, temperature, max_tokens)
        self.api_key = os.environ.get("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY environment variable is not set.")

    def generate_patch(self, system_prompt: str, user_prompt: str) -> str:
        import requests
        import time
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens
        }
        
        # Free-tier rate limit handler
        retry_delay = 5
        max_retries = 3
        
        for attempt in range(max_retries):
            response = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                json=payload,
                headers=headers
            )
            
            if response.status_code == 200:
                return response.json()["choices"][0]["message"]["content"]
            elif response.status_code == 429:
                print(f"  [WARNING] Groq API rate limited (429). Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 2
            else:
                raise Exception(f"Groq API Error: {response.status_code} - {response.text}")
                
        raise Exception("Failed to get response from Groq API after multiple retries due to rate limiting.")


class MockModelClient(ModelClient):
    """
    A Mock Model Client for testing the benchmark runner without API keys or remote calls.
    Returns pre-configured patch diffs matching expected tasks.
    """
    def __init__(self, model_name: str = "mock-model", temperature: float = 0.2, max_tokens: int = 2000):
        super().__init__(model_name, temperature, max_tokens)
        self.mock_registry = {}
        self._load_default_mocks()
        
    def register_mock(self, task_id: str, patch_content: str):
        self.mock_registry[task_id] = patch_content
        
    def _load_default_mocks(self):
        # Default mock for test_microservice: Modify getUserById to return 'Ajeem Modified'
        self.register_mock(
            "task_modify_get_user",
            """```diff
--- api.js
+++ api.js
@@ -8,3 +8,3 @@
 const getUserById = () => {
-    return { "user": "Ajeem" };
+    return { "user": "Ajeem Modified" };
 }
```"""
        )
        
        # Default mock for testing1: Add lockout policy scenario
        self.register_mock(
            "task_lockout_policy",
            """```diff
--- src/services/auth.service.js
+++ src/services/auth.service.js
@@ -42,3 +42,9 @@
     if (!user) {
       throw CustomError.unauthorized('Invalid credentials');
     }
+    
+    if (user.failedAttempts >= 5) {
+      throw CustomError.forbidden('Account is locked due to multiple failed login attempts');
+    }
```"""
        )

    def generate_patch(self, system_prompt: str, user_prompt: str) -> str:
        # Match task_id from user prompt or use default fallback
        for task_id, patch in self.mock_registry.items():
            if task_id in user_prompt or task_id in system_prompt:
                return patch
                
        # Return first registry item if no exact match found
        if self.mock_registry:
            return list(self.mock_registry.values())[0]
            
        return "No mock registered."
