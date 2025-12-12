"""Точка входа Meeting Assistant агента через A2A протокол."""
import os
import logging

from dotenv import load_dotenv
load_dotenv(override=False)

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentSkill

from agent import create_meeting_assistant_agent
from a2a_wrapper import MeetingAssistantA2AWrapper
from agent_task_manager import MeetingAssistantAgentExecutor

logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
    format='%(asctime)s %(levelname)s %(name)s %(message)s',
)
logger = logging.getLogger(__name__)


def main():
    followup_mcp_url = os.getenv("FOLLOWUP_MCP_URL")
    gcalendar_mcp_url = os.getenv("GCALENDAR_MCP_URL")
    rag_mcp_url = os.getenv("MANAGED_RAG_MCP_URL")
    
    logger.info("🤖 MEETING ASSISTANT AGENT")
    logger.info(f"Follow-Up: {followup_mcp_url or 'не настроен'}")
    logger.info(f"Calendar: {gcalendar_mcp_url or 'не настроен'}")
    logger.info(f"RAG: {rag_mcp_url or 'не настроен'}")
    
    agent_executor = create_meeting_assistant_agent(
        followup_mcp_url=followup_mcp_url,
        gcalendar_mcp_url=gcalendar_mcp_url,
        rag_mcp_url=rag_mcp_url,
    )
    
    agent_wrapper = MeetingAssistantA2AWrapper(agent_executor)
    agent_executor_a2a = MeetingAssistantAgentExecutor(agent_wrapper)
    
    agent_card = AgentCard(
        name=os.getenv('AGENT_NAME', 'Meeting Assistant'),
        description=os.getenv('AGENT_DESCRIPTION', 'AI-ассистент для созвонов'),
        url=os.getenv('URL_AGENT'),
        version=os.getenv('AGENT_VERSION', '1.0.0'),
        default_input_modes=agent_wrapper.SUPPORTED_CONTENT_TYPES,
        default_output_modes=agent_wrapper.SUPPORTED_CONTENT_TYPES,
        capabilities=AgentCapabilities(streaming=True),
        skills=[
            AgentSkill(
                id="join_conference",
                name="Подключение к созвонам",
                description="Подключение бота для записи",
                tags=["meeting", "recording"],
                examples=["Подключись к созвону https://meet.google.com/xxx"],
            ),
            AgentSkill(
                id="transcription",
                name="Транскрипции",
                description="Получение транскрипций созвонов",
                tags=["transcription"],
                examples=["Покажи транскрипцию созвона"],
            ),
            AgentSkill(
                id="calendar",
                name="Календарь",
                description="Создание встреч",
                tags=["calendar", "meeting"],
                examples=["Создай встречу на завтра в 15:00"],
            ),
            AgentSkill(
                id="search",
                name="Поиск",
                description="Поиск по истории созвонов",
                tags=["search"],
                examples=["О чём говорили на прошлой встрече?"],
            ),
        ],
    )
    
    request_handler = DefaultRequestHandler(
        agent_executor=agent_executor_a2a,
        task_store=InMemoryTaskStore(),
    )
    
    server = A2AStarletteApplication(
        agent_card=agent_card,
        http_handler=request_handler
    )
    
    import uvicorn
    port = int(os.getenv("PORT", 10000))
    logger.info(f"🚀 Starting on port {port}")
    uvicorn.run(server.build(), host='0.0.0.0', port=port)


if __name__ == '__main__':
    main()
