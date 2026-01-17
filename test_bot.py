"""
Тестовый скрипт для проверки функционала бота
"""
import asyncio
import logging
from py4writers import API
from py4writers.exceptions import NetworkError, AuthenticationError
from envparse import env

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Загружаем переменные окружения
env.read_envfile(".env")

# Тестовые данные из store
TEST_USERS = [
    {"login": "socalm", "password": "milavalerasocalm", "id": 538700366},
    {"login": "jerrynetwork", "password": "Blazikenforever2003", "id": 581757147},
]


async def test_api_connection(user: dict):
    """Тест подключения к API для пользователя"""
    logger.info(f"\n{'='*60}")
    logger.info(f"🧪 Тестирование пользователя: {user['login']}")
    logger.info(f"{'='*60}")

    try:
        # Создаём API клиент с дефолтными настройками
        async with API(login=user["login"], password=user["password"]) as api:
            # Тест 1: Авторизация
            logger.info("📝 Тест 1: Авторизация...")
            await api.login()
            logger.info("✅ Авторизация успешна")

            # Тест 2: Получение заказов
            logger.info("\n📝 Тест 2: Получение доступных заказов...")
            orders = await api.get_orders(page=1, page_size=10)

            if orders is None:
                logger.warning("⚠️  API вернул None")
                return False

            logger.info(f"✅ Получено заказов: {len(orders)}")

            # Вывод информации о первых 3 заказах
            for i, order in enumerate(orders[:3], 1):
                logger.info(f"\n📦 Заказ #{i}:")
                logger.info(f"  ID: {order.order_id}")
                logger.info(f"  Index: {order.order_index}")
                logger.info(f"  Title: {order.title}")
                logger.info(f"  Subject: {order.subject}")
                logger.info(f"  Type: {order.order_type}")
                logger.info(f"  Level: {order.academic_level}")
                logger.info(f"  Pages: {order.pages}")
                logger.info(f"  Deadline: {order.deadline}")
                logger.info(f"  Remaining: {order.remaining}")
                logger.info(f"  Total: ${order.total}")

            # Тест 3: Получение деталей заказа
            if orders and len(orders) > 0:
                logger.info("\n📝 Тест 3: Получение деталей первого заказа...")
                first_order = orders[0]
                try:
                    description = await api.fetch_order_details(
                        order_index=first_order.order_index,
                        is_completed=False
                    )
                    if description:
                        logger.info(f"✅ Описание получено ({len(description)} символов)")
                        logger.info(f"  Первые 100 символов: {description[:100]}...")
                    else:
                        logger.warning("⚠️  Описание пустое или None")
                except Exception as e:
                    logger.error(f"❌ Ошибка при получении деталей: {e}")

            # Тест 4: Получение выполненных заказов
            logger.info("\n📝 Тест 4: Получение выполненных заказов...")
            try:
                completed_orders = await api.get_completed_orders(page=1)
                if completed_orders is None:
                    logger.warning("⚠️  Выполненные заказы: None")
                else:
                    logger.info(f"✅ Получено выполненных заказов: {len(completed_orders)}")

                    # Показываем первый выполненный заказ
                    if completed_orders and len(completed_orders) > 0:
                        comp_order = completed_orders[0]
                        logger.info(f"\n📦 Выполненный заказ:")
                        logger.info(f"  ID: {comp_order.order_id}")
                        logger.info(f"  Title: {comp_order.title}")
                        logger.info(f"  Your Payment: ${comp_order.your_payment}")
                        logger.info(f"  Pages: {comp_order.pages}")
            except Exception as e:
                logger.error(f"❌ Ошибка при получении выполненных заказов: {e}")

            logger.info(f"\n{'='*60}")
            logger.info(f"✅ Все тесты для пользователя {user['login']} пройдены!")
            logger.info(f"{'='*60}\n")
            return True

    except NetworkError as e:
        logger.error(f"⚠️  Сетевая ошибка (таймаут) для {user['login']}: {e}")
        logger.warning("💡 Это нормально - сервер 4writers иногда медленно отвечает. Бот будет повторять попытки.")
        return False
    except AuthenticationError as e:
        logger.error(f"❌ Ошибка авторизации для {user['login']}: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ ОШИБКА при тестировании пользователя {user['login']}: {e}")
        logger.exception(e)
        return False


async def test_bot_imports():
    """Тест импортов бота"""
    logger.info("\n🧪 Тест импортов модулей бота...")

    try:
        from src.config import BOT_TOKEN
        logger.info("✅ src.config импортирован")

        from src.store import get_users, get_user_by_chat_id
        logger.info("✅ src.store импортирован")

        from src.handlers import start, orders
        logger.info("✅ src.handlers импортированы")

        from src.keyboards.order import get_order_keyboard
        logger.info("✅ src.keyboards импортированы")

        from src.services.order_monitor import start_monitoring, format_new_order
        logger.info("✅ src.services импортированы")

        logger.info("✅ Все модули бота импортированы успешно!\n")
        return True

    except Exception as e:
        logger.error(f"❌ Ошибка импорта: {e}")
        logger.exception(e)
        return False


async def main():
    """Главная функция тестирования"""
    logger.info("\n" + "="*60)
    logger.info("🚀 ЗАПУСК ТЕСТОВ БОТА 4WRITERS")
    logger.info("="*60 + "\n")

    # Тест 1: Импорты
    imports_ok = await test_bot_imports()

    if not imports_ok:
        logger.error("❌ Тесты импортов провалены. Остановка.")
        return

    # Тест 2: API для каждого пользователя
    results = []
    for user in TEST_USERS:
        result = await test_api_connection(user)
        results.append((user["login"], result))

        # Пауза между тестами пользователей
        if user != TEST_USERS[-1]:
            logger.info("⏳ Пауза 3 секунды перед следующим тестом...\n")
            await asyncio.sleep(3)

    # Итоговый отчёт
    logger.info("\n" + "="*60)
    logger.info("📊 ИТОГОВЫЙ ОТЧЁТ")
    logger.info("="*60)

    for login, success in results:
        status = "✅ УСПЕШНО" if success else "❌ ПРОВАЛЕНО"
        logger.info(f"{login}: {status}")

    all_passed = all(success for _, success in results)

    logger.info("="*60)
    if all_passed:
        logger.info("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
    else:
        logger.error("⚠️  НЕКОТОРЫЕ ТЕСТЫ ПРОВАЛЕНЫ")
    logger.info("="*60 + "\n")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n⏹ Тестирование прервано пользователем")
    except Exception as e:
        logger.error(f"\n❌ Критическая ошибка: {e}")
        logger.exception(e)
