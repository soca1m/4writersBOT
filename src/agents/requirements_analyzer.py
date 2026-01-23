"""
Bot 1: Requirements Analyzer
Извлекает структурированные требования из описания задания
Возвращает JSON с темой, структурой, количеством слов и источников
"""
import json
import logging
import re
from typing import Dict, Any

from src.workflows.state import OrderWorkflowState
from src.utils.llm_service import get_smart_model
from src.utils.file_parser import parse_multiple_files

logger = logging.getLogger(__name__)


def parse_json_response(text: str) -> Dict[str, Any]:
    """Извлекает JSON из ответа LLM"""
    # Убираем markdown code blocks
    text = re.sub(r'```json\s*', '', text)
    text = re.sub(r'```\s*', '', text)
    text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Пробуем найти JSON между { и }
        match = re.search(r'\{[\s\S]*\}', text)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
    return {}


async def analyze_requirements_node(state: OrderWorkflowState) -> dict:
    """
    Bot 1: Анализирует задание и извлекает структурированные требования

    Args:
        state: Текущее состояние workflow

    Returns:
        Обновленное состояние с requirements
    """
    logger.info(f"📋 Bot 1: Analyzing requirements for order {state['order_id']}...")

    # Парсим прикрепленные файлы
    files_content = ""
    if state.get('attached_files'):
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
                "error": "LLM not available",
                "agent_logs": state.get('agent_logs', []) + ["[Bot1:Requirements] ERROR: LLM not available"]
            }

        # Рассчитываем целевое количество слов
        pages = state.get('pages_required', 1)
        target_word_count = pages * 300

        prompt = f"""You are an academic assignment analyzer. Extract structured requirements from this assignment.

ORDER INFORMATION:
- Description: {state.get('order_description', 'Not specified')}
- Pages required: {pages}
- Minimum word count: {target_word_count} words
- Academic level: University

ATTACHED FILES CONTENT:
{files_content if files_content else "No files attached"}

TASK: Analyze the assignment and return a JSON response.

Return ONLY valid JSON (no markdown, no extra text):

{{
  "is_sufficient": true,
  "missing_info": null,
  "assignment_type": "essay/discussion post/case study/research paper/short answer",
  "main_topic": "the core topic in 1-2 sentences",
  "main_question": "the specific question(s) to answer",
  "required_sources": {max(2, pages)},
  "search_keywords": "keyword1 keyword2 keyword3 (space-separated string, NOT array)",
  "citation_style": "APA",
  "structure": {{
    "introduction_words": {int(target_word_count * 0.1)},
    "body_sections": [
      {{"heading": "Section 1 topic", "words": {int(target_word_count * 0.35)}}},
      {{"heading": "Section 2 topic", "words": {int(target_word_count * 0.35)}}}
    ],
    "conclusion_words": {int(target_word_count * 0.1)}
  }},
  "key_points": ["important point 1", "important point 2"],
  "specific_instructions": "any special requirements from the assignment",
  "target_word_count": {target_word_count}
}}

STRUCTURE GUIDELINES by word count:
- 300 words: intro 30 + 1-2 body sections 210 + conclusion 30
- 600 words: intro 60 + 2-3 body sections 450 + conclusion 60
- 900 words: intro 90 + 3-4 body sections 700 + conclusion 90
- 1500 words: intro 150 + 4-5 body sections 1150 + conclusion 150

SOURCES GUIDELINES:
- 1-2 pages: 2 sources
- 3-4 pages: 3-4 sources
- 5+ pages: 4-5 sources

If the assignment description is unclear or missing critical information, set:
- "is_sufficient": false
- "missing_info": "what specific information is missing"

Return ONLY the JSON object, nothing else."""

        print("\n" + "="*80)
        print("🤖 Bot 1: ANALYZING REQUIREMENTS...")
        print("="*80 + "\n")

        response = await llm.ainvoke(prompt)
        response_text = response.content.strip()

        # Парсим JSON
        requirements = parse_json_response(response_text)

        if not requirements:
            logger.error("Failed to parse JSON response")
            print(f"Raw response: {response_text[:500]}...")
            return {
                **state,
                "status": "failed",
                "error": "Failed to parse requirements JSON",
                "agent_logs": state.get('agent_logs', []) + ["[Bot1:Requirements] ERROR: JSON parse failed"]
            }

        # Проверяем достаточно ли информации
        is_sufficient = requirements.get('is_sufficient', True)

        if not is_sufficient:
            missing = requirements.get('missing_info', 'Unknown')
            logger.warning(f"Insufficient information: {missing}")
            print(f"❌ INSUFFICIENT INFO: {missing}\n")
            return {
                **state,
                "requirements": requirements,
                "parsed_files_content": files_content,
                "status": "insufficient_info",
                "error": f"Insufficient information: {missing}",
                "agent_logs": state.get('agent_logs', []) + [f"[Bot1:Requirements] INSUFFICIENT: {missing}"]
            }

        # Добавляем дополнительные поля
        requirements['pages'] = pages
        requirements['target_word_count'] = target_word_count

        # Выводим результаты
        print("📋 REQUIREMENTS EXTRACTED:\n")
        print(f"  Type: {requirements.get('assignment_type', 'N/A')}")
        print(f"  Topic: {requirements.get('main_topic', 'N/A')}")
        print(f"  Main Question: {requirements.get('main_question', 'N/A')}")
        print(f"  Target Words: {requirements.get('target_word_count', 'N/A')}")
        print(f"  Required Sources: {requirements.get('required_sources', 'N/A')}")
        print(f"  Search Keywords: {requirements.get('search_keywords', 'N/A')}")
        print(f"  Citation Style: {requirements.get('citation_style', 'APA')}")

        if requirements.get('structure'):
            print(f"\n  Structure:")
            struct = requirements['structure']
            print(f"    - Intro: {struct.get('introduction_words', 0)} words")
            for section in struct.get('body_sections', []):
                print(f"    - {section.get('heading', 'Section')}: {section.get('words', 0)} words")
            print(f"    - Conclusion: {struct.get('conclusion_words', 0)} words")

        if requirements.get('key_points'):
            print(f"\n  Key Points:")
            for point in requirements['key_points']:
                print(f"    • {point}")

        print("\n" + "="*80 + "\n")

        logger.info("✅ Requirements extracted successfully")

        return {
            **state,
            "requirements": requirements,
            "parsed_files_content": files_content,
            "target_word_count": target_word_count,
            "status": "requirements_extracted",
            "agent_logs": state.get('agent_logs', []) + [
                f"[Bot1:Requirements] Extracted: {requirements.get('assignment_type')}, {target_word_count} words, {requirements.get('required_sources')} sources"
            ]
        }

    except Exception as e:
        logger.error(f"Error analyzing requirements: {e}")
        logger.exception(e)
        return {
            **state,
            "status": "failed",
            "error": f"Requirements analysis failed: {str(e)}",
            "agent_logs": state.get('agent_logs', []) + [f"[Bot1:Requirements] ERROR: {str(e)}"]
        }
