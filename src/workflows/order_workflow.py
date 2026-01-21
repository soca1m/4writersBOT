"""
LangGraph workflow для обработки заказов
"""
import logging
from langgraph.graph import StateGraph, END
from src.workflows.state import OrderWorkflowState
from src.agents.analyzer import analyze_order_node
from src.agents.requirements_extractor import extract_requirements_node
from src.agents.writer import write_text_node
from src.agents.word_count_checker import check_word_count_node
from src.agents.ai_detector import check_ai_detection_node
from src.agents.rewriter import rewrite_text_node

logger = logging.getLogger(__name__)


def create_order_workflow():
    """
    Создает LangGraph workflow для обработки заказов

    Returns:
        Скомпилированный граф
    """
    # Создаем граф
    workflow = StateGraph(OrderWorkflowState)

    # Добавляем узлы (агенты)
    workflow.add_node("analyze", analyze_order_node)
    workflow.add_node("extract_requirements", extract_requirements_node)
    workflow.add_node("write", write_text_node)
    workflow.add_node("check_word_count", check_word_count_node)
    workflow.add_node("check_ai_detection", check_ai_detection_node)
    workflow.add_node("rewrite", rewrite_text_node)

    # Устанавливаем точку входа
    workflow.set_entry_point("analyze")

    # Условное ребро после анализа
    def should_continue_after_analysis(state: OrderWorkflowState) -> str:
        """Решает продолжать ли после анализа"""
        if state["status"] == "rejected":
            logger.info(f"Order {state['order_id']} rejected, ending workflow")
            return END
        elif state["status"] == "accepted":
            logger.info(f"Order {state['order_id']} accepted, extracting requirements")
            return "extract_requirements"
        else:
            logger.warning(f"Unknown status: {state['status']}, ending workflow")
            return END

    workflow.add_conditional_edges(
        "analyze",
        should_continue_after_analysis
    )

    # Условное ребро после extract_requirements
    def should_continue_after_requirements(state: OrderWorkflowState) -> str:
        """Решает продолжать ли после извлечения требований"""
        if state["status"] == "insufficient_info":
            logger.warning(f"Order {state['order_id']} has insufficient information, ending workflow")
            return END
        elif state["status"] == "requirements_extracted":
            logger.info(f"Order {state['order_id']} requirements extracted, starting writing")
            return "write"
        elif state["status"] == "failed":
            logger.error(f"Order {state['order_id']} failed during requirements extraction")
            return END
        else:
            logger.warning(f"Unknown status after requirements: {state['status']}, ending workflow")
            return END

    workflow.add_conditional_edges(
        "extract_requirements",
        should_continue_after_requirements
    )

    # Условное ребро после write
    def should_continue_after_write(state: OrderWorkflowState) -> str:
        """Решает продолжать ли после написания"""
        if state["status"] == "text_generated":
            logger.info(f"Order {state['order_id']} text generated, checking word count")
            return "check_word_count"
        elif state["status"] == "writing_failed":
            logger.error(f"Order {state['order_id']} writing failed")
            return END
        else:
            logger.warning(f"Unknown status after write: {state['status']}, ending workflow")
            return END

    workflow.add_conditional_edges(
        "write",
        should_continue_after_write
    )

    # Условное ребро после check_word_count (с циклом обратно к write)
    def should_continue_after_word_count(state: OrderWorkflowState) -> str:
        """Решает продолжать ли после проверки слов"""
        if state["status"] == "insufficient_words":
            logger.warning(f"Order {state['order_id']} needs more words, expanding text")
            return "write"  # Возвращаемся к write для дополнения
        elif state["status"] == "too_many_words":
            logger.warning(f"Order {state['order_id']} has too many words, proceeding to AI check")
            return "check_ai_detection"
        elif state["status"] == "word_count_ok":
            logger.info(f"Order {state['order_id']} word count is acceptable, checking AI detection")
            return "check_ai_detection"
        elif state["status"] == "word_count_failed":
            logger.error(f"Order {state['order_id']} word count check failed")
            return END
        else:
            logger.warning(f"Unknown status after word count: {state['status']}, ending workflow")
            return END

    workflow.add_conditional_edges(
        "check_word_count",
        should_continue_after_word_count
    )

    # Условное ребро после check_ai_detection
    def should_continue_after_ai_check(state: OrderWorkflowState) -> str:
        """Решает продолжать ли после проверки AI"""
        if state["status"] == "ai_check_passed":
            logger.info(f"Order {state['order_id']} passed AI detection, workflow complete")
            return END
        elif state["status"] == "ai_detected":
            logger.warning(f"Order {state['order_id']} detected as AI, rewriting")
            return "rewrite"
        elif state["status"] == "ai_check_failed":
            logger.error(f"Order {state['order_id']} AI check failed")
            return END
        else:
            logger.warning(f"Unknown status after AI check: {state['status']}, ending workflow")
            return END

    workflow.add_conditional_edges(
        "check_ai_detection",
        should_continue_after_ai_check
    )

    # Условное ребро после rewrite (возвращаемся на проверку AI)
    def should_continue_after_rewrite(state: OrderWorkflowState) -> str:
        """Решает продолжать ли после переписывания"""
        if state["status"] == "text_rewritten":
            logger.info(f"Order {state['order_id']} text rewritten, checking AI again")
            return "check_ai_detection"
        elif state["status"] == "rewrite_failed":
            logger.error(f"Order {state['order_id']} rewrite failed")
            return END
        else:
            logger.warning(f"Unknown status after rewrite: {state['status']}, ending workflow")
            return END

    workflow.add_conditional_edges(
        "rewrite",
        should_continue_after_rewrite
    )

    # Компилируем граф
    app = workflow.compile()

    logger.info("✅ Order workflow compiled successfully")
    return app


async def process_order(order_data: dict) -> OrderWorkflowState:
    """
    Обрабатывает заказ через workflow

    Args:
        order_data: Данные заказа

    Returns:
        Финальное состояние
    """
    logger.info(f"🚀 Starting workflow for order {order_data.get('order_id', 'unknown')}")

    # Создаем workflow
    app = create_order_workflow()

    # Создаем начальное состояние
    initial_state = OrderWorkflowState(
        order_id=order_data.get('order_id', 'unknown'),
        order_index=order_data.get('order_index', ''),
        order_description=order_data.get('description', ''),
        pages_required=order_data.get('pages', 0),
        deadline=order_data.get('deadline', ''),
        attached_files=order_data.get('files', []),
        requirements={},
        parsed_files_content="",
        sources_found=[],
        quotes=[],
        draft_text="",
        word_count=0,
        meets_requirements=False,
        quality_issues=[],
        plagiarism_score=100.0,
        plagiarism_details={},
        rewrite_attempts=0,
        final_text="",
        references="",
        status="analyzing",
        agent_logs=[],
        error=None
    )

    # Запускаем workflow
    try:
        final_state = await app.ainvoke(initial_state)

        logger.info(f"✅ Workflow completed for order {order_data.get('order_id')}")
        logger.info(f"Final status: {final_state['status']}")

        return final_state

    except Exception as e:
        logger.error(f"❌ Workflow failed for order {order_data.get('order_id')}: {e}")
        return {
            **initial_state,
            "status": "failed",
            "error": str(e)
        }
