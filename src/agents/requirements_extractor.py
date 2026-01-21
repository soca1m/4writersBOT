"""
Requirements Extractor Agent - извлекает детальные требования из описания и файлов
"""
import logging
from src.workflows.state import OrderWorkflowState
from src.utils.llm_service import get_smart_model
from src.utils.file_parser import parse_multiple_files
from src.utils.prompt_loader import get_requirements_extractor_prompt

logger = logging.getLogger(__name__)


async def extract_requirements_node(state: OrderWorkflowState) -> dict:
    """
    Извлекает детальные требования из описания заказа и прикрепленных файлов
    Анализирует и объясняет что нужно сделать

    Args:
        state: Текущее состояние workflow

    Returns:
        Обновленное состояние с requirements
    """
    logger.info(f"🔍 Extracting requirements from order {state['order_id']}...")

    # Парсим прикрепленные файлы
    files_content = ""
    if state['attached_files']:
        logger.info(f"Parsing {len(state['attached_files'])} attached files...")
        files_content = parse_multiple_files(state['attached_files'])
        logger.info(f"Extracted {len(files_content)} characters from files")

    try:
        llm = get_smart_model()

        if not llm:
            logger.error("Smart LLM not available")
            return {
                **state,
                "status": "failed",
                "error": "LLM not available for requirements extraction",
                "agent_logs": ["[requirements_extractor] ERROR: LLM not available"]
            }

        # Загружаем промпт из файла
        extraction_prompt = get_requirements_extractor_prompt(
            order_description=state.get('order_description', 'Not specified'),
            pages_required=state['pages_required'],
            files_content=files_content
        )

        print("\n" + "="*80)
        print("🤔 LLM начинает анализ задания...")
        print("="*80)

        # Используем streaming для вывода процесса мышления в реальном времени
        full_response = ""
        async for chunk in llm.astream(extraction_prompt):
            content = chunk.content
            print(content, end='', flush=True)
            full_response += content

        print("\n" + "="*80)

        analysis_text = full_response.strip()

        logger.info("✅ Requirements analysis completed")
        print("\n" + "="*80)
        print("📋 ASSIGNMENT ANALYSIS:")
        print("="*80)
        print(analysis_text)
        print("="*80 + "\n")

        # Проверяем достаточно ли информации
        is_insufficient = "INSUFFICIENT INFORMATION" in analysis_text.upper()

        if is_insufficient:
            logger.warning("⚠️ Insufficient information to complete the order")
            return {
                **state,
                "requirements": {
                    "analysis": analysis_text,
                    "is_sufficient": False
                },
                "parsed_files_content": files_content,
                "status": "insufficient_info",
                "error": "Insufficient information to complete the assignment",
                "agent_logs": [f"[requirements_extractor] INSUFFICIENT INFO: Cannot proceed"]
            }

        # Сохраняем анализ в requirements как текст
        requirements = {
            "analysis": analysis_text,
            "pages": state['pages_required'],
            "files_content": files_content[:500] + "..." if len(files_content) > 500 else files_content,
            "is_sufficient": True
        }

        return {
            **state,
            "requirements": requirements,
            "parsed_files_content": files_content,
            "status": "requirements_extracted",
            "agent_logs": [f"[requirements_extractor] Analysis completed: {len(analysis_text)} characters"]
        }

    except Exception as e:
        logger.error(f"Error extracting requirements: {e}")
        logger.exception(e)
        return {
            **state,
            "status": "failed",
            "error": f"Requirements extraction failed: {str(e)}",
            "agent_logs": [f"[requirements_extractor] ERROR: {str(e)}"]
        }
