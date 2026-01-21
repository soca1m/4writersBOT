"""
Order Analyzer Agent - анализирует заказ и решает брать его или нет
"""
import logging
from src.workflows.state import OrderWorkflowState
from src.utils.llm_service import get_fast_model
from src.utils.prompt_loader import get_analyzer_prompt

logger = logging.getLogger(__name__)


async def analyze_order_node(state: OrderWorkflowState) -> dict:
    """
    Анализирует заказ и решает: брать или нет

    Criteria:
    - Не более 3 страниц
    - Реалистичный дедлайн
    - Академическое задание

    Args:
        state: Текущее состояние workflow

    Returns:
        Обновленное состояние
    """
    logger.info(f"📋 Analyzing order {state['order_id']}...")

    # Базовая проверка: количество страниц
    if state['pages_required'] > 3:
        logger.warning(f"❌ Order {state['order_id']} rejected: too many pages ({state['pages_required']})")
        return {
            **state,
            "status": "rejected",
            "error": f"Order requires {state['pages_required']} pages, maximum is 3",
            "agent_logs": [f"[analyzer] REJECTED: Too many pages ({state['pages_required']} > 3)"]
        }

    # Используем LLM для более глубокого анализа
    try:
        llm = get_fast_model()

        if not llm:
            logger.warning("LLM not available, accepting order by default")
            return {
                **state,
                "status": "accepted",
                "agent_logs": ["[analyzer] ACCEPTED by default (LLM not available)"]
            }

        # Загружаем промпт из файла
        analysis_prompt = get_analyzer_prompt(
            order_description=state['order_description'],
            pages_required=state['pages_required'],
            deadline=state['deadline']
        )

        response = await llm.ainvoke(analysis_prompt)
        decision_text = response.content.strip()

        if "REJECT" in decision_text.upper():
            logger.warning(f"❌ Order {state['order_id']} rejected by LLM: {decision_text}")
            return {
                **state,
                "status": "rejected",
                "error": f"Order rejected by analyzer: {decision_text}",
                "agent_logs": [f"[analyzer] {decision_text}"]
            }

        logger.info(f"✅ Order {state['order_id']} accepted")
        return {
            **state,
            "status": "accepted",
            "agent_logs": [f"[analyzer] ACCEPTED: Order meets criteria ({state['pages_required']} pages)"]
        }

    except Exception as e:
        logger.error(f"Error analyzing order {state['order_id']}: {e}")
        # В случае ошибки - принимаем заказ (можно изменить логику)
        return {
            **state,
            "status": "accepted",
            "error": f"Analysis error: {str(e)}",
            "agent_logs": [f"[analyzer] ACCEPTED by default (analysis error: {str(e)})"]
        }
