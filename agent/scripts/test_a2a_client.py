"""
Test script for A2A client connection to Cloud.ru AI Agent.
"""
import asyncio
import httpx
from typing import Any
from uuid import uuid4

from a2a.client import A2ACardResolver, A2AClient
from a2a.types import (
    MessageSendParams,
    SendMessageRequest,
)


async def get_access_token() -> str:
    """Get access token from Cloud.ru IAM API"""
    url = "https://iam.api.cloud.ru/api/v1/auth/token"
    payload = {
        "keyId": "4461381aeb626292a774dc49a801636d",
        "secret": "56cc75128e021e92a00c8c24a0c69ddd"
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()
        return response.json()["access_token"]


async def main():
    timeout_config = httpx.Timeout(5 * 60.0)
    base_url = 'https://764bbda6-9ead-42cd-b38f-430fc9fc4ed3-agent.ai-agent.inference.cloud.ru'
    
    print("Getting access token...")
    access_token = await get_access_token()
    print(f"Token received: {access_token[:20]}...")
    
    async with httpx.AsyncClient(timeout=timeout_config) as httpx_client:
        httpx_client.headers['Authorization'] = f'Bearer {access_token}'
        
        print("Resolving agent card...")
        resolver = A2ACardResolver(
            httpx_client=httpx_client,
            base_url=base_url,
        )
        public_card = await resolver.get_agent_card()
        print(f"Agent card resolved successfully")
        
        client = A2AClient(
            httpx_client=httpx_client,
            agent_card=public_card,
        )
        
        send_message_payload: dict[str, Any] = {
            'message': {
                'role': 'user',
                'parts': [{'kind': 'text', 'text': 'на какой встрече мы разговаривали про компьютеры и шахматы'}],
                'messageId': uuid4().hex,
            },
        }
        
        print("Sending message...")
        request = SendMessageRequest(
            id=str(uuid4()), 
            params=MessageSendParams(**send_message_payload)
        )
        response = await client.send_message(request)
        
        print("\n=== Response ===")
        print(response.model_dump(mode='json', exclude_none=True))


if __name__ == "__main__":
    asyncio.run(main())
