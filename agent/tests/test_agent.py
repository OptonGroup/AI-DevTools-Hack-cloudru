"""Тесты для Meeting Assistant Agent."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock


class TestPrompts:
    """Тесты для промптов."""
    
    def test_system_prompt_exists(self):
        """Проверка что системный промпт существует."""
        from src.prompts import SYSTEM_PROMPT
        
        assert SYSTEM_PROMPT is not None
        assert len(SYSTEM_PROMPT) > 100
        assert "созвон" in SYSTEM_PROMPT.lower() or "meeting" in SYSTEM_PROMPT.lower()
    
    def test_system_prompt_contains_capabilities(self):
        """Проверка что промпт содержит описание возможностей."""
        from src.prompts import SYSTEM_PROMPT
        
        assert "join_conference" in SYSTEM_PROMPT
        assert "get_transcription" in SYSTEM_PROMPT
        assert "create_meeting" in SYSTEM_PROMPT
        assert "search_knowledge_base" in SYSTEM_PROMPT


class TestMCPToolClient:
    """Тесты для MCPToolClient."""
    
    def test_init(self):
        """Тест инициализации клиента."""
        from src.agent import MCPToolClient
        
        client = MCPToolClient("http://localhost:8000/mcp")
        assert client.mcp_url == "http://localhost:8000/mcp"
        assert client.timeout == 30.0
    
    def test_init_strips_trailing_slash(self):
        """Тест что trailing slash удаляется."""
        from src.agent import MCPToolClient
        
        client = MCPToolClient("http://localhost:8000/mcp/")
        assert client.mcp_url == "http://localhost:8000/mcp"


class TestToolCreation:
    """Тесты для создания инструментов."""
    
    def test_create_followup_tools(self):
        """Тест создания Follow-Up инструментов."""
        from src.agent import create_followup_tools
        
        tools = create_followup_tools("http://localhost:8000/mcp")
        
        assert len(tools) == 4
        tool_names = [t.name for t in tools]
        assert "join_conference" in tool_names
        assert "get_transcription" in tool_names
        assert "list_conferences" in tool_names
        assert "get_conference_info" in tool_names
    
    def test_create_calendar_tools(self):
        """Тест создания Calendar инструментов."""
        from src.agent import create_calendar_tools
        
        tools = create_calendar_tools("http://localhost:8001/mcp")
        
        assert len(tools) == 3
        tool_names = [t.name for t in tools]
        assert "create_meeting" in tool_names
        assert "list_meetings" in tool_names
        assert "get_meeting_info" in tool_names
    
    def test_create_rag_tools(self):
        """Тест создания RAG инструментов."""
        from src.agent import create_rag_tools
        
        tools = create_rag_tools("http://localhost:8002/mcp")
        
        assert len(tools) == 2
        tool_names = [t.name for t in tools]
        assert "search_knowledge_base" in tool_names
        assert "add_to_knowledge_base" in tool_names


class TestAgentCreation:
    """Тесты для создания агента."""
    
    def test_create_agent_without_mcp(self):
        """Тест создания агента без MCP серверов."""
        import os
        from dotenv import load_dotenv
        load_dotenv()
        
        from src.agent import create_meeting_assistant_agent
        
        agent = create_meeting_assistant_agent()
        assert agent is not None
    
    def test_create_agent_with_followup_mcp(self):
        """Тест создания агента с Follow-Up MCP."""
        import os
        from dotenv import load_dotenv
        load_dotenv()
        
        from src.agent import create_meeting_assistant_agent
        
        agent = create_meeting_assistant_agent(
            followup_mcp_url="http://localhost:8000/mcp"
        )
        assert agent is not None
        assert len(agent.tools) == 4  # 4 Follow-Up tools
    
    def test_create_agent_with_all_mcp(self):
        """Тест создания агента со всеми MCP серверами."""
        import os
        from dotenv import load_dotenv
        load_dotenv()
        
        from src.agent import create_meeting_assistant_agent
        
        agent = create_meeting_assistant_agent(
            followup_mcp_url="http://localhost:8000/mcp",
            gcalendar_mcp_url="http://localhost:8001/mcp",
            rag_mcp_url="http://localhost:8002/mcp"
        )
        assert agent is not None
        assert len(agent.tools) == 9  # 4 Follow-Up + 3 Calendar + 2 RAG


class TestA2AWrapper:
    """Тесты для A2A обёртки."""
    
    def test_session_history_creation(self):
        """Тест создания истории сессии."""
        from src.a2a_wrapper import MeetingAssistantA2AWrapper
        
        # Создаём mock агента
        mock_agent = MagicMock()
        wrapper = MeetingAssistantA2AWrapper(mock_agent)
        
        history = wrapper._get_session_history("session-1")
        assert history == []
        
        # Повторный вызов возвращает тот же список
        history.append(("human", "test"))
        history2 = wrapper._get_session_history("session-1")
        assert len(history2) == 1
    
    def test_supported_content_types(self):
        """Тест поддерживаемых типов контента."""
        from src.a2a_wrapper import MeetingAssistantA2AWrapper
        
        assert "text" in MeetingAssistantA2AWrapper.SUPPORTED_CONTENT_TYPES
        assert "text/plain" in MeetingAssistantA2AWrapper.SUPPORTED_CONTENT_TYPES







