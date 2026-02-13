"""LLM Router - Handles multiple LLM providers"""

import os
from typing import AsyncGenerator, Optional, Dict, Any
from abc import ABC, abstractmethod

import httpx
from openai import AsyncOpenAI


class LLMProvider(ABC):
    """Abstract base class for LLM providers"""
    
    @abstractmethod
    async def chat(
        self,
        message: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Send a chat message and return response"""
        pass
    
    @abstractmethod
    async def stream(
        self,
        message: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Stream chat response"""
        pass


class OpenAIProvider(LLMProvider):
    """OpenAI GPT provider"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key not provided")
        self.client = AsyncOpenAI(api_key=self.api_key)
    
    async def chat(
        self,
        message: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        model = model or "gpt-4"
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": message})
        
        response = await self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        
        return {
            "response": response.choices[0].message.content,
            "model": response.model,
            "provider": "openai",
            "tokens_used": response.usage.total_tokens if response.usage else None,
        }
    
    async def stream(
        self,
        message: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        model = model or "gpt-4"
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": message})
        
        stream = await self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            stream=True,
        )
        
        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content


class AnthropicProvider(LLMProvider):
    """Anthropic Claude provider"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("Anthropic API key not provided")
        self.base_url = "https://api.anthropic.com/v1"
    
    async def chat(
        self,
        message: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        model = model or "claude-3-opus-20240229"
        max_tokens = max_tokens or 1024
        
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        
        data = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [{"role": "user", "content": message}],
        }
        
        if system_prompt:
            data["system"] = system_prompt
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/messages",
                headers=headers,
                json=data,
            )
            response.raise_for_status()
            result = response.json()
        
        return {
            "response": result["content"][0]["text"],
            "model": result["model"],
            "provider": "anthropic",
            "tokens_used": result.get("usage", {}).get("input_tokens", 0) + result.get("usage", {}).get("output_tokens", 0),
        }
    
    async def stream(
        self,
        message: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        model = model or "claude-3-opus-20240229"
        
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        
        data = {
            "model": model,
            "max_tokens": 1024,
            "temperature": temperature,
            "messages": [{"role": "user", "content": message}],
            "stream": True,
        }
        
        if system_prompt:
            data["system"] = system_prompt
        
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/messages",
                headers=headers,
                json=data,
            ) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        event_data = line[6:]
                        if event_data != "[DONE]":
                            # Parse SSE event
                            import json
                            try:
                                event = json.loads(event_data)
                                if event.get("type") == "content_block_delta":
                                    yield event["delta"]["text"]
                            except json.JSONDecodeError:
                                pass


class LLMRouter:
    """Router for multiple LLM providers"""
    
    PROVIDERS = {
        "openai": OpenAIProvider,
        "anthropic": AnthropicProvider,
    }
    
    def __init__(self):
        self._providers: Dict[str, LLMProvider] = {}
    
    def get_provider(self, name: str) -> LLMProvider:
        """Get or create a provider instance"""
        if name not in self._providers:
            if name not in self.PROVIDERS:
                raise ValueError(f"Unknown provider: {name}")
            self._providers[name] = self.PROVIDERS[name]()
        return self._providers[name]
    
    async def chat(
        self,
        message: str,
        provider: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Route chat to appropriate provider"""
        provider = provider or os.getenv("DEFAULT_PROVIDER", "openai")
        llm = self.get_provider(provider)
        return await llm.chat(message, **kwargs)
    
    def list_providers(self) -> list:
        """List available providers"""
        available = []
        for name, provider_class in self.PROVIDERS.items():
            try:
                provider_class()  # Test instantiation
                available.append(name)
            except ValueError:
                pass  # Missing API key
        return available


# Global router instance
router = LLMRouter()
