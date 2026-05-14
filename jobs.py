"""
المهام المجدولة: تقارير يومية، فحص أسعار، تحديث الرصيد، التحويلات التلقائية
"""
import asyncio
import logging
from telegram.ext import Application, ContextTypes
from telegram.constants import ParseMode
from . import config, database as db, usdt, fastcard
from .notify import notify_admin

logger = logging.getLogger(__name__)


async def _send_admin(app: Application, text: str) -> None:
    if config.ADMIN_ID:
        try:
            await app.bot.send_message(chat_id=config.ADMIN_ID, text=text, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Failed to send message to admin: {e}")


async def check_usdt_transactions(context: ContextTypes.DEFAULT_TYPE) -> None:
    if not usdt.is_enabled():
        return
    try:
        new_txs = await usdt.sync_wallet_transactions()
        for tx in new_txs:
            amount_usdt = tx["value"]
            from_address = tx["from"]
            tx_hash = tx["hash"]
            rate = usdt.get_usdt_rate()
            amount_syp = int(amount_usdt * rate)
            message = (
                f"✅ **تحويل USDT جديد!**\n\n"
                f"💰 المبلغ: `{amount_usdt:.2f}` USDT\n"
                f"💵 بالليرة: `{amount_syp:,}` ل.س\n"
                f"📍 من: `{from_address}`\n"
                f"🔗 [عرض على BSCScan](https://bscscan.com/tx/{tx_hash})\n"
            )
            await notify_admin(context.application.bot, message)
            logger.info(f"Notified admin about USDT transaction: {amount_usdt} USDT")
    except Exception as e:
        logger.error(f"check_usdt_transactions failed: {e}")


# ============= متابعة الطلبات المعلقة =============

_ACCEPTED = frozenset(("accept", "accepted", "completed", "done", "success"))
_REJECTED = frozenset(("reject", "rejected", "fail", "failed", "refund", "refunded", "canceled", "cancelled"))


async def check_pending_api_orders(context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    يفحص الطلبات المعلقة عند Fastcard API كل دقيقتين ويرسل التأكيد
    للمستخدم حين تكتمل، أو يسترجع المبلغ حين ترفض.
    """
    if not fastcard.is_enabled():
        return

    try:
        orders = await asyncio.to_thread(db.get_followup_orders, 30)
    except Exception as e:
        logger.error(f"check_pending_api_orders: failed to fetch orders: {e}")
        return

    if not orders:
        return

    bot = context.application.bot
    logger.info(f"check_pending_api_orders: checking {len(orders)} pending order(s)...")

    for order in orders:
        order_id = order["id"]
        user_id = int(order["user_id"])
        api_uuid = order.get("api_uuid")
        item_label = order.get("item") or "—"
        price = float(order.get("price") or 0)
        player_id = order.get("player_id") or "—"
        game = order.get("game") or ""

        if not api_uuid:
            continue

        try:
            info = await asyncio.to_thread(fastcard.check_order, api_uuid, by_uuid=True)
        except fastcard.FastcardError as e:
            logger.warning(f"check_pending_api_orders: order #{order_id} check failed: {e}")
            continue
        except Exception as e:
            logger.warning(f"check_pending_api_orders: order #{order_id} unexpected error: {e}")
            continue

        if not info:
            continue

        status = (info.get("status") or "").lower()

        if status not in _ACCEPTED and status not in _REJECTED:
            continue

        # حدّث الحالة في قاعدة البيانات
        db.update_order_api(order_id, status=status, api_response=config.sanitize_for_storage(info))
        logger.info(f"check_pending_api_orders: order #{order_id} resolved → {status}")

        if status in _ACCEPTED:
            replay = info.get("replay_api") or []
            extra = ""
            if isinstance(replay, list) and replay:
                val = str(replay[0]).strip()
                if val:
                    extra = f"\n📩 رد المتجر: `{val}`"

            new_user = db.get_user(user_id)
            current_balance = float((new_user or {}).get("balance") or 0)

            if game == "PUBG":
                game_line = "\n✨ الشدات أُضيفت على حسابك ببجي مباشرة."
            elif game == "FREEFIRE":
                game_line = "\n✨ الجواهر أُضيفت على حسابك فري فاير مباشرة."
            else:
                game_line = "\n✅ تم تنفيذ الطلب على حسابك مباشرة."

            try:
                await bot.send_message(
                    user_id,
                    f"✅ *تم تنفيذ طلبك بنجاح!*\n\n"
                    f"💎 العرض: {item_label}\n"
                    f"🎮 Player ID: `{player_id}`\n"
                    f"💰 السعر: {price:,.0f} ل.س\n"
                    f"📋 رقم الطلب: #{order_id}\n"
                    f"💼 رصيدك الحالي: {current_balance:,.0f} ل.س"
                    f"{extra}"
                    f"{game_line}",
                    parse_mode=ParseMode.MARKDOWN,
                )
            except Exception as e:
                logger.error(f"failed to notify user {user_id}: {e}")

            # نقاط ولاء + تقييم
            try:
                from .handlers_user import grant_loyalty_for_order, send_rating_prompt
                await grant_loyalty_for_order(bot, user_id, price)
                await send_rating_prompt(bot, user_id, order_id, item_label)
            except Exception as e:
                logger.warning(f"loyalty/rating for order #{order_id} failed: {e}")

            if config.ADMIN_ID:
                try:
                    user_row = db.get_user(user_id) or {}
                    uname = user_row.get("username") or user_row.get("first_name") or str(user_id)
                    await notify_admin(
                        bot,
                        f"💰 *طلب معلق اكتمل* #{order_id}\n\n"
                        f"المستخدم: @{uname} ({user_id})\n"
                        f"اللعبة: {game}\n"
                        f"العرض: {item_label}\n"
                        f"Player ID: `{player_id}`\n"
                        f"الحالة: {status}",
                        parse_mode=ParseMode.MARKDOWN,
                    )
                except Exception:
                    pass

        elif status in _REJECTED:
            try:
                db.update_balance(user_id, price)
            except Exception as e:
                logger.error(f"refund failed for order #{order_id}: {e}")

            try:
                await bot.send_message(
                    user_id,
                    f"❌ *المتجر رفض طلبك وتم استرجاع المبلغ كاملاً.*\n\n"
                    f"📋 رقم الطلب: #{order_id}\n"
                    f"💎 العرض: {item_label}\n"
                    f"💰 المبلغ المسترجع: {price:,.0f} ل.س\n"
                    f"الحالة: {status}\n\n"
                    "تأكد من Player ID وجرّب مرة ثانية، أو تواصل مع الدعم.",
                    parse_mode=ParseMode.MARKDOWN,
                )
            except Exception as e:
                logger.error(f"failed to notify rejection to user {user_id}: {e}")

            if config.ADMIN_ID:
                try:
                    await notify_admin(
                        bot,
                        f"⚠️ *طلب معلق رُفض — تم الاسترجاع* #{order_id}\n\n"
                        f"User: {user_id}\n"
                        f"العرض: {item_label}\n"
                        f"Player ID: `{player_id}`\n"
                        f"الحالة: {status}",
                        parse_mode=ParseMode.MARKDOWN,
                    )
                except Exception:
                    pass


def schedule_jobs(app: Application) -> None:
    """تسجيل كل المهام المجدولة."""
    job_queue = app.job_queue

    if usdt.is_enabled():
        job_queue.run_repeating(
            check_usdt_transactions,
            interval=config.USDT_CHECK_INTERVAL,
            first=5,
            name="check_usdt_transactions",
        )
        logger.info("✅ USDT transaction checker scheduled")

    # ✅ الإصلاح: متابعة الطلبات المعلقة كل دقيقتين
    job_queue.run_repeating(
        check_pending_api_orders,
        interval=120,
        first=30,
        name="check_pending_api
