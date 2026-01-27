"""
LangGraph workflow for order processing
New architecture with AI detection and humanization

Flow:
Bot 1 (Requirements) → Bot 2 (Writer:initial) → Bot 3 (Citations) →
Bot 4 (Word Count) ↔ Bot 2 (expand/shorten) →
Bot 5 (Quality Pre-AI) ↔ Bot 2 (revise) + Bot 3 (if reinsert) →
Bot 6 (AI Check) →
  ├─ If ≤5% AI → Check if post-humanization →
  │   ├─ Yes → Bot 5b (Quality Post-Humanization) → Bot 7 (References)
  │   └─ No → Bot 7 (References)
  └─ If >5% AI → Humanizer →
      ├─ If >70% AI → Full Rehumanize → Bot 6 (recheck)
      └─ If 5-70% AI → Sentence Humanize → Bot 6 (recheck)

After Bot 5b (Quality Post-Humanization):
  ├─ If OK → Bot 7 (References) → END
  └─ If Critical Errors → Bot 2 (fix_humanized) → Bot 6 (final check)
"""
import logging
from typing import Optional
from langgraph.graph import StateGraph, END

from src.workflows.state import OrderWorkflowState
from src.checkpoint_manager import get_checkpointer
from src.agents.requirements_analyzer import analyze_requirements_node
from src.agents.writer import write_text_node
from src.agents.citation_integrator import integrate_citations_node
from src.agents.word_count_checker import check_word_count_node
from src.agents.quality_checker import check_quality_node
from src.agents.quality_checker_post_humanization import check_quality_post_humanization_node
from src.agents.ai_detector import check_ai_detection_node
from src.agents.humanizer import humanize_text_node
from src.agents.references_generator import generate_references_node

logger = logging.getLogger(__name__)


def create_order_workflow(checkpointer=None):
    """
    Creates LangGraph workflow for order processing

    Args:
        checkpointer: Optional checkpointer for state persistence

    Returns:
        Compiled graph
    """
    workflow = StateGraph(OrderWorkflowState)

    # Add nodes (bots)
    workflow.add_node("analyze_requirements", analyze_requirements_node)          # Bot 1
    workflow.add_node("write", write_text_node)                                   # Bot 2
    workflow.add_node("integrate_citations", integrate_citations_node)            # Bot 3
    workflow.add_node("check_word_count", check_word_count_node)                  # Bot 4
    workflow.add_node("check_quality", check_quality_node)                        # Bot 5 (Pre-AI)
    workflow.add_node("check_quality_post_humanization", check_quality_post_humanization_node)  # Bot 5b (Post-Humanization)
    workflow.add_node("check_ai", check_ai_detection_node)                        # Bot 6
    workflow.add_node("humanize", humanize_text_node)                             # Humanizer
    workflow.add_node("generate_references", generate_references_node)            # Bot 7

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
            # Check if this was shorten_humanized mode
            if mode == "shorten_humanized":
                # Citations already in text after humanization, go back to word count check
                logger.info("Humanized text shortened, checking word count again")
                return "check_word_count"

            # After initial, expand, or shorten mode
            logger.info(f"Text written (mode: {mode}), adding citations")
            return "integrate_citations"

        elif state["status"] == "text_revised":
            # Check if this was a post-humanization fix
            post_humanization = state.get("post_humanization_check", False)

            if mode == "fix_humanized" and post_humanization:
                # After fixing humanized text, go back to AI check to verify
                logger.info("Humanized text fixed, checking AI again")
                return "check_ai"

            # Regular revision from quality check
            citation_action = state.get("citation_action", "keep")
            if citation_action == "reinsert":
                logger.info("Text revised, reinserting citations")
                return "integrate_citations"
            else:
                # Citations kept/adjusted, go back to quality check to verify fixes
                logger.info("Text revised, re-checking quality")
                return "check_quality"

        elif state["status"] == "word_count_shortening":
            # After shorten mode - check if we need to reinsert citations
            citations_already_inserted = state.get("citations_inserted", False)
            citation_action = state.get("citation_action", "keep")

            if citations_already_inserted and citation_action != "reinsert":
                # Citations already in text and we're just adjusting/keeping them
                # Skip Bot 3 to avoid re-inserting in same places
                logger.info("Text shortened, citations already in text, checking quality")
                return "check_quality"
            else:
                # Need to insert citations for first time
                logger.info("Text shortened, inserting citations")
                return "integrate_citations"

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
        post_humanization = state.get("post_humanization_check", False)

        if state["status"] == "word_count_ok":
            # Check if this is after humanization
            if post_humanization:
                logger.info("Word count OK after humanization, generating references")
                return "generate_references"
            else:
                logger.info("Word count OK, checking quality")
                return "check_quality"

        elif state["status"] == "word_count_expanding":
            logger.info("Word count low, expanding text")
            return "write"  # Goes to Bot 2 in expand mode

        elif state["status"] == "word_count_shortening":
            # Check if this is after humanization
            if post_humanization:
                logger.info("Word count too high after humanization, shortening while preserving human style")
                return "write"  # Goes to Bot 2 in shorten_humanized mode
            else:
                logger.info("Word count too high, shortening text")
                return "write"  # Goes to Bot 2 in shorten mode
        else:
            logger.warning(f"Word count status: {state['status']}, checking quality")
            return "check_quality"

    workflow.add_conditional_edges("check_word_count", after_word_count)

    # After Bot 5 (Quality)
    def after_quality(state: OrderWorkflowState) -> str:
        if state["status"] == "quality_ok":
            logger.info("Quality OK, checking AI detection")
            return "check_ai"  # Go to AI check
        elif state["status"] == "quality_revising":
            logger.info("Quality issues, revising text")
            return "write"  # Goes to Bot 2 in revise mode
        else:
            logger.warning(f"Quality status: {state['status']}, checking AI anyway")
            return "check_ai"

    workflow.add_conditional_edges("check_quality", after_quality)

    # After Bot 6 (AI Detection)
    def after_ai_check(state: OrderWorkflowState) -> str:
        status = state.get("status")
        post_humanization = state.get("post_humanization_check", False)

        # TEMPORARY: Skip humanization for testing
        logger.info("⚠️ HUMANIZATION DISABLED FOR TESTING - going directly to references")
        return "generate_references"

        # Original logic (commented out for testing):
        # if status == "ai_passed":
        #     # AI check passed - determine next step
        #     if post_humanization:
        #         # This was after humanization - skip to references
        #         logger.info("AI check passed after humanization, generating references")
        #         return "generate_references"
        #     else:
        #         # First time passing - go to references directly
        #         logger.info("AI check passed, generating references")
        #         return "generate_references"

        # elif status == "ai_passed_post_humanization":
        #     # AI passed and this was a post-humanization check
        #     # Go to post-humanization quality check
        #     logger.info("AI passed after humanization, checking post-humanization quality")
        #     return "check_quality_post_humanization"

        # elif status == "ai_humanizing":
        #     logger.info("AI detected, sending to humanizer")
        #     return "humanize"  # Go to humanizer

        # else:
        #     logger.warning(f"AI check status: {status}, generating references anyway")
        #     return "generate_references"

    workflow.add_conditional_edges("check_ai", after_ai_check)

    # After Humanizer → back to AI check
    def after_humanize(state: OrderWorkflowState) -> str:
        logger.info("Text humanized, rechecking with AI detector")
        # Set flag that next AI check is post-humanization
        return "check_ai"  # Always go back to AI check

    workflow.add_conditional_edges("humanize", after_humanize)

    # After Bot 5b (Post-Humanization Quality Check)
    def after_quality_post_humanization(state: OrderWorkflowState) -> str:
        if state.get("quality_ok"):
            logger.info("Post-humanization quality OK, checking word count")
            return "check_word_count"  # Check word count after humanization
        elif state.get("status") == "quality_revising":
            # Critical errors found - need manual fixes
            logger.info("Post-humanization quality issues, fixing with style preservation")
            return "write"  # Go to writer in fix_humanized mode
        else:
            logger.warning("Unknown post-humanization quality status, checking word count")
            return "check_word_count"

    workflow.add_conditional_edges("check_quality_post_humanization", after_quality_post_humanization)

    # After Bot 7 (References) → END
    workflow.add_edge("generate_references", END)

    # Compile with optional checkpointer
    if checkpointer:
        app = workflow.compile(checkpointer=checkpointer)
        logger.info("✅ Order workflow compiled successfully with checkpointing")
    else:
        app = workflow.compile()
        logger.info("✅ Order workflow compiled successfully")

    return app


async def process_order(order_data: dict, resume: bool = False, chat_id: Optional[int] = None) -> OrderWorkflowState:
    """
    Process order through workflow with checkpointing support

    Args:
        order_data: Order data dict
        resume: If True, try to resume from last checkpoint
        chat_id: Optional Telegram chat ID for database logging

    Returns:
        Final state
    """
    from src.db.database import create_workflow, update_workflow_status, add_workflow_stage

    order_id = order_data.get('order_id', 'unknown')
    logger.info(f"🚀 Starting workflow for order {order_id} (resume={resume})")

    # Create workflow record in database
    workflow_id = None
    if chat_id:
        workflow_id = create_workflow(
            chat_id=chat_id,
            order_id=order_id,
            order_index=order_data.get('order_index')
        )
        logger.info(f"Created workflow record #{workflow_id} in database")

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
        humanization_mode="none",
        humanized_document_id=None,
        post_humanization_check=False,

        # Bot 7
        references="",

        # Final
        final_text="",
        status="started",
        agent_logs=[],
        error=None
    )

    # Get global checkpointer
    checkpointer = get_checkpointer()

    app = create_order_workflow(checkpointer=checkpointer)

    # Use order_id as thread_id for checkpointing
    config = {
        "configurable": {"thread_id": str(order_id)},
        "recursion_limit": 200  # Increased to allow more quality iterations
    }

    try:
        # Update status to running
        if workflow_id:
            update_workflow_status(workflow_id, "running")

        if resume:
            # Try to resume from checkpoint
            logger.info(f"Attempting to resume from checkpoint for order {order_id}")
            # Get the current state from checkpoint
            state = await app.aget_state(config)
            if state.values:
                logger.info(f"Found checkpoint, resuming from: {state.next}")
                # Continue from last checkpoint
                final_state = await app.ainvoke(None, config=config)
            else:
                logger.info("No checkpoint found, starting fresh")
                final_state = await app.ainvoke(initial_state, config=config)
        else:
            # Start fresh
            final_state = await app.ainvoke(initial_state, config=config)

        logger.info(f"✅ Workflow completed for order {order_id}")
        logger.info(f"Final status: {final_state['status']}")

        # Update workflow in database
        if workflow_id:
            update_workflow_status(
                workflow_id,
                "completed",
                final_text=final_state.get('final_text', ''),
                word_count=final_state.get('word_count', 0),
                ai_score=final_state.get('ai_score', 0.0)
            )

            # Log final stage
            add_workflow_stage(
                workflow_id=workflow_id,
                stage_name="completed",
                status="completed",
                output_data={
                    "word_count": final_state.get('word_count', 0),
                    "ai_score": final_state.get('ai_score', 0.0),
                    "final_status": final_state.get('status')
                },
                agent_logs=final_state.get('agent_logs', [])
            )

        return final_state

    except Exception as e:
        logger.error(f"❌ Workflow failed: {e}")
        logger.exception(e)
        logger.info(f"💾 State saved at checkpoint - can resume with resume=True")

        # Update workflow status to failed
        if workflow_id:
            update_workflow_status(workflow_id, "failed", error=str(e))

            # Log failed stage
            add_workflow_stage(
                workflow_id=workflow_id,
                stage_name="failed",
                status="failed",
                error=str(e)
            )

        return {
            **initial_state,
            "status": "failed",
            "error": str(e)
        }
