"""
Writer Agent - генерирует академический текст
"""
import logging
from typing import Dict, Any

from src.workflows.state import OrderWorkflowState
from src.utils.llm_service import get_smart_model
from src.utils.prompt_loader import get_writer_prompt
from src.utils.text_analysis import count_words

logger = logging.getLogger(__name__)


async def write_text_node(state: OrderWorkflowState) -> dict:
    """
    Генерирует академический текст на основе требований

    Args:
        state: Текущее состояние workflow

    Returns:
        Обновленное состояние с сгенерированным текстом
    """
    logger.info(f"✍️  Writing text for order {state['order_id']}...")

    requirements: Dict[str, Any] = state.get('requirements', {})

    if not requirements:
        logger.error("No requirements found for writing")
        return {
            **state,
            "status": "writing_failed",
            "error": "No requirements extracted",
            "agent_logs": state.get('agent_logs', []) + ["[writer] ERROR: No requirements to write from"]
        }

    # Извлекаем параметры
    assignment_type: str = requirements.get('assignment_type', 'essay')
    main_topic: str = requirements.get('main_topic', state.get('order_description', ''))
    main_question: str = requirements.get('main_question', 'Address the topic comprehensively')
    required_sources: int = requirements.get('required_sources', 2)
    specific_instructions: str = requirements.get('specific_instructions', '')

    # Расчёт целевого количества слов: pages * 300
    pages: int = state['pages_required']
    target_word_count: int = pages * 300

    # Контент из файлов
    files_content: str = state.get('parsed_files_content', '')
    if files_content:
        # Ограничиваем размер контента для промпта
        files_content = files_content[:3000]
    else:
        files_content = "No additional files provided."

    try:
        llm = get_smart_model()

        if not llm:
            logger.error("LLM not available for writing")
            return {
                **state,
                "status": "writing_failed",
                "error": "LLM not configured",
                "agent_logs": state.get('agent_logs', []) + ["[writer] ERROR: LLM not available"]
            }

        # Проверяем, это первая генерация или дополнение
        is_expansion: bool = state.get('draft_text', '') != ''

        if is_expansion:
            # Это дополнение существующего текста
            current_text: str = state['draft_text']
            current_word_count: int = state.get('word_count', 0)
            words_needed: int = target_word_count - current_word_count

            logger.info(f"📝 Expanding existing text (current: {current_word_count}, target: {target_word_count}, need: +{words_needed} words)")

            # Определяем стратегию расширения в зависимости от того, сколько слов не хватает
            expansion_strategy: str = ""

            if words_needed > 1000:
                expansion_strategy = f"""
**EXPANSION STRATEGY:**
You need to add approximately {words_needed} words. This requires substantial additions:
1. Add 2-3 NEW body sections on related subtopics
2. Each new section should be 300-500 words
3. Possible new sections to add:
   - Cultural and societal factors influencing the topic
   - Policy implications and recommendations
   - Case studies or real-world examples
   - Comparative analysis with related issues
   - Future directions and research needs
   - Theoretical frameworks and their applications
4. Ensure each new section has its own heading and follows the same citation pattern
"""
            elif words_needed > 500:
                expansion_strategy = f"""
**EXPANSION STRATEGY:**
You need to add approximately {words_needed} words. Add substantial content:
1. Expand EXISTING body sections by adding:
   - More detailed explanations of key concepts
   - Additional examples and evidence
   - Counter-arguments and rebuttals
   - Deeper analysis and implications
2. Add 1-2 NEW body sections if appropriate
3. Each paragraph should be expanded with 2-3 additional sentences
"""
            else:
                expansion_strategy = f"""
**EXPANSION STRATEGY:**
You need to add approximately {words_needed} words. Make targeted additions:
1. Expand existing paragraphs by adding:
   - More supporting details and explanations
   - Additional examples
   - Transitions between ideas
2. Ensure each body paragraph is at least 150-200 words
3. Add 1-2 sentences to introduction and conclusion if needed
"""

            expansion_prompt: str = f"""You are expanding an academic essay that needs more words.

CURRENT TEXT ({current_word_count} words):
{current_text}

TASK:
Expand this essay to reach the target word count of {target_word_count} words.

{expansion_strategy}

REQUIREMENTS:
- Target word count: {target_word_count} words (you MUST add {words_needed} more words)
- Maintain the same style and tone
- Keep all existing citations
- Add new citations as needed (realistic academic citations with author names and years 2019-2024)
- Follow the same structure and format rules
- Do NOT add title or references page
- Ensure smooth flow and logical connections between new and existing content

**CRITICAL FORMATTING RULES:**
- NEVER start or end paragraphs with citations
- Each paragraph must start with a topic sentence and end with a concluding sentence
- Citations should be in the middle of paragraphs with explanations before and after
- Use format: (Author, Year) or (Author et al., Year) - NO page numbers
- Body sections must have SHORT headings (not "Introduction" or "Conclusion")

**IMPORTANT:** Output the COMPLETE expanded text (not just additions). Make sure the final output is close to {target_word_count} words.
"""

            print("\n" + "="*80)
            print("EXPANDING TEXT...")
            print("="*80 + "\n")

            # Генерация с streaming
            full_text: str = ""
            async for chunk in llm.astream(expansion_prompt):
                content = chunk.content
                print(content, end='', flush=True)
                full_text += content

            print("\n")

        else:
            # Первая генерация
            logger.info(f"📝 Generating initial text (target: {target_word_count} words)")

            writing_prompt: str = get_writer_prompt(
                assignment_type=assignment_type,
                main_topic=main_topic,
                target_word_count=target_word_count,
                required_sources=required_sources,
                main_question=main_question,
                files_content=files_content,
                specific_instructions=specific_instructions
            )

            print("\n" + "="*80)
            print("GENERATING TEXT...")
            print("="*80 + "\n")

            # Генерация с streaming
            full_text: str = ""
            async for chunk in llm.astream(writing_prompt):
                content = chunk.content
                print(content, end='', flush=True)
                full_text += content

            print("\n")

        # Подсчитываем слова в сгенерированном тексте
        word_count: int = count_words(full_text)

        logger.info(f"✅ Generated text with {word_count} words (target: {target_word_count})")

        return {
            **state,
            "status": "text_generated",
            "draft_text": full_text.strip(),
            "word_count": word_count,
            "agent_logs": state.get('agent_logs', []) + [
                f"[writer] Generated text: {word_count} words (target: {target_word_count})"
            ]
        }

    except Exception as e:
        logger.error(f"Error writing text for order {state['order_id']}: {e}")
        return {
            **state,
            "status": "writing_failed",
            "error": f"Writing error: {str(e)}",
            "agent_logs": state.get('agent_logs', []) + [
                f"[writer] ERROR: {str(e)}"
            ]
        }
