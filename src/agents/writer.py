"""
Bot 2: Writer
Пишет текст в трех режимах:
- initial: первоначальное написание
- expand: расширение текста (добавление предложений)
- revise: исправление по замечаниям качества
НЕ вставляет цитаты - это делает Bot 3
"""
import logging
from typing import Dict, Any, List

from src.workflows.state import OrderWorkflowState
from src.utils.llm_service import get_smart_model

logger = logging.getLogger(__name__)


def count_words(text: str) -> int:
    """Подсчитывает количество слов в тексте"""
    if not text:
        return 0
    return len(text.split())


async def write_text_node(state: OrderWorkflowState) -> dict:
    """
    Bot 2: Пишет текст в зависимости от режима

    Режимы:
    - initial: первое написание текста по требованиям
    - expand: добавление предложений для увеличения word count
    - revise: переписывание с учетом quality issues

    Args:
        state: Текущее состояние workflow

    Returns:
        Обновленное состояние с draft_text
    """
    mode = state.get('writer_mode', 'initial')
    requirements = state.get('requirements', {})
    target_words = state.get('target_word_count', requirements.get('target_word_count', 300))

    logger.info(f"✍️ Bot 2: Writing text in '{mode}' mode for order {state['order_id']}...")

    try:
        llm = get_smart_model()

        if not llm:
            logger.error("Smart LLM not available")
            return {
                **state,
                "status": "failed",
                "error": "LLM not available for writing",
                "agent_logs": state.get('agent_logs', []) + ["[Bot2:Writer] ERROR: LLM not available"]
            }

        if mode == "initial":
            return await _write_initial(state, llm, requirements, target_words)
        elif mode == "expand":
            return await _write_expand(state, llm, requirements, target_words)
        elif mode == "revise":
            return await _write_revise(state, llm, requirements)
        else:
            logger.error(f"Unknown writer mode: {mode}")
            return {
                **state,
                "status": "failed",
                "error": f"Unknown writer mode: {mode}",
                "agent_logs": state.get('agent_logs', []) + [f"[Bot2:Writer] ERROR: Unknown mode {mode}"]
            }

    except Exception as e:
        logger.error(f"Error in writer: {e}")
        logger.exception(e)
        return {
            **state,
            "status": "failed",
            "error": f"Writing failed: {str(e)}",
            "agent_logs": state.get('agent_logs', []) + [f"[Bot2:Writer] ERROR: {str(e)}"]
        }


async def _write_initial(state: OrderWorkflowState, llm, requirements: Dict, target_words: int) -> dict:
    """Первоначальное написание текста"""
    print("\n" + "="*80)
    print("✍️ Bot 2: WRITING INITIAL TEXT...")
    print("="*80 + "\n")

    # Формируем структуру для промпта
    structure_text = ""
    if requirements.get('structure'):
        struct = requirements['structure']
        structure_text = f"""
REQUIRED STRUCTURE:
- Introduction: ~{struct.get('introduction_words', 50)} words
"""
        for i, section in enumerate(struct.get('body_sections', []), 1):
            structure_text += f"- {section.get('heading', f'Section {i}')}: ~{section.get('words', 100)} words\n"
        structure_text += f"- Conclusion: ~{struct.get('conclusion_words', 50)} words"

    # Формируем key points
    key_points_text = ""
    if requirements.get('key_points'):
        key_points_text = "\nKEY POINTS TO ADDRESS:\n"
        for point in requirements['key_points']:
            key_points_text += f"- {point}\n"

    prompt = f"""Write an academic {requirements.get('assignment_type', 'essay')} on the following topic.

TOPIC: {requirements.get('main_topic', state.get('order_description', 'Not specified'))}

MAIN QUESTION TO ANSWER: {requirements.get('main_question', 'Address the topic comprehensively')}

TARGET WORD COUNT: {target_words} words
{structure_text}
{key_points_text}

SPECIFIC INSTRUCTIONS: {requirements.get('specific_instructions', 'None')}

=== CRITICAL ACADEMIC WRITING RULES ===

**INTRODUCTION (~10% of total words):**
- NEVER use "This essay will...", "This paper examines...", "In this paper..."
- End with a clear THESIS STATEMENT following ISO rule:
  * IDEA: Your main argument/position
  * SUPPORT: Why/how (2-3 reasons)
  * ORDER: Shows structure of body paragraphs

WRONG THESIS: "This essay examines how gender affects violence..."
RIGHT THESIS: "Gender symmetry in domestic violence reveals patterns in perpetration rates, challenges traditional frameworks, and suggests new approaches to justice."

**BODY PARAGRAPHS:**
- Each paragraph discusses ONE idea only
- First sentence = TOPIC SENTENCE (introduces the paragraph's main point)
- Last sentence = CONCLUDING SENTENCE (summarizes paragraph - YOUR words)
- At least 5-6 sentences per paragraph
- All paragraphs approximately equal length

**CONCLUSION (~10% of total words):**
- Summarize main points
- Restate thesis in different words
- NO new information

**PROHIBITED WORDS (never use):**
delve, realm, harness, unlock, tapestry, paradigm, cutting-edge, revolutionize, landscape, potential, findings, intricate, showcasing, crucial, pivotal, surpass, meticulously, vibrant, unparalleled, underscore, leverage, synergy, innovative, game-changer, testament, commendable, meticulous, highlight, emphasize, boast, groundbreaking, align, foster, showcase, enhance, holistic, garner, accentuate, pioneering, trailblazing, unleash, versatile, transformative, redefine, seamless, optimize, scalable, robust, breakthrough, empower, streamline, comprehensive, nuanced, multifaceted

**STYLE:**
- NO contractions (don't → do not, isn't → is not)
- NO first/second person (I, we, you, my, our)
- NO rhetorical questions
- NO conjunctions at sentence start (And, But, Or)
- Academic but natural tone

**OUTPUT:**
- DO NOT include any citations - they will be added later by Bot 3
- DO NOT write a References section
- Start with introduction, then body sections with headings, then conclusion

Write the essay now."""

    response = await llm.ainvoke(prompt)
    draft_text = response.content.strip()

    # Удаляем References если LLM всё же добавил
    if "References" in draft_text or "Bibliography" in draft_text:
        for marker in ["References", "Bibliography", "Works Cited"]:
            if marker in draft_text:
                draft_text = draft_text[:draft_text.find(marker)].strip()

    word_count = count_words(draft_text)

    print(f"📝 Initial draft written: {word_count} words")
    print(f"   Target: {target_words} words")
    print(f"   {'✅ Meets target' if word_count >= target_words else '⚠️ Below target'}")
    print()

    logger.info(f"Initial draft: {word_count} words (target: {target_words})")

    return {
        **state,
        "draft_text": draft_text,
        "word_count": word_count,
        "writer_mode": "initial",
        "status": "text_written",
        "agent_logs": state.get('agent_logs', []) + [
            f"[Bot2:Writer] Initial draft: {word_count}/{target_words} words"
        ]
    }


async def _write_expand(state: OrderWorkflowState, llm, requirements: Dict, target_words: int) -> dict:
    """Расширение текста - добавление предложений"""
    current_text = state.get('draft_text', '')
    current_words = count_words(current_text)
    words_needed = target_words - current_words

    print("\n" + "="*80)
    print(f"✍️ Bot 2: EXPANDING TEXT (+{words_needed} words needed)...")
    print("="*80 + "\n")

    prompt = f"""Expand this academic text by adding MORE CONTENT to reach the target word count.

CURRENT TEXT ({current_words} words):
{current_text}

TARGET: {target_words} words (need to add approximately {words_needed} more words)

TOPIC: {requirements.get('main_topic', 'Not specified')}
MAIN QUESTION: {requirements.get('main_question', 'Not specified')}

HOW TO EXPAND:
1. Add more detailed explanations to existing paragraphs
2. Add more examples or elaborations
3. Expand on key arguments with additional sentences
4. Add transitional sentences between paragraphs
5. Develop the conclusion more thoroughly

RULES:
- DO NOT add citations or references
- DO NOT repeat the same ideas - add NEW content
- Maintain academic tone and quality
- Keep the same structure (intro, body, conclusion)
- Make sure the expanded content still answers the main question

Return the COMPLETE expanded text (not just the additions)."""

    response = await llm.ainvoke(prompt)
    expanded_text = response.content.strip()

    # Удаляем References если добавлены
    for marker in ["References", "Bibliography", "Works Cited"]:
        if marker in expanded_text:
            expanded_text = expanded_text[:expanded_text.find(marker)].strip()

    new_word_count = count_words(expanded_text)

    print(f"📝 Text expanded: {current_words} → {new_word_count} words")
    print(f"   Target: {target_words} words")
    print(f"   {'✅ Meets target' if new_word_count >= target_words else '⚠️ Still below target'}")
    print()

    logger.info(f"Expanded: {current_words} → {new_word_count} words")

    return {
        **state,
        "draft_text": expanded_text,
        "word_count": new_word_count,
        "writer_mode": "expand",
        "word_count_attempts": state.get('word_count_attempts', 0) + 1,
        "status": "text_written",
        "agent_logs": state.get('agent_logs', []) + [
            f"[Bot2:Writer] Expanded: {current_words} → {new_word_count} words"
        ]
    }


async def _write_revise(state: OrderWorkflowState, llm, requirements: Dict) -> dict:
    """Исправление текста по замечаниям качества"""
    current_text = state.get('text_with_citations', state.get('draft_text', ''))
    quality_issues = state.get('quality_issues', [])
    quality_suggestions = state.get('quality_suggestions', [])
    citation_action = state.get('citation_action', 'keep')

    print("\n" + "="*80)
    print("✍️ Bot 2: REVISING TEXT BASED ON QUALITY FEEDBACK...")
    print("="*80 + "\n")

    issues_text = "\n".join([f"- {issue}" for issue in quality_issues]) if quality_issues else "None"
    suggestions_text = "\n".join([f"- {s}" for s in quality_suggestions]) if quality_suggestions else "None"

    # Инструкции по цитатам зависят от citation_action
    citation_instructions = ""
    if citation_action == "keep":
        citation_instructions = "KEEP all existing citations exactly as they are (Author, Year). Do not remove or change them."
    elif citation_action == "adjust":
        citation_instructions = "You may MOVE citations to better positions, but keep the same sources."
    elif citation_action == "reinsert":
        citation_instructions = "Citations will be re-added later. Focus only on the text content."

    prompt = f"""Revise this academic text to fix ALL the quality issues listed below.

=== CURRENT TEXT ===
{current_text}

=== QUALITY ISSUES TO FIX (MUST FIX ALL) ===
{issues_text}

=== SUGGESTIONS ===
{suggestions_text}

=== CONTEXT ===
TOPIC: {requirements.get('main_topic', 'Not specified')}
MAIN QUESTION: {requirements.get('main_question', 'Not specified')}
CITATION HANDLING: {citation_instructions}

=== ACADEMIC WRITING RULES (MUST FOLLOW) ===

**INTRODUCTION:**
- NEVER use "This essay will...", "This paper examines...", "In this paper..." - these announce intentions
- Thesis must be at the END of introduction
- Thesis must follow ISO: Idea + Support + Order

**BAD THESIS (NEVER USE):**
- "This essay examines how..."
- "This paper will discuss..."
- "This essay discusses..."

**GOOD THESIS EXAMPLE:**
- "Gender symmetry in domestic violence reveals important patterns, challenging traditional frameworks and suggesting new approaches to justice."

**BODY PARAGRAPHS:**
- Each paragraph must START with a topic sentence (YOUR words, no citation)
- Each paragraph must END with a concluding sentence (YOUR words, NO citation)
- Citations go in the MIDDLE only
- WRONG ending: "...better outcomes (Smith, 2020)."
- RIGHT ending: "...better outcomes (Smith, 2020). These results show the importance of continued research."

**CONCLUSION:**
- NO new information
- NO citations
- Summarize main points
- Restate thesis differently

**PROHIBITED WORDS (replace with alternatives):**
delve, realm, harness, unlock, tapestry, paradigm, cutting-edge, revolutionize, landscape, potential, findings, intricate, showcasing, crucial, pivotal, surpass, meticulously, vibrant, unparalleled, underscore, leverage, synergy, innovative, game-changer, testament, commendable, meticulous, highlight, emphasize, boast, groundbreaking, align, foster, showcase, enhance, holistic, garner, accentuate, pioneering, trailblazing, unleash, versatile, transformative, redefine, seamless, optimize, scalable, robust, breakthrough, empower, streamline, comprehensive, nuanced, multifaceted

**STYLE:**
- NO contractions (don't → do not)
- NO first person (I, we, you, my, our)
- NO rhetorical questions
- NO conjunctions at sentence start (And, But, Or)

=== TASK ===
Fix ALL issues listed above. Return the COMPLETE revised text.
Maintain approximately the same word count (±10%)."""

    response = await llm.ainvoke(prompt)
    revised_text = response.content.strip()

    # Удаляем References если добавлены
    for marker in ["References", "Bibliography", "Works Cited"]:
        if marker in revised_text:
            revised_text = revised_text[:revised_text.find(marker)].strip()

    word_count = count_words(revised_text)

    print(f"📝 Text revised: {word_count} words")
    print(f"   Issues addressed: {len(quality_issues)}")
    print()

    logger.info(f"Revised text: {word_count} words, fixed {len(quality_issues)} issues")

    # Если citation_action == "reinsert", то текст идёт обратно в draft_text
    # иначе обновляем text_with_citations
    if citation_action == "reinsert":
        return {
            **state,
            "draft_text": revised_text,
            "word_count": word_count,
            "writer_mode": "revise",
            "citations_inserted": False,  # Нужно заново вставить цитаты
            "quality_check_attempts": state.get('quality_check_attempts', 0) + 1,
            "status": "text_written",
            "agent_logs": state.get('agent_logs', []) + [
                f"[Bot2:Writer] Revised text, citations need reinsertion"
            ]
        }
    else:
        return {
            **state,
            "text_with_citations": revised_text,
            "word_count": word_count,
            "writer_mode": "revise",
            "quality_check_attempts": state.get('quality_check_attempts', 0) + 1,
            "status": "text_revised",
            "agent_logs": state.get('agent_logs', []) + [
                f"[Bot2:Writer] Revised text, citations {citation_action}"
            ]
        }
