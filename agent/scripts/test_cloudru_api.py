#!/usr/bin/env python3
"""Тестовый скрипт для проверки Cloud.ru Foundation Models API."""
import os
import sys
from dotenv import load_dotenv

load_dotenv()

def test_with_openai():
    """Тест с OpenAI клиентом (как в документации Cloud.ru)."""
    from openai import OpenAI
    
    api_key = os.getenv("LLM_API_KEY") or os.getenv("API_KEY")
    url = os.getenv("LLM_API_BASE") or "https://foundation-models.api.cloud.ru/v1"
    model = os.getenv("LLM_MODEL") or "Qwen/Qwen3-235B-A22B-Instruct-2507"
    
    # Убираем hosted_vllm/ префикс
    if model.startswith("hosted_vllm/"):
        model = model[len("hosted_vllm/"):]
    
    print(f"Testing Cloud.ru Foundation Models API")
    print(f"URL: {url}")
    print(f"Model: {model}")
    print(f"API Key: {api_key[:20]}..." if api_key else "API Key: NOT SET")
    print("-" * 50)
    
    client = OpenAI(
        api_key=api_key,
        base_url=url
    )
    
    try:
        # Попробуем получить список моделей
        print("\n1. Trying to list models...")
        try:
            models = client.models.list()
            print(f"Available models: {[m.id for m in models.data]}")
        except Exception as e:
            print(f"Failed to list models: {e}")
        
        # Попробуем сделать запрос
        print(f"\n2. Trying chat completion with model: {model}")
        response = client.chat.completions.create(
            model=model,
            max_tokens=100,
            temperature=0.5,
            messages=[
                {"role": "user", "content": "Привет! Скажи 'тест успешен'"}
            ]
        )
        print(f"Response: {response.choices[0].message.content}")
        print("\n✅ SUCCESS!")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        print(f"\nError type: {type(e).__name__}")


def test_with_httpx():
    """Тест с httpx напрямую."""
    import httpx
    
    api_key = os.getenv("LLM_API_KEY") or os.getenv("API_KEY")
    url = os.getenv("LLM_API_BASE") or "https://foundation-models.api.cloud.ru/v1"
    model = os.getenv("LLM_MODEL") or "Qwen/Qwen3-235B-A22B-Instruct-2507"
    
    if model.startswith("hosted_vllm/"):
        model = model[len("hosted_vllm/"):]
    
    print("\n" + "=" * 50)
    print("Testing with httpx directly")
    print("=" * 50)
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # Тест: POST /chat/completions
    print(f"\nPOST /chat/completions (model={model})")
    try:
        resp = httpx.post(
            f"{url}/chat/completions",
            headers=headers,
            json={
                "model": model,
                "messages": [{"role": "user", "content": "test"}],
                "max_tokens": 50
            },
            timeout=30
        )
        print(f"   Status: {resp.status_code}")
        print(f"   Response: {resp.text[:500]}")
    except Exception as e:
        print(f"   Error: {e}")


if __name__ == "__main__":
    test_with_openai()
    test_with_httpx()
