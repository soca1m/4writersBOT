"""
Research Agent - находит академические источники через Tavily API
"""
import logging
import os
from typing import List, Dict, Any
from datetime import datetime

from src.workflows.state import OrderWorkflowState
from src.utils.llm_service import get_fast_model
from src.utils.prompt_loader import get_researcher_prompt

logger = logging.getLogger(__name__)


async def research_sources_node(state: OrderWorkflowState) -> dict:
    """
    Ищет академические источники по теме заказа

    Args:
        state: Текущее состояние workflow

    Returns:
        Обновленное состояние с найденными источниками
    """
    logger.info(f"🔍 Researching sources for order {state['order_id']}...")

    requirements: Dict[str, Any] = state.get('requirements', {})
    main_topic: str = requirements.get('main_topic', state.get('order_description', ''))
    required_sources: int = requirements.get('required_sources', 2)

    if not main_topic:
        logger.error("No topic found for research")
        return {
            **state,
            "status": "research_failed",
            "error": "No topic specified for research",
            "agent_logs": state.get('agent_logs', []) + ["[researcher] ERROR: No topic for research"]
        }

    try:
        # Проверяем наличие Tavily API
        tavily_api_key: str = os.getenv("TAVILY_API_KEY", "")
        if not tavily_api_key:
            logger.error("TAVILY_API_KEY not found in environment")
            return {
                **state,
                "status": "research_failed",
                "error": "TAVILY_API_KEY not configured",
                "agent_logs": state.get('agent_logs', []) + ["[researcher] ERROR: TAVILY_API_KEY not found"]
            }

        # Импортируем Tavily
        try:
            from tavily import TavilyClient
        except ImportError:
            logger.error("tavily-python package not installed")
            return {
                **state,
                "status": "research_failed",
                "error": "tavily-python package not installed",
                "agent_logs": state.get('agent_logs', []) + ["[researcher] ERROR: tavily-python not installed"]
            }

        # Генерируем поисковые запросы с помощью LLM
        logger.info("Generating search queries...")
        llm = get_fast_model()

        if not llm:
            logger.warning("LLM not available, using topic as-is")
            search_queries: List[str] = [main_topic]
        else:
            current_year: int = datetime.now().year
            min_year: int = current_year - 5  # Источники не старше 5 лет

            research_prompt: str = get_researcher_prompt(
                main_topic=main_topic,
                required_sources=required_sources,
                min_year=min_year
            )

            response = await llm.ainvoke(research_prompt)
            queries_text: str = response.content.strip()

            # Парсим запросы из ответа
            search_queries = []
            for line in queries_text.split('\n'):
                line = line.strip()
                if line and (line[0].isdigit() or line.startswith('-')):
                    # Убираем номер и берём текст
                    query: str = line.split('.', 1)[-1].strip() if '.' in line else line.strip('- ')
                    if query:
                        search_queries.append(query)

            if not search_queries:
                search_queries = [main_topic]

            logger.info(f"Generated {len(search_queries)} search queries")

        # Инициализируем Tavily клиент
        tavily_client = TavilyClient(api_key=tavily_api_key)

        # Выполняем поиск по каждому запросу
        all_sources: List[Dict[str, Any]] = []
        seen_urls: set = set()

        # Академические домены для фильтрации
        academic_domains: List[str] = [
            "edu",
            "scholar.google.com",
            "researchgate.net",
            "jstor.org",
            "springer.com",
            "sciencedirect.com",
            "wiley.com",
            "tandfonline.com",
            "sagepub.com",
            "apa.org",
            "nih.gov",
            "pubmed"
        ]

        current_year: int = datetime.now().year
        min_year: int = current_year - 5

        for query in search_queries[:3]:  # Ограничиваем 3 запросами
            logger.info(f"Searching: {query}")

            try:
                # Поиск с фильтрами
                response = tavily_client.search(
                    query=query,
                    search_depth="advanced",
                    max_results=5,
                    include_domains=academic_domains
                )

                # Обрабатываем результаты
                for result in response.get('results', []):
                    url: str = result.get('url', '')

                    # Пропускаем дубликаты
                    if url in seen_urls:
                        continue

                    # Пропускаем PDF напрямую (они обычно не содержат метаданные)
                    if url.endswith('.pdf'):
                        continue

                    # Проверяем академический домен
                    is_academic: bool = any(domain in url.lower() for domain in academic_domains)
                    if not is_academic:
                        continue

                    title: str = result.get('title', '')
                    content: str = result.get('content', '')

                    # Пытаемся извлечь год из контента
                    year: int = extract_year_from_content(content, title)

                    # Фильтруем по году если можем определить
                    if year and year < min_year:
                        logger.info(f"Skipping old source: {title} ({year})")
                        continue

                    source: Dict[str, Any] = {
                        'title': title,
                        'url': url,
                        'content': content[:500],  # Краткое содержание
                        'year': year if year else None,
                        'query_used': query
                    }

                    all_sources.append(source)
                    seen_urls.add(url)

                    # Останавливаемся если набрали достаточно
                    if len(all_sources) >= required_sources * 2:
                        break

            except Exception as e:
                logger.warning(f"Error searching query '{query}': {e}")
                continue

            # Останавливаемся если набрали достаточно
            if len(all_sources) >= required_sources * 2:
                break

        # Проверяем результаты
        if not all_sources:
            logger.warning(f"No academic sources found for topic: {main_topic}")
            return {
                **state,
                "status": "insufficient_sources",
                "sources_found": [],
                "agent_logs": state.get('agent_logs', []) + [
                    f"[researcher] WARNING: No academic sources found for: {main_topic}"
                ]
            }

        # Ограничиваем количество источников
        sources_to_use: List[Dict[str, Any]] = all_sources[:required_sources * 2]

        logger.info(f"✅ Found {len(sources_to_use)} academic sources")

        return {
            **state,
            "status": "sources_found",
            "sources_found": sources_to_use,
            "agent_logs": state.get('agent_logs', []) + [
                f"[researcher] Found {len(sources_to_use)} academic sources using {len(search_queries)} queries"
            ]
        }

    except Exception as e:
        logger.error(f"Error researching sources for order {state['order_id']}: {e}")
        return {
            **state,
            "status": "research_failed",
            "error": f"Research error: {str(e)}",
            "agent_logs": state.get('agent_logs', []) + [
                f"[researcher] ERROR: {str(e)}"
            ]
        }


def extract_year_from_content(content: str, title: str) -> int:
    """
    Пытается извлечь год публикации из контента или заголовка

    Args:
        content: Текст контента
        title: Заголовок

    Returns:
        Год публикации или 0 если не найден
    """
    import re

    current_year: int = datetime.now().year

    # Ищем год в формате 4 цифр
    text: str = f"{title} {content}"
    years: List[int] = []

    # Паттерны для поиска года
    patterns: List[str] = [
        r'\b(20[0-2][0-9])\b',  # 2000-2029
        r'\((\d{4})\)',  # Год в скобках
        r'(?:published|pub\.|copyright|©)\s*(\d{4})',  # После ключевых слов
    ]

    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            year: int = int(match)
            if 2000 <= year <= current_year:
                years.append(year)

    # Возвращаем самый поздний год (скорее всего год публикации)
    if years:
        return max(years)

    return 0
