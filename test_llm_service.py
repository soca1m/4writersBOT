"""
Тест нового унифицированного LLM сервиса на базе OpenRouter
"""
import asyncio
import logging
from src.utils.llm_service import (
    get_fast_model,
    get_smart_model,
    get_writer_model,
    get_analyzer_model,
    get_custom_model,
    list_available_models
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_model(model, model_name: str):
    """Тестирует модель простым запросом"""
    try:
        print(f"\n📝 Тестирую {model_name}...")

        response = await model.ainvoke("Say 'OK' in 3 words or less")

        print(f"  ✅ {model_name}: {response.content}")
        return True

    except Exception as e:
        print(f"  ❌ {model_name}: Ошибка - {e}")
        return False


async def main():
    """Главная функция тестирования"""
    print("="*60)
    print("🧪 ТЕСТ УНИФИЦИРОВАННОГО LLM СЕРВИСА")
    print("="*60)

    # Показываем доступные модели
    list_available_models()

    results = {}

    # Тест 1: Fast Model
    print("\n" + "="*60)
    print("1️⃣  FAST MODEL (для простых задач)")
    print("="*60)
    fast_model = get_fast_model()
    if fast_model:
        results["fast"] = await test_model(fast_model, "Fast Model (GPT-4o Mini)")
    else:
        print("  ❌ Fast model failed to initialize")
        results["fast"] = False

    # Тест 2: Smart Model
    print("\n" + "="*60)
    print("2️⃣  SMART MODEL (для сложных задач)")
    print("="*60)
    smart_model = get_smart_model()
    if smart_model:
        results["smart"] = await test_model(smart_model, "Smart Model (Claude 3.5 Sonnet)")
    else:
        print("  ❌ Smart model failed to initialize")
        results["smart"] = False

    # Тест 3: Writer Model
    print("\n" + "="*60)
    print("3️⃣  WRITER MODEL (для генерации текстов)")
    print("="*60)
    writer_model = get_writer_model()
    if writer_model:
        results["writer"] = await test_model(writer_model, "Writer Model (Claude 3.5 Sonnet)")
    else:
        print("  ❌ Writer model failed to initialize")
        results["writer"] = False

    # Тест 4: Analyzer Model
    print("\n" + "="*60)
    print("4️⃣  ANALYZER MODEL (для анализа)")
    print("="*60)
    analyzer_model = get_analyzer_model()
    if analyzer_model:
        results["analyzer"] = await test_model(analyzer_model, "Analyzer Model (Claude 3.5 Sonnet)")
    else:
        print("  ❌ Analyzer model failed to initialize")
        results["analyzer"] = False

    # Тест 5: Custom Model (Gemini)
    print("\n" + "="*60)
    print("5️⃣  CUSTOM MODEL (Gemini Pro)")
    print("="*60)
    try:
        gemini_model = get_custom_model("google/gemini-pro", temperature=0.5, max_tokens=100)
        if gemini_model:
            results["gemini"] = await test_model(gemini_model, "Gemini Pro")
        else:
            print("  ❌ Gemini model failed to initialize")
            results["gemini"] = False
    except Exception as e:
        print(f"  ❌ Gemini test failed: {e}")
        results["gemini"] = False

    # Итоговый отчёт
    print("\n" + "="*60)
    print("📊 ИТОГОВЫЙ ОТЧЁТ")
    print("="*60)

    for model_type, success in results.items():
        status = "✅ УСПЕШНО" if success else "❌ ПРОВАЛЕНО"
        print(f"{model_type.upper():15} {status}")

    all_passed = all(results.values())

    print("="*60)
    if all_passed:
        print("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ!")
    else:
        print("⚠️  НЕКОТОРЫЕ ТЕСТЫ ПРОВАЛЕНЫ")
    print("="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
