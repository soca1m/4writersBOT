"""
Тестовый скрипт для проверки OpenRouter API ключа
"""
import asyncio
import os
from openai import AsyncOpenAI

# OpenRouter API ключ
OPENROUTER_API_KEY = "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"

async def test_openrouter_key():
    """Тестирует OpenRouter API ключ"""
    print("="*60)
    print("🧪 ТЕСТ OPENROUTER API КЛЮЧА")
    print("="*60)

    # Создаём клиент OpenRouter
    client = AsyncOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=OPENROUTER_API_KEY,
    )

    try:
        print("\n📝 Тест 1: Простой запрос к Claude 3.5 Sonnet...")

        response = await client.chat.completions.create(
            model="anthropic/claude-3.5-sonnet",
            messages=[
                {
                    "role": "user",
                    "content": "Say hello in 5 words or less"
                }
            ],
            max_tokens=50
        )

        result = response.choices[0].message.content
        print(f"✅ Ответ получен: {result}")
        print(f"📊 Модель: {response.model}")
        print(f"🔢 Использовано токенов: {response.usage.total_tokens}")

        print("\n" + "="*60)
        print("🎉 OPENROUTER API КЛЮЧ РАБОТАЕТ!")
        print("="*60)

        return True

    except Exception as e:
        print(f"\n❌ ОШИБКА: {e}")
        print("\n" + "="*60)
        print("⚠️  OPENROUTER API КЛЮЧ НЕ РАБОТАЕТ")
        print("="*60)
        return False


async def test_multiple_models():
    """Тестирует разные модели через OpenRouter"""
    print("\n" + "="*60)
    print("🧪 ТЕСТ РАЗНЫХ МОДЕЛЕЙ")
    print("="*60)

    client = AsyncOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=OPENROUTER_API_KEY,
    )

    models_to_test = [
        "anthropic/claude-3.5-sonnet",
        "openai/gpt-4o-mini",
        "google/gemini-2.0-flash-exp:free",
    ]

    for model in models_to_test:
        try:
            print(f"\n📝 Тестирую {model}...")

            response = await client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "user",
                        "content": "Say 'OK' if you can hear me"
                    }
                ],
                max_tokens=10
            )

            result = response.choices[0].message.content
            tokens = response.usage.total_tokens

            print(f"  ✅ {model}: {result} (токенов: {tokens})")

        except Exception as e:
            print(f"  ❌ {model}: Ошибка - {e}")

    print("\n" + "="*60)


async def main():
    """Главная функция"""
    # Тест 1: Основной тест ключа
    success = await test_openrouter_key()

    if success:
        # Тест 2: Разные модели
        await test_multiple_models()

    print("\n✅ Тестирование завершено!\n")


if __name__ == "__main__":
    asyncio.run(main())
