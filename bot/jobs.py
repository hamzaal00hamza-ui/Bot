import logging
import asyncio
from telegram.ext import Application
from . import database as db
from . import fastcard
from . import config

logger = logging.getLogger(__name__)


async def check_pending_api_orders(context):
    """يتحقق من الطلبات المعلقة عبر Fastcard API ويرسل تأكيداً للمستخدم."""
    try:
        orders = db.get_followup_orders(limit=50)
    except Exception as e:
        logger.error(f"get_followup_orders failed: {e}")
        return

    for order in orders:
        order_id = order.get("id")
        api_uuid = order.get("api_uuid")
        user_id = order.get("user_id")
        if not api_uuid or not user_id:
            continue

        try:
            info = await asyncio.to_thread(
                fastcard.check_order, api_uuid, by_uuid=True
            )
        except Exception as e:
            logger.warning(f"check_order failed for order {order_id}: {e}")
            continue

        if not info:
            continue

        final_status = (info.get("status") or "").lower()
        accepted = final_status in ("accept", "accepted", "completed", "done", "success")
        rejected = final_status in ("reject", "rejected", "fail", "failed", "refund", "refunded", "canceled", "cancelled")

        if not accepted and not rejected:
            continue

        db.update_order_api(order_id, status=final_status, api_response=str(info)[:2000])

        try:
            if accepted:
                replay = info.get("replay_api") or []
                code_txt = ""
                if isinstance(replay, list) and replay:
                    val = str(replay[0]).strip()
                    if val:
                        code_txt = f"\n\n\U0001f39f *\u0627\u0644\u0643\u0648\u062f:*\n`{val}`"
                new_bal = (db.get_user(user_id) or {}).get("balance") or 0
                await context.bot.send_message(
                    user_id,
                    f"\u2705 *\u062a\u0645 \u062a\u0646\u0641\u064a\u0630 \u0637\u0644\u0628\u0643 \u0628\u0646\u062c\u0627\u062d!*\n"
                    f"\U0001f4cb \u0631\u0642\u0645 \u0627\u0644\u0637\u0644\u0628: #{order_id}"
                    f"{code_txt}\n\n"
                    f"\U0001f4bc \u0631\u0635\u064a\u062f\u0643 \u0627\u0644\u062d\u0627\u0644\u064a: {new_bal:,.0f} \u0644.\u0633".replace(",", "\u060c"),
                    parse_mode="Markdown",
                )
            else:
                price = order.get("amount") or 0
                if price:
                    db.update_balance(user_id, price)
                new_bal = (db.get_user(user_id) or {}).get("balance") or 0
                await context.bot.send_message(
                    user_id,
                    f"\u274c *\u062a\u0639\u0630\u0651\u0631 \u062a\u0646\u0641\u064a\u0630 \u0627\u0644\u0637\u0644\u0628 \u0648\u062a\u0645 \u0627\u0633\u062a\u0631\u062c\u0627\u0639 \u0627\u0644\u0645\u0628\u0644\u063a.*\n"
                    f"\U0001f4cb \u0631\u0642\u0645 \u0627\u0644\u0637\u0644\u0628: #{order_id}\n"
                    f"\U0001f4bc \u0631\u0635\u064a\u062f\u0643 \u0627\u0644\u062d\u0627\u0644\u064a: {new_bal:,.0f} \u0644.\u0633".replace(",", "\u060c"),
                    parse_mode="Markdown",
                )
        except Exception as e:
            logger.warning(f"Failed to notify user {user_id} for order {order_id}: {e}")


def setup_jobs(application: Application):
    jq = application.job_queue
    jq.run_repeating(
        check_pending_api_orders,
        interval=120,
        first=60,
        name="check_pending_api_orders",
    )
