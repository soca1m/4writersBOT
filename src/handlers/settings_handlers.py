"""
Interactive settings configuration handlers with FSM
"""
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from src.store import get_user_by_chat_id
from src.db.database import get_user_settings, update_criteria, toggle_auto_collect
from src.keyboards.menu import get_settings_menu, get_criteria_menu

router = Router()
logger = logging.getLogger(__name__)


class SettingsStates(StatesGroup):
    """FSM states for settings configuration"""
    waiting_for_price = State()
    waiting_for_pages = State()
    waiting_for_types = State()
    waiting_for_levels = State()
    waiting_for_subjects = State()
    waiting_for_deadline = State()


# Settings callback handlers
@router.callback_query(F.data == "settings_toggle_auto")
async def toggle_auto_collection(callback: CallbackQuery):
    """Toggle auto-collection on/off"""
    chat_id = callback.message.chat.id
    new_state = toggle_auto_collect(chat_id)

    settings = get_user_settings(chat_id)
    max_orders = settings["max_orders"]

    status = "✅ Enabled" if new_state else "❌ Disabled"

    text = "⚙️ <b>Settings</b>\n\n"
    text += f"Auto-Collection: {status}\n"
    text += f"Max Orders: {max_orders}\n"

    await callback.message.edit_text(
        text=text,
        reply_markup=get_settings_menu(new_state)
    )
    await callback.answer(f"Auto-collection {status}")


@router.callback_query(F.data == "settings_criteria")
async def show_criteria_config(callback: CallbackQuery):
    """Show criteria configuration menu"""
    chat_id = callback.message.chat.id
    settings = get_user_settings(chat_id)
    criteria = settings.get("criteria", {})

    text = "🎯 <b>Order Criteria Configuration</b>\n\n"

    if criteria.get("min_price") or criteria.get("max_price"):
        text += f"💵 Price: ${criteria.get('min_price', 0)} - ${criteria.get('max_price', '∞')}\n"

    if criteria.get("min_pages") or criteria.get("max_pages"):
        text += f"📄 Pages: {criteria.get('min_pages', 0)} - {criteria.get('max_pages', '∞')}\n"

    if criteria.get("order_types"):
        text += f"📝 Types: {', '.join(criteria['order_types'])}\n"

    if criteria.get("academic_levels"):
        text += f"🎓 Levels: {', '.join(criteria['academic_levels'])}\n"

    if criteria.get("subjects"):
        text += f"📚 Subjects: {', '.join(criteria['subjects'])}\n"

    if criteria.get("min_deadline_hours"):
        text += f"⏰ Min Deadline: {criteria['min_deadline_hours']}h\n"

    if not any(criteria.values()):
        text += "❌ No criteria set\n"

    text += "\n<i>Click below to configure each criterion:</i>"

    await callback.message.edit_text(
        text=text,
        reply_markup=get_criteria_menu()
    )
    await callback.answer()


@router.callback_query(F.data == "criteria_price")
async def configure_price(callback: CallbackQuery, state: FSMContext):
    """Configure price range"""
    await callback.message.answer(
        "💵 <b>Price Range Configuration</b>\n\n"
        "Send min and max price separated by space.\n"
        "Example: <code>5 20</code>\n\n"
        "Send <code>0 0</code> to clear this filter."
    )
    await state.set_state(SettingsStates.waiting_for_price)
    await callback.answer()


@router.callback_query(F.data == "criteria_pages")
async def configure_pages(callback: CallbackQuery, state: FSMContext):
    """Configure pages range"""
    await callback.message.answer(
        "📄 <b>Pages Configuration</b>\n\n"
        "Send min and max pages separated by space.\n"
        "Example: <code>1 5</code>\n\n"
        "Send <code>0 0</code> to clear this filter."
    )
    await state.set_state(SettingsStates.waiting_for_pages)
    await callback.answer()


@router.callback_query(F.data == "criteria_types")
async def configure_types(callback: CallbackQuery, state: FSMContext):
    """Configure order types"""
    await callback.message.answer(
        "📝 <b>Order Types Configuration</b>\n\n"
        "Send order types separated by commas.\n"
        "Example: <code>Essay, Research Paper, Discussion Board Post</code>\n\n"
        "Common types:\n"
        "• Essay\n"
        "• Research Paper\n"
        "• Discussion Board Post\n"
        "• Coursework\n"
        "• Case Study\n\n"
        "Send <code>clear</code> to remove filter."
    )
    await state.set_state(SettingsStates.waiting_for_types)
    await callback.answer()


@router.callback_query(F.data == "criteria_level")
async def configure_levels(callback: CallbackQuery, state: FSMContext):
    """Configure academic levels"""
    await callback.message.answer(
        "🎓 <b>Academic Levels Configuration</b>\n\n"
        "Send academic levels separated by commas.\n"
        "Example: <code>College, High School</code>\n\n"
        "Common levels:\n"
        "• High School\n"
        "• College\n"
        "• Undergraduate\n"
        "• Master\n"
        "• PhD\n\n"
        "Send <code>clear</code> to remove filter."
    )
    await state.set_state(SettingsStates.waiting_for_levels)
    await callback.answer()


@router.callback_query(F.data == "criteria_subjects")
async def configure_subjects(callback: CallbackQuery, state: FSMContext):
    """Configure subjects"""
    await callback.message.answer(
        "📚 <b>Subjects Configuration</b>\n\n"
        "Send subjects separated by commas.\n"
        "Example: <code>Nursing, History, Psychology</code>\n\n"
        "Send <code>clear</code> to remove filter."
    )
    await state.set_state(SettingsStates.waiting_for_subjects)
    await callback.answer()


@router.callback_query(F.data == "criteria_deadline")
async def configure_deadline(callback: CallbackQuery, state: FSMContext):
    """Configure minimum deadline"""
    await callback.message.answer(
        "⏰ <b>Minimum Deadline Configuration</b>\n\n"
        "Send minimum deadline in hours.\n"
        "Example: <code>12</code> (at least 12 hours remaining)\n\n"
        "Send <code>0</code> to clear this filter."
    )
    await state.set_state(SettingsStates.waiting_for_deadline)
    await callback.answer()


@router.callback_query(F.data == "criteria_clear")
async def clear_all_criteria(callback: CallbackQuery):
    """Clear all criteria"""
    chat_id = callback.message.chat.id

    update_criteria(chat_id, {
        "min_price": None,
        "max_price": None,
        "order_types": [],
        "academic_levels": [],
        "subjects": [],
        "min_pages": None,
        "max_pages": None,
        "min_deadline_hours": None
    })

    await callback.answer("✅ All criteria cleared!")

    # Show updated criteria menu
    await show_criteria_config(callback)


# FSM message handlers
@router.message(SettingsStates.waiting_for_price)
async def process_price(message: Message, state: FSMContext):
    """Process price range input"""
    try:
        parts = message.text.strip().split()
        if len(parts) != 2:
            await message.answer("❌ Invalid format. Send two numbers separated by space (e.g., <code>5 20</code>)")
            return

        min_price = float(parts[0])
        max_price = float(parts[1])

        if min_price == 0 and max_price == 0:
            # Clear filter
            update_criteria(message.chat.id, {"min_price": None, "max_price": None})
            await message.answer("✅ Price filter cleared!")
        else:
            if min_price < 0 or max_price < 0 or min_price > max_price:
                await message.answer("❌ Invalid range. Min must be ≤ Max and both ≥ 0")
                return

            update_criteria(message.chat.id, {"min_price": min_price, "max_price": max_price})
            await message.answer(f"✅ Price range set: ${min_price} - ${max_price}")

        await state.clear()

    except ValueError:
        await message.answer("❌ Invalid numbers. Try again with format: <code>5 20</code>")


@router.message(SettingsStates.waiting_for_pages)
async def process_pages(message: Message, state: FSMContext):
    """Process pages range input"""
    try:
        parts = message.text.strip().split()
        if len(parts) != 2:
            await message.answer("❌ Invalid format. Send two numbers separated by space (e.g., <code>1 5</code>)")
            return

        min_pages = int(parts[0])
        max_pages = int(parts[1])

        if min_pages == 0 and max_pages == 0:
            # Clear filter
            update_criteria(message.chat.id, {"min_pages": None, "max_pages": None})
            await message.answer("✅ Pages filter cleared!")
        else:
            if min_pages < 0 or max_pages < 0 or min_pages > max_pages:
                await message.answer("❌ Invalid range. Min must be ≤ Max and both ≥ 0")
                return

            update_criteria(message.chat.id, {"min_pages": min_pages, "max_pages": max_pages})
            await message.answer(f"✅ Pages range set: {min_pages} - {max_pages}")

        await state.clear()

    except ValueError:
        await message.answer("❌ Invalid numbers. Try again with format: <code>1 5</code>")


@router.message(SettingsStates.waiting_for_types)
async def process_types(message: Message, state: FSMContext):
    """Process order types input"""
    text = message.text.strip()

    if text.lower() == "clear":
        update_criteria(message.chat.id, {"order_types": []})
        await message.answer("✅ Order types filter cleared!")
    else:
        types = [t.strip() for t in text.split(",") if t.strip()]

        if not types:
            await message.answer("❌ No types provided. Try again.")
            return

        update_criteria(message.chat.id, {"order_types": types})
        await message.answer(f"✅ Order types set: {', '.join(types)}")

    await state.clear()


@router.message(SettingsStates.waiting_for_levels)
async def process_levels(message: Message, state: FSMContext):
    """Process academic levels input"""
    text = message.text.strip()

    if text.lower() == "clear":
        update_criteria(message.chat.id, {"academic_levels": []})
        await message.answer("✅ Academic levels filter cleared!")
    else:
        levels = [l.strip() for l in text.split(",") if l.strip()]

        if not levels:
            await message.answer("❌ No levels provided. Try again.")
            return

        update_criteria(message.chat.id, {"academic_levels": levels})
        await message.answer(f"✅ Academic levels set: {', '.join(levels)}")

    await state.clear()


@router.message(SettingsStates.waiting_for_subjects)
async def process_subjects(message: Message, state: FSMContext):
    """Process subjects input"""
    text = message.text.strip()

    if text.lower() == "clear":
        update_criteria(message.chat.id, {"subjects": []})
        await message.answer("✅ Subjects filter cleared!")
    else:
        subjects = [s.strip() for s in text.split(",") if s.strip()]

        if not subjects:
            await message.answer("❌ No subjects provided. Try again.")
            return

        update_criteria(message.chat.id, {"subjects": subjects})
        await message.answer(f"✅ Subjects set: {', '.join(subjects)}")

    await state.clear()


@router.message(SettingsStates.waiting_for_deadline)
async def process_deadline(message: Message, state: FSMContext):
    """Process minimum deadline input"""
    try:
        hours = int(message.text.strip())

        if hours == 0:
            update_criteria(message.chat.id, {"min_deadline_hours": None})
            await message.answer("✅ Deadline filter cleared!")
        else:
            if hours < 0:
                await message.answer("❌ Hours must be ≥ 0")
                return

            update_criteria(message.chat.id, {"min_deadline_hours": hours})
            await message.answer(f"✅ Minimum deadline set: {hours} hours")

        await state.clear()

    except ValueError:
        await message.answer("❌ Invalid number. Send hours as integer (e.g., <code>12</code>)")
