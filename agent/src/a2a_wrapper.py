"""Обертка LangChain агента для A2A протокола."""
import asyncio
import logging
from typing import Dict, Any, AsyncGenerator

from langchain.agents import AgentExecutor

logger = logging.getLogger(__name__)


class MeetingAssistantA2AWrapper:
    """Обертка для преобразования LangChain агента в A2A-совместимый интерфейс."""
    
    def __init__(self, agent_executor: AgentExecutor):
        self.agent_executor = agent_executor
        self.sessions: Dict[str, list] = {}  # Хранение истории сессий
    
    def _get_session_history(self, session_id: str) -> list:
        """Получает историю сессии."""
        if session_id not in self.sessions:
            self.sessions[session_id] = []
        return self.sessions[session_id]
    
    async def invoke(self, query: str, session_id: str) -> Dict[str, Any]:
        """Выполняет запрос к агенту и возвращает результат."""
        try:
            chat_history = self._get_session_history(session_id)
            
            # Выполняем агента в отдельном потоке
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self.agent_executor.invoke({
                    "input": query,
                    "chat_history": chat_history
                })
            )
            
            # Обновляем историю
            chat_history.append(("human", query))
            chat_history.append(("assistant", result.get("output", "")))
            
            return {
                "is_task_complete": True,
                "require_user_input": False,
                "content": result.get("output", ""),
                "is_error": False,
                "is_event": False
            }
        except Exception as e:
            logger.error(f"Error in invoke: {e}", exc_info=True)
            return {
                "is_task_complete": True,
                "require_user_input": False,
                "content": f"Ошибка: {str(e)}",
                "is_error": True,
                "is_event": False
            }
    
    async def stream(self, query: str, session_id: str) -> AsyncGenerator[Dict[str, Any], None]:
        """Потоковое выполнение запроса к агенту."""
        try:
            chat_history = self._get_session_history(session_id)
            full_response = ""
            
            # LangChain AgentExecutor поддерживает astream
            async for chunk in self.agent_executor.astream({
                "input": query,
                "chat_history": chat_history
            }):
                # Извлекаем текст из чанков
                if "output" in chunk:
                    output = chunk["output"]
                    if output and output != full_response:
                        new_part = output[len(full_response):]
                        full_response = output
                        
                        yield {
                            "is_task_complete": False,
                            "require_user_input": False,
                            "content": new_part,
                            "is_error": False,
                            "is_event": False
                        }
                
                # Отправляем события о вызове инструментов
                if "intermediate_steps" in chunk:
                    for step in chunk["intermediate_steps"]:
                        if step:
                            tool_name = step[0].tool if hasattr(step[0], 'tool') else "tool"
                            yield {
                                "is_task_complete": False,
                                "require_user_input": False,
                                "content": f"🔧 Использую инструмент: {tool_name}\n",
                                "is_error": False,
                                "is_event": True
                            }
            
            # Обновляем историю
            chat_history.append(("human", query))
            chat_history.append(("assistant", full_response))
            
            # Финальный чанк
            yield {
                "is_task_complete": True,
                "require_user_input": False,
                "content": "",
                "is_error": False,
                "is_event": False
            }
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error in stream: {e}", exc_info=True)
            
            # Более информативное сообщение для 404 ошибки
            if "404" in error_msg:
                error_msg = (
                    f"Ошибка 404: Модель или эндпоинт не найден.\n"
                    f"Проверьте:\n"
                    f"1. Правильность имени модели в LLM_MODEL\n"
                    f"2. Доступность модели в вашем проекте Cloud.ru\n"
                    f"3. Права API ключа\n\n"
                    f"Детали: {e}"
                )
            
            yield {
                "is_task_complete": True,
                "require_user_input": False,
                "content": error_msg,
                "is_error": True,
                "is_event": False
            }
    
    # Для совместимости с A2A
    SUPPORTED_CONTENT_TYPES = ["text", "text/plain"]







