"""
Rewriter Agent - переписывает текст используя ZeroGPT Humanizer API
"""
import logging
import httpx
from typing import Dict, Any

from src.workflows.state import OrderWorkflowState
from src.utils.text_analysis import count_words

logger = logging.getLogger(__name__)

# ZeroGPT Humanizer API endpoint
ZEROGPT_HUMANIZER_URL = "https://api.zerogpt.com/api/transform/humanize"

# Заголовки для запроса
ZEROGPT_HEADERS = {
    'Host': 'api.zerogpt.com',
    'Connection': 'keep-alive',
    'sec-ch-ua-platform': '"Windows"',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36 Edg/144.0.0.0',
    'Accept': 'application/json, text/plain, */*',
    'sec-ch-ua': '"Not(A:Brand";v="8", "Chromium";v="144", "Microsoft Edge";v="144"',
    'sec-ch-ua-mobile': '?0',
    'Origin': 'https://www.zerogpt.com',
    'Sec-Fetch-Site': 'same-site',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Dest': 'empty',
    'Referer': 'https://www.zerogpt.com/',
    'Accept-Language': 'ru,en;q=0.9,en-GB;q=0.8,en-US;q=0.7',
    'Content-Type': 'application/json'
}


async def rewrite_text_node(state: OrderWorkflowState) -> dict:
    """
    Переписывает текст используя ZeroGPT Humanizer API

    Args:
        state: Текущее состояние workflow

    Returns:
        Обновленное состояние с переписанным текстом
    """
    logger.info(f"✍️  Humanizing text for order {state['order_id']}...")

    current_text: str = state.get('final_text', '')
    ai_percentage: float = state.get('plagiarism_score', 100.0)

    if not current_text:
        logger.error("No text found for humanizing")
        return {
            **state,
            "status": "rewrite_failed",
            "error": "No text to humanize",
            "agent_logs": state.get('agent_logs', []) + ["[rewriter] ERROR: No text to humanize"]
        }

    # Проверяем количество попыток переписывания
    rewrite_attempts: int = state.get('rewrite_attempts', 0)
    MAX_REWRITE_ATTEMPTS: int = 3

    if rewrite_attempts >= MAX_REWRITE_ATTEMPTS:
        logger.error(f"Maximum humanize attempts reached ({MAX_REWRITE_ATTEMPTS})")
        return {
            **state,
            "status": "rewrite_failed",
            "error": f"Maximum humanize attempts ({MAX_REWRITE_ATTEMPTS}) reached, still {ai_percentage}% AI",
            "agent_logs": state.get('agent_logs', []) + [
                f"[rewriter] ERROR: Max attempts reached ({MAX_REWRITE_ATTEMPTS}), AI: {ai_percentage}%"
            ]
        }

    try:
        logger.info(f"📝 Humanizing attempt {rewrite_attempts + 1}/{MAX_REWRITE_ATTEMPTS}")
        logger.info(f"Current AI detection: {ai_percentage}%, target: <10%")

        print("\n" + "="*80)
        print(f"HUMANIZING TEXT (Attempt {rewrite_attempts + 1}/{MAX_REWRITE_ATTEMPTS})...")
        print(f"Current AI: {ai_percentage}%, Target: <10%")
        print("="*80 + "\n")

        # Отправляем запрос к ZeroGPT Humanizer API
        async with httpx.AsyncClient(timeout=120.0) as client:
            payload: Dict[str, Any] = {
                "string": current_text,
                "skipRealtime": 1,
                "humanizerReadability": "High School",
                "humanizerPurpose": "General Writing",
                "humanizerStrength": "Balanced",
                "humanizerModel": "v11"
            }

            logger.info("Sending text to ZeroGPT Humanizer API...")

            response = await client.post(
                ZEROGPT_HUMANIZER_URL,
                headers=ZEROGPT_HEADERS,
                json=payload
            )

            response.raise_for_status()
            result: Dict[str, Any] = response.json()

            # Логируем ответ для отладки
            logger.info(f"ZeroGPT Humanizer API response: {result}")
            print(f"\nAPI Response: {result}\n")

            # Проверяем успешность запроса
            if not result.get('success'):
                error_msg: str = result.get('message', 'Unknown error')
                logger.error(f"ZeroGPT Humanizer API error: {error_msg}")
                return {
                    **state,
                    "status": "rewrite_failed",
                    "error": f"ZeroGPT Humanizer API error: {error_msg}",
                    "agent_logs": state.get('agent_logs', []) + [
                        f"[rewriter] ERROR: API returned error: {error_msg}"
                    ]
                }

            # Извлекаем humanized текст
            data: Dict[str, Any] = result.get('data', {})
            humanized_text: str = data.get('output', '')

            if not humanized_text:
                logger.error("No humanized text returned from API")
                return {
                    **state,
                    "status": "rewrite_failed",
                    "error": "No humanized text returned",
                    "agent_logs": state.get('agent_logs', []) + [
                        "[rewriter] ERROR: No humanized text in response"
                    ]
                }

            # Выводим результат
            print(humanized_text)
            print("\n")

            # Подсчитываем слова
            word_count: int = count_words(humanized_text)

            logger.info(f"✅ Humanized text: {word_count} words")

            # Обновляем количество попыток
            new_rewrite_attempts: int = rewrite_attempts + 1

            return {
                **state,
                "status": "text_rewritten",
                "draft_text": humanized_text.strip(),
                "final_text": humanized_text.strip(),  # Обновляем final_text для следующей проверки
                "word_count": word_count,
                "rewrite_attempts": new_rewrite_attempts,
                "agent_logs": state.get('agent_logs', []) + [
                    f"[rewriter] Attempt {new_rewrite_attempts}: Humanized text with {word_count} words"
                ]
            }

    except httpx.TimeoutException:
        logger.error("ZeroGPT Humanizer API timeout")
        return {
            **state,
            "status": "rewrite_failed",
            "error": "ZeroGPT Humanizer API timeout",
            "agent_logs": state.get('agent_logs', []) + [
                "[rewriter] ERROR: API timeout"
            ]
        }

    except httpx.HTTPStatusError as e:
        logger.error(f"ZeroGPT Humanizer API HTTP error: {e.response.status_code}")
        return {
            **state,
            "status": "rewrite_failed",
            "error": f"ZeroGPT Humanizer API HTTP error: {e.response.status_code}",
            "agent_logs": state.get('agent_logs', []) + [
                f"[rewriter] ERROR: HTTP {e.response.status_code}"
            ]
        }

    except Exception as e:
        logger.error(f"Error humanizing text for order {state['order_id']}: {e}")
        return {
            **state,
            "status": "rewrite_failed",
            "error": f"Humanize error: {str(e)}",
            "agent_logs": state.get('agent_logs', []) + [
                f"[rewriter] ERROR: {str(e)}"
            ]
        }
