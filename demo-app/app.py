"""
A2A Demo Inspector - Mini application for demonstrating A2A agent requests.
"""
import asyncio
import json
from datetime import datetime
from uuid import uuid4
from typing import Any

import httpx
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# Configuration
BASE_URL = 'https://764bbda6-9ead-42cd-b38f-430fc9fc4ed3-agent.ai-agent.inference.cloud.ru'
IAM_URL = "https://iam.api.cloud.ru/api/v1/auth/token"
IAM_CREDENTIALS = {
    "keyId": "4461381aeb626292a774dc49a801636d",
    "secret": "56cc75128e021e92a00c8c24a0c69ddd"
}


async def get_access_token() -> str:
    """Get access token from Cloud.ru IAM API"""
    async with httpx.AsyncClient() as client:
        response = await client.post(IAM_URL, json=IAM_CREDENTIALS)
        response.raise_for_status()
        return response.json()["access_token"]


async def get_agent_card(token: str) -> dict:
    """Get agent card from A2A endpoint"""
    timeout = httpx.Timeout(60.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        client.headers['Authorization'] = f'Bearer {token}'
        response = await client.get(f"{BASE_URL}/.well-known/agent.json")
        response.raise_for_status()
        return response.json()


async def send_a2a_message(token: str, message: str) -> dict:
    """Send message to A2A agent and get response"""
    timeout = httpx.Timeout(5 * 60.0)
    
    payload = {
        "jsonrpc": "2.0",
        "id": str(uuid4()),
        "method": "message/send",
        "params": {
            "message": {
                "role": "user",
                "parts": [{"kind": "text", "text": message}],
                "messageId": uuid4().hex,
            }
        }
    }
    
    async with httpx.AsyncClient(timeout=timeout) as client:
        client.headers['Authorization'] = f'Bearer {token}'
        client.headers['Content-Type'] = 'application/json'
        
        response = await client.post(BASE_URL, json=payload)
        response.raise_for_status()
        return {
            "request": payload,
            "response": response.json(),
            "timestamp": datetime.now().isoformat()
        }


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/agent-card', methods=['GET'])
def api_agent_card():
    try:
        token = asyncio.run(get_access_token())
        card = asyncio.run(get_agent_card(token))
        return jsonify({"success": True, "data": card})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/send', methods=['POST'])
def api_send():
    try:
        data = request.json
        message = data.get('message', '')
        
        if not message:
            return jsonify({"success": False, "error": "Message is required"}), 400
        
        token = asyncio.run(get_access_token())
        result = asyncio.run(send_a2a_message(token, message))
        
        return jsonify({"success": True, "data": result})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, port=5000)
