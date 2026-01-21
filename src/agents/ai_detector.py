"""
AI Detection Checker - проверяет текст на AI-generated content через ZeroGPT
"""
import logging
import httpx
from typing import Dict, Any

from src.workflows.state import OrderWorkflowState

logger = logging.getLogger(__name__)

# ZeroGPT API endpoint
ZEROGPT_API_URL = "https://api.zerogpt.com/api/detect/detectText"

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


async def check_ai_detection_node(state: OrderWorkflowState) -> dict:
    """
    Проверяет текст на AI-generated content

    Критерии:
    - fakePercentage должен быть 0% (или очень низкий)
    - Если > 10% - текст нужно переписать

    Args:
        state: Текущее состояние workflow

    Returns:
        Обновленное состояние с результатами проверки
    """
    logger.info(f"🔍 Checking AI detection for order {state['order_id']}...")

    # Берём текст который прошёл проверку word count
    final_text: str = state.get('final_text', '')

    if not final_text:
        logger.error("No final text found for AI detection check")
        return {
            **state,
            "status": "ai_check_failed",
            "error": "No text to check for AI detection",
            "agent_logs": state.get('agent_logs', []) + ["[ai_detector] ERROR: No text to check"]
        }

    try:
        # Отправляем запрос к ZeroGPT API
        async with httpx.AsyncClient(timeout=60.0) as client:
            payload: Dict[str, str] = {
                "input_text": final_text
            }

            logger.info("Sending text to ZeroGPT API...")

            response = await client.post(
                ZEROGPT_API_URL,
                headers=ZEROGPT_HEADERS,
                json=payload
            )

            response.raise_for_status()
            result: Dict[str, Any] = response.json()

            # Проверяем успешность запроса
            if not result.get('success'):
                error_msg: str = result.get('message', 'Unknown error')
                logger.error(f"ZeroGPT API error: {error_msg}")
                return {
                    **state,
                    "status": "ai_check_failed",
                    "error": f"ZeroGPT API error: {error_msg}",
                    "agent_logs": state.get('agent_logs', []) + [
                        f"[ai_detector] ERROR: API returned error: {error_msg}"
                    ]
                }

            # Извлекаем данные
            data: Dict[str, Any] = result.get('data', {})
            fake_percentage: float = data.get('fakePercentage', 100.0)
            is_human: int = data.get('isHuman', 0)
            feedback: str = data.get('feedback', 'Unknown')
            ai_words: int = data.get('aiWords', 0)
            text_words: int = data.get('textWords', 0)

            logger.info(f"AI Detection Result: {fake_percentage}% AI-generated ({ai_words}/{text_words} words)")
            logger.info(f"Feedback: {feedback}")

            # Порог: если больше 10% AI - нужно переписывать
            AI_THRESHOLD: float = 10.0

            if fake_percentage <= AI_THRESHOLD:
                logger.info(f"✅ Text passed AI detection ({fake_percentage}% ≤ {AI_THRESHOLD}%)")

                return {
                    **state,
                    "status": "ai_check_passed",
                    "plagiarism_score": fake_percentage,  # Используем это поле для AI %
                    "plagiarism_details": {
                        "ai_percentage": fake_percentage,
                        "is_human": is_human,
                        "feedback": feedback,
                        "ai_words": ai_words,
                        "text_words": text_words
                    },
                    "agent_logs": state.get('agent_logs', []) + [
                        f"[ai_detector] PASSED: {fake_percentage}% AI-generated ({ai_words}/{text_words} words)"
                    ]
                }

            else:
                logger.warning(f"⚠️  Text failed AI detection ({fake_percentage}% > {AI_THRESHOLD}%)")

                return {
                    **state,
                    "status": "ai_detected",
                    "plagiarism_score": fake_percentage,
                    "plagiarism_details": {
                        "ai_percentage": fake_percentage,
                        "is_human": is_human,
                        "feedback": feedback,
                        "ai_words": ai_words,
                        "text_words": text_words
                    },
                    "agent_logs": state.get('agent_logs', []) + [
                        f"[ai_detector] FAILED: {fake_percentage}% AI-generated (threshold: {AI_THRESHOLD}%)"
                    ]
                }

    except httpx.TimeoutException:
        logger.error("ZeroGPT API timeout")
        return {
            **state,
            "status": "ai_check_failed",
            "error": "ZeroGPT API timeout",
            "agent_logs": state.get('agent_logs', []) + [
                "[ai_detector] ERROR: API timeout"
            ]
        }

    except httpx.HTTPStatusError as e:
        logger.error(f"ZeroGPT API HTTP error: {e.response.status_code}")
        return {
            **state,
            "status": "ai_check_failed",
            "error": f"ZeroGPT API HTTP error: {e.response.status_code}",
            "agent_logs": state.get('agent_logs', []) + [
                f"[ai_detector] ERROR: HTTP {e.response.status_code}"
            ]
        }

    except Exception as e:
        logger.error(f"Error checking AI detection for order {state['order_id']}: {e}")
        return {
            **state,
            "status": "ai_check_failed",
            "error": f"AI detection error: {str(e)}",
            "agent_logs": state.get('agent_logs', []) + [
                f"[ai_detector] ERROR: {str(e)}"
            ]
        }
