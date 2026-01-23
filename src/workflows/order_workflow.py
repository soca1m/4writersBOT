"""
LangGraph workflow for order processing
New architecture: 7 bots with clean transitions

Flow:
Bot 1 (Requirements) → Bot 2 (Writer:initial) → Bot 3 (Citations) →
Bot 4 (Word Count) ↔ Bot 2 (expand) →
Bot 5 (Quality) ↔ Bot 2 (revise) + Bot 3 (if reinsert) →
Bot 6 (AI Check, max 5) → Bot 7 (References) → END
"""
import logging
from langgraph.graph import StateGraph, END

from src.workflows.state import OrderWorkflowState
from src.agents.requirements_analyzer import analyze_requirements_node
from src.agents.writer import write_text_node
from src.agents.citation_integrator import integrate_citations_node
from src.agents.word_count_checker import check_word_count_node
from src.agents.quality_checker import check_quality_node
from src.agents.ai_detector import check_ai_detection_node
from src.agents.references_generator import generate_references_node

logger = logging.getLogger(__name__)


def create_order_workflow():
    """
    Creates LangGraph workflow for order processing

    Returns:
        Compiled graph
    """
    workflow = StateGraph(OrderWorkflowState)

    # Add nodes (bots)
    workflow.add_node("analyze_requirements", analyze_requirements_node)  # Bot 1
    workflow.add_node("write", write_text_node)                           # Bot 2
    workflow.add_node("integrate_citations", integrate_citations_node)    # Bot 3
    workflow.add_node("check_word_count", check_word_count_node)          # Bot 4
    workflow.add_node("check_quality", check_quality_node)                # Bot 5
    workflow.add_node("check_ai", check_ai_detection_node)                # Bot 6
    workflow.add_node("generate_references", generate_references_node)    # Bot 7

    # Set entry point
    workflow.set_entry_point("analyze_requirements")

    # === Transitions ===

    # After Bot 1 (Requirements)
    def after_requirements(state: OrderWorkflowState) -> str:
        if state["status"] == "requirements_extracted":
            logger.info("Requirements extracted, starting writing")
            return "write"
        elif state["status"] == "insufficient_info":
            logger.warning("Insufficient info, ending workflow")
            return END
        else:
            logger.error(f"Requirements failed: {state.get('error')}")
            return END

    workflow.add_conditional_edges("analyze_requirements", after_requirements)

    # After Bot 2 (Writer)
    def after_write(state: OrderWorkflowState) -> str:
        mode = state.get("writer_mode", "initial")

        if state["status"] == "text_written":
            if mode == "initial":
                # First write → go to citations
                logger.info("Initial text written, adding citations")
                return "integrate_citations"
            elif mode == "expand":
                # Expanded text → back to citations (they might need reinsertion)
                logger.info("Text expanded, re-adding citations")
                return "integrate_citations"
            else:
                logger.warning(f"Unknown write mode: {mode}")
                return "integrate_citations"

        elif state["status"] == "text_revised":
            # After revision from quality check
            citation_action = state.get("citation_action", "keep")
            if citation_action == "reinsert":
                logger.info("Text revised, reinserting citations")
                return "integrate_citations"
            else:
                # Citations kept/adjusted, go back to quality check to verify fixes
                logger.info("Text revised, re-checking quality")
                return "check_quality"

        elif state["status"] == "failed":
            logger.error("Writing failed")
            return END

        else:
            logger.warning(f"Unknown status after write: {state['status']}")
            return END

    workflow.add_conditional_edges("write", after_write)

    # After Bot 3 (Citations)
    def after_citations(state: OrderWorkflowState) -> str:
        if state["status"] == "citations_added":
            logger.info("Citations added, checking word count")
            return "check_word_count"
        else:
            logger.warning(f"Citation status: {state['status']}, checking word count anyway")
            return "check_word_count"

    workflow.add_conditional_edges("integrate_citations", after_citations)

    # After Bot 4 (Word Count)
    def after_word_count(state: OrderWorkflowState) -> str:
        if state["status"] == "word_count_ok":
            logger.info("Word count OK, checking quality")
            return "check_quality"
        elif state["status"] == "word_count_expanding":
            logger.info("Word count low, expanding text")
            return "write"  # Goes to Bot 2 in expand mode
        else:
            logger.warning(f"Word count status: {state['status']}, checking quality")
            return "check_quality"

    workflow.add_conditional_edges("check_word_count", after_word_count)

    # After Bot 5 (Quality)
    def after_quality(state: OrderWorkflowState) -> str:
        if state["status"] == "quality_ok":
            logger.info("Quality OK, checking AI")
            return "check_ai"
        elif state["status"] == "quality_revising":
            logger.info("Quality issues, revising text")
            return "write"  # Goes to Bot 2 in revise mode
        else:
            logger.warning(f"Quality status: {state['status']}, checking AI anyway")
            return "check_ai"

    workflow.add_conditional_edges("check_quality", after_quality)

    # After Bot 6 (AI Detection)
    def after_ai_check(state: OrderWorkflowState) -> str:
        if state["status"] == "ai_passed":
            logger.info("AI check passed, generating references")
            return "generate_references"
        elif state["status"] == "ai_humanizing":
            logger.info("AI detected, rechecking after humanization")
            return "check_ai"  # Loop back to check again
        else:
            logger.warning(f"AI check status: {state['status']}, generating references anyway")
            return "generate_references"

    workflow.add_conditional_edges("check_ai", after_ai_check)

    # After Bot 7 (References) → END
    workflow.add_edge("generate_references", END)

    # Compile
    app = workflow.compile()
    logger.info("✅ Order workflow compiled successfully")

    return app


async def process_order(order_data: dict) -> OrderWorkflowState:
    """
    Process order through workflow

    Args:
        order_data: Order data dict

    Returns:
        Final state
    """
    logger.info(f"🚀 Starting workflow for order {order_data.get('order_id', 'unknown')}")

    app = create_order_workflow()

    # Calculate target word count
    pages = order_data.get('pages', 1)
    target_word_count = pages * 300

    # Create initial state
    initial_state = OrderWorkflowState(
        # Order data
        order_id=order_data.get('order_id', 'unknown'),
        order_index=order_data.get('order_index', ''),
        order_description=order_data.get('description', ''),
        pages_required=pages,
        deadline=order_data.get('deadline', ''),
        attached_files=order_data.get('files', []),

        # Bot 1
        requirements={},
        parsed_files_content="",

        # Bot 2
        writer_mode="initial",
        draft_text="",
        text_with_citations="",

        # Bot 3
        sources_found=[],
        citations_inserted=False,

        # Bot 4
        word_count=0,
        target_word_count=target_word_count,
        word_count_ok=False,
        word_count_attempts=0,

        # Bot 5
        quality_ok=False,
        quality_issues=[],
        quality_suggestions=[],
        citation_action="keep",
        quality_check_attempts=0,

        # Bot 6
        ai_score=0.0,
        ai_sentences=[],
        ai_check_attempts=0,
        ai_check_passed=False,

        # Bot 7
        references="",

        # Final
        final_text="",
        status="started",
        agent_logs=[],
        error=None
    )

    try:
        final_state = await app.ainvoke(initial_state)

        logger.info(f"✅ Workflow completed for order {order_data.get('order_id')}")
        logger.info(f"Final status: {final_state['status']}")

        return final_state

    except Exception as e:
        logger.error(f"❌ Workflow failed: {e}")
        logger.exception(e)
        return {
            **initial_state,
            "status": "failed",
            "error": str(e)
        }
