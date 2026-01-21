"""
Утилиты для анализа текста (подсчет слов, цитат и т.д.)
"""
import re
from typing import List, Dict


def count_words(text: str) -> int:
    """
    Подсчитывает количество слов в тексте

    Args:
        text: Текст для анализа

    Returns:
        Количество слов
    """
    # Убираем лишние пробелы и считаем слова
    words = text.split()
    return len(words)


def count_citations(text: str, citation_style: str = "APA") -> int:
    """
    Подсчитывает количество цитат в тексте

    Args:
        text: Текст для анализа
        citation_style: Стиль цитирования (APA, MLA, Chicago)

    Returns:
        Количество найденных цитат
    """
    if citation_style == "APA":
        # Ищем (Author, Year) или (Author et al., Year)
        pattern = r'\([A-Z][a-z]+(?:\s+et\s+al\.)?,\s*\d{4}\)'
        citations = re.findall(pattern, text)
        return len(citations)

    elif citation_style == "MLA":
        # Ищем (Author Page) например (Smith 45)
        pattern = r'\([A-Z][a-z]+\s+\d+\)'
        citations = re.findall(pattern, text)
        return len(citations)

    else:
        # Общий поиск любых паттернов цитирования
        pattern = r'\([^)]+,\s*\d{4}\)'
        citations = re.findall(pattern, text)
        return len(citations)


def extract_citations(text: str) -> List[str]:
    """
    Извлекает все цитаты из текста

    Args:
        text: Текст для анализа

    Returns:
        Список найденных цитат
    """
    # Ищем все паттерны (Author, Year)
    pattern = r'\([^)]+,\s*\d{4}\)'
    citations = re.findall(pattern, text)
    return list(set(citations))  # Убираем дубликаты


def has_references_section(text: str) -> bool:
    """
    Проверяет наличие секции References в тексте

    Args:
        text: Текст для анализа

    Returns:
        True если есть секция References
    """
    # Ищем заголовки References, Bibliography, Works Cited
    pattern = r'(References|Bibliography|Works\s+Cited)\s*\n'
    return bool(re.search(pattern, text, re.IGNORECASE))


def extract_references_section(text: str) -> str:
    """
    Извлекает секцию References из текста

    Args:
        text: Текст с references

    Returns:
        Секция References
    """
    pattern = r'(References|Bibliography|Works\s+Cited)\s*\n(.*?)(\n\n|$)'
    match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)

    if match:
        return match.group(0)
    return ""


def extract_year_from_text(text: str) -> int:
    """
    Извлекает год публикации из текста (для фильтрации источников)

    Args:
        text: Текст для анализа

    Returns:
        Год публикации или 0 если не найден
    """
    # Ищем 4-значное число в диапазоне 1900-2099
    pattern = r'\b(19|20)\d{2}\b'
    matches = re.findall(pattern, text)

    if matches:
        # Возвращаем последний найденный год (обычно год публикации в конце)
        years = [int(m[0] + m[1:]) for m in matches]
        return max(years)

    return 0


def check_academic_structure(text: str) -> Dict[str, bool]:
    """
    Проверяет наличие основных элементов академической структуры

    Args:
        text: Текст для анализа

    Returns:
        Словарь с результатами проверки
    """
    text_lower = text.lower()

    return {
        "has_introduction": any(keyword in text_lower for keyword in ["introduction", "in this paper", "this essay"]),
        "has_body": len(text.split("\n\n")) > 3,  # Больше 3 параграфов
        "has_conclusion": any(keyword in text_lower for keyword in ["conclusion", "in conclusion", "to conclude"]),
        "has_citations": count_citations(text) > 0,
        "has_references": has_references_section(text)
    }
