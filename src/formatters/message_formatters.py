"""
Message Formatters - View Layer (Single Responsibility)
Only responsible for formatting data into user-friendly messages
"""
from py4writers import Order
from typing import List


class OrderFormatter:
    """Format order data into telegram messages"""

    @staticmethod
    def format_order_card(order: Order, index: int = None, prefix: str = "🔔") -> str:
        """
        Format single order as a card

        Args:
            order: Order object
            index: Optional order number in list
            prefix: Emoji prefix

        Returns:
            Formatted HTML string
        """
        title = f"{prefix} <b>Order #{index}</b>" if index else f"{prefix} <b>Order</b>"

        return (
            f"{title}\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🆔 <b>ID:</b> <code>{order.order_id}</code>\n"
            f"📝 <b>Title:</b> <code>{order.title}</code>\n"
            f"📚 <b>Subject:</b> <code>{order.subject}</code>\n"
            f"⌛️ <b>Deadline:</b> <code>{order.remaining}</code>\n"
            f"📄 <b>Type:</b> <code>{order.order_type}</code>\n"
            f"🎓 <b>Level:</b> <code>{order.academic_level}</code>\n"
            f"🖋 <b>Style:</b> <code>{order.style}</code>\n"
            f"📄 <b>Pages:</b> <code>{order.pages}</code>\n"
            f"🔎 <b>Sources:</b> <code>{order.sources}</code>\n"
            f"💵 <b>Total:</b> $<code>{order.total}</code>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )

    @staticmethod
    def format_order_list(orders: List[Order], title: str) -> str:
        """
        Format multiple orders as a compact list

        Args:
            orders: List of orders
            title: List title

        Returns:
            Formatted HTML string
        """
        if not orders:
            return f"{title}\n\n❌ No orders"

        text = f"{title} ({len(orders)})\n\n"
        for idx, order in enumerate(orders, 1):
            text += f"{idx}. <b>{order.title}</b>\n"
            text += f"   💵 ${order.total} | 📄 {order.pages}p | ⏰ {order.remaining}\n"
            text += f"   🆔 #{order.order_index}\n\n"

        return text

    @staticmethod
    def format_statistics(order_stats: dict, workflow_stats: dict) -> str:
        """
        Format statistics message

        Args:
            order_stats: Dict with order counts
            workflow_stats: Dict with workflow stats

        Returns:
            Formatted HTML string
        """
        text = "📊 <b>Full Statistics</b>\n\n"

        text += "━━━ <b>Orders Overview</b> ━━━\n"
        text += f"📋 Active Orders: {order_stats.get('active', 0)}\n"
        text += f"✅ Completed: {order_stats.get('completed', 0)}\n"
        text += f"⏰ Late: {order_stats.get('late', 0)}\n"
        text += f"🔄 Revisions: {order_stats.get('revisions', 0)}\n\n"

        text += "━━━ <b>AI Workflow Stats</b> ━━━\n"
        text += f"🔢 Total Workflows: {workflow_stats['total_workflows']}\n"
        text += f"✅ Completed: {workflow_stats['completed_workflows']}\n"
        text += f"❌ Failed: {workflow_stats['failed_workflows']}\n"
        text += f"📝 Total Words: {workflow_stats['total_words_generated']:,}\n"
        text += f"🤖 Avg AI Score: {workflow_stats['avg_ai_score']:.1f}%\n"

        if workflow_stats.get('last_workflow_at'):
            text += f"\n⏰ Last Workflow: {workflow_stats['last_workflow_at'][:16]}"

        return text

    @staticmethod
    def format_settings(settings: dict) -> str:
        """
        Format settings message

        Args:
            settings: User settings dict

        Returns:
            Formatted HTML string
        """
        auto_enabled = settings["auto_collect_enabled"]
        max_orders = settings["max_orders"]
        criteria = settings.get("criteria", {})

        text = "⚙️ <b>Settings</b>\n\n"
        text += f"Auto-Collection: {'✅ Enabled' if auto_enabled else '❌ Disabled'}\n"
        text += f"Max Orders: {max_orders}\n\n"

        text += "━━━ <b>Criteria</b> ━━━\n"

        if criteria.get("min_price") or criteria.get("max_price"):
            text += f"💵 Price: ${criteria.get('min_price', 0)} - ${criteria.get('max_price', '∞')}\n"

        if criteria.get("min_pages") or criteria.get("max_pages"):
            text += f"📄 Pages: {criteria.get('min_pages', 0)} - {criteria.get('max_pages', '∞')}\n"

        if criteria.get("order_types"):
            types = ', '.join(criteria['order_types'][:3])
            more = f" +{len(criteria['order_types']) - 3}" if len(criteria['order_types']) > 3 else ""
            text += f"📝 Types: {types}{more}\n"

        if criteria.get("academic_levels"):
            levels = ', '.join(criteria['academic_levels'][:3])
            more = f" +{len(criteria['academic_levels']) - 3}" if len(criteria['academic_levels']) > 3 else ""
            text += f"🎓 Levels: {levels}{more}\n"

        if criteria.get("subjects"):
            subjects = ', '.join(criteria['subjects'][:3])
            more = f" +{len(criteria['subjects']) - 3}" if len(criteria['subjects']) > 3 else ""
            text += f"📚 Subjects: {subjects}{more}\n"

        if criteria.get("min_deadline_hours"):
            text += f"⏰ Min Deadline: {criteria['min_deadline_hours']}h\n"

        if not any(criteria.values()):
            text += "❌ No criteria set\n"

        return text
