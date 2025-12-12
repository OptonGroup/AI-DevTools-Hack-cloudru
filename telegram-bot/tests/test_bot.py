"""Unit tests for Telegram bot"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.services.agent_connector import AgentConnector
from src.utils.session import SessionStore


class TestAgentConnector:
    """Tests for AgentConnector"""

    def test_init_adds_trailing_slash(self):
        """Test that URL gets trailing slash"""
        connector = AgentConnector("https://example.com")
        assert connector.agent_url == "https://example.com/"

    def test_init_keeps_trailing_slash(self):
        """Test that existing trailing slash is kept"""
        connector = AgentConnector("https://example.com/")
        assert connector.agent_url == "https://example.com/"

    @pytest.mark.asyncio
    async def test_create_payload(self):
        """Test payload creation"""
        connector = AgentConnector("https://example.com")
        payload = connector._create_payload("Hello")

        assert payload["jsonrpc"] == "2.0"
        assert payload["method"] == "message/send"
        assert payload["params"]["message"]["parts"][0]["text"] == "Hello"
        assert payload["params"]["message"]["role"] == "user"

    def test_is_retryable_error_task_failed(self):
        """Test detection of retryable task failure"""
        connector = AgentConnector("https://example.com")

        response = '{"kind": "task", "status": {"state": "failed"}}'
        assert connector._is_retryable_error(response) is True

    def test_is_retryable_error_success(self):
        """Test that success response is not retryable"""
        connector = AgentConnector("https://example.com")

        response = '{"kind": "task", "status": {"state": "completed"}}'
        assert connector._is_retryable_error(response) is False

    def test_clean_response_text_truncates_long_text(self):
        """Test that long text is truncated"""
        connector = AgentConnector("https://example.com")

        long_text = "a" * 5000
        result = connector._clean_response_text(long_text)

        assert len(result) < 4100
        assert "[Сообщение сокращено]" in result


class TestSessionStore:
    """Tests for SessionStore"""

    def test_singleton(self):
        """Test that SessionStore is singleton"""
        store1 = SessionStore()
        store2 = SessionStore()
        assert store1 is store2

    def test_connect_and_get_agent(self):
        """Test connecting and getting agent"""
        store = SessionStore()
        store.connect_agent(123, "https://example.com")

        agent = store.get_agent(123)
        assert agent is not None
        assert isinstance(agent, AgentConnector)

        # Cleanup
        store.disconnect_agent(123)

    def test_disconnect_agent(self):
        """Test disconnecting agent"""
        store = SessionStore()
        store.connect_agent(456, "https://example.com")
        store.disconnect_agent(456)

        agent = store.get_agent(456)
        assert agent is None

    def test_is_connected(self):
        """Test is_connected method"""
        store = SessionStore()
        store.connect_agent(789, "https://example.com")

        assert store.is_connected(789) is True
        assert store.is_connected(999) is False

        # Cleanup
        store.disconnect_agent(789)
