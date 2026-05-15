"""
المهام المجدولة: تقارير يومية، فحص أسعار، تحديث الرصيد، التحويلات التلقائية
"""
import asyncio
import logging
from datetime import datetime, timezone

from telegram.ext import Application, ContextTypes
from . import config, database as db, usdt, fastcard
from .notify import notify_admin

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# دوال مساعدة داخلية
# ─────────────────────────────────────────────

async def _send_admin(app: Application, text: str) -> None:
    """يرسل رسالة للأدمن عبر البوت."""
    if config.ADMIN_ID:
        try:
            await app.bot.send_message(chat_id=config.ADMIN_ID, text=text, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Failed to send message to admin: {e}")


def _today_iso() -> str:
    """يرجع بداية اليوم الحالي بتوقيت UTC بصيغة ISO."""
    now = datetime.now(timezone.utc)
    return now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()


# ─────────────────────────────────────────────
# تقرير اليوم
# ─────────────────────────────────────────────

async def build_today_report() -> str:
    """يبني تقريراً نصياً بمبيعات اليوم الحالي."""
    since = _today_iso()
    try:
        stats = await asyncio.to_thread(db.get_sales_stats_since, since)
    except Exception as e:
        logger.warning(f"build_today_report: get_sales_stats_since failed: {e}")
        stats = {}

    orders_count  = stats.get("orders_count", 0)
    revenue_syp   = stats.get("revenue_syp", 0) or 0
    cost_usd      = stats.get("cost_usd", 0) or 0
    profit_syp    = stats.get("profit_syp", 0) or 0
    rate          = config.get_usd_to_syp()
    cost_syp      = int(cost_usd * rate)

    lines = [
        "📊 *تقرير اليوم*",
        "━━━━━━━━━━━━━━━━━",
        f"🛒 الطلبات: *{orders_count}*",
        f"💰 الإيرادات: *{revenue_syp:,.0f} ل.س*".replace(",", "،"),
        f"📦 التكلفة: *{cost_syp:,.0f} ل.س* ({cost_usd:.2f}$)".replace(",", "،"),
        f"📈 الربح: *{profit_syp:,.0f} ل.س*".replace(",", "،"),
        f"💱 سعر الصرف: {rate:,.0f} ل.س/$".replace(",", "،"),
    ]
    return "\n".join(lines)


# ─────────────────────────────────────────────
# فحص الأسعار
# ─────────────────────────────────────────────

async def compute_price_check_data() -> dict:
    """
    يقارن أسعار البوت الحالية بتكاليف Fastcard.
    يرجع dict: {ok, loss, thin, ok_items, rate}
    loss  → منتجات نبيعها بأقل من التكلفة
    thin  → منتجات هامش ربحها أقل من 8%
    """
    try:
        offers = await asyncio.to_thread(config.collect_priced_offers)
    except Exception as e:
        return {"ok": False, "error": str(e), "loss": [], "thin": [], "ok_items": []}

    rate = config.get_usd_to_syp()
    loss, thin, ok_items = [], [], []

    overrides = {}
    try:
        overrides = await asyncio.to_thread(db.list_price_overrides)
    except Exception:
        pass

    for item in offers:
        cost_usd = item.get("cost_usd") or 0
        if not cost_usd:
            continue

        offer_id = item.get("id") or ""
        label    = item.get("label", offer_id)
        source   = item.get("source", "")

        cost_syp     = cost_usd * rate
        # السعر الحالي: override أولاً ثم raw_offer
        raw_offer = item.get("raw_offer") or {}
        current_price = overrides.get(offer_id) or config.get_offer_price(raw_offer)

        if current_price <= 0:
            continue

        margin_pct = (current_price - cost_syp) / cost_syp * 100 if cost_syp > 0 else 100
        suggested  = config.round_up_to_500(cost_syp * 1.12)

        entry = {
            "id":            offer_id,
            "label":         label,
            "source":        source,
            "cost_usd":      cost_usd,
            "cost_syp":      int(cost_syp),
            "current_price": current_price,
            "margin_pct":    round(margin_pct, 1),
            "suggested":     suggested,
        }

        if margin_pct < 0:
            loss.append(entry)
        elif margin_pct < 8:
            thin.append(entry)
        else:
            ok_items.append(entry)

    return {"ok": True, "loss": loss, "thin": thin, "ok_items": ok_items, "rate": rate}


def format_price_check_report(check_data: dict) -> str:
    """يحوّل نتيجة compute_price_check_data إلى رسالة Telegram."""
    if not check_data.get("ok"):
        return f"❌ فشل الفحص: {check_data.get('error', 'خطأ غير معروف')}"

    loss     = check_data.get("loss", [])
    thin     = check_data.get("thin", [])
    ok_items = check_data.get("ok_items", [])
    rate     = check_data.get("rate", 0)
    total    = len(loss) + len(thin) + len(ok_items)

    lines = [
        "🔍 *تقرير فحص الأسعار*",
        "━━━━━━━━━━━━━━━━━",
        f"💱 سعر الصرف: {rate:,.0f} ل.س/$".replace(",", "،"),
        f"📦 إجمالي المنتجات المفحوصة: {total}",
        f"🆘 خاسرة: {len(loss)} | ⚠️ هامش ضعيف: {len(thin)} | ✅ سليمة: {len(ok_items)}",
        "",
    ]

    if loss:
        lines.append("🆘 *منتجات خاسرة (السعر أقل من التكلفة):*")
        for e in loss[:15]:
            lines.append(
                f"  • {e['label']} — سعرنا: {e['current_price']:,} | تكلفة: {e['cost_syp']:,} | مقترح: {e['suggested']:,}".replace(",", "،")
            )
        if len(loss) > 15:
            lines.append(f"  _... و{len(loss)-15} منتج آخر_")
        lines.append("")

    if thin:
        lines.append("⚠️ *منتجات هامش ضعيف (< 8%):*")
        for e in thin[:10]:
            lines.append(
                f"  • {e['label']} — هامش: {e['margin_pct']}% | مقترح: {e['suggested']:,}".replace(",", "،")
            )
        if len(thin) > 10:
            lines.append(f"  _... و{len(thin)-10} منتج آخر_")
        lines.append("")

    if not loss and not thin:
        lines.append("✅ *جميع الأسعار ضمن الهامش المطلوب.*")

    return "\n".join(lines)


async def build_price_check_report() -> str:
    """يبني تقرير فحص الأسعار كاملاً (compute + format)."""
    data = await compute_price_check_data()
    return format_price_check_report(data)


async def apply_price_fix(check_data: dict) -> dict:
    """
    يطبّق الأسعار المقترحة على منتجات loss و thin.
    يرجع {applied, skipped, details}
    """
    items  = check_data.get("loss", []) + check_data.get("thin", [])
    applied, skipped, details = 0, 0, []

    for item in items:
        offer_id  = item.get("id", "")
        suggested = item.get("suggested", 0)
        if not offer_id or not suggested:
            skipped += 1
            continue
        try:
            await asyncio.to_thread(db.set_price_override, offer_id, suggested)
            applied += 1
            details.append(
                f"✅ {item['label']}: {item['current_price']:,} → {suggested:,} ل.س".replace(",", "،")
            )
        except Exception as e:
            skipped += 1
            details.append(f"❌ {item.get('label', offer_id)}: {e}")

    return {"applied": applied, "skipped": skipped, "details": details}


# ─────────────────────────────────────────────
# متابعة الطلبات المعلقة
# ─────────────────────────────────────────────

async def check_pending_api_orders(context: ContextTypes.DEFAULT_TYPE) -> None:
    """يتحقق من الطلبات المعلقة عبر Fastcard API ويرسل تأكيداً للمستخدم."""
    try:
        orders = await asyncio.to_thread(db.get_followup_orders, 50)
    except Exception as e:
        logger.error(f"get_followup_orders failed: {e}")
        return

    for order in orders:
        order_id = order.get("id")
        api_uuid = order.get("api_uuid")
        user_id  = order.get("user_id")
        if not api_uuid or not user_id:
            continue

        try:
            info = await asyncio.to_thread(fastcard.check_order, api_uuid, by_uuid=True)
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

        await asyncio.to_thread(db.update_order_api, order_id, status=final_status,
                                api_response=str(info)[:2000])

        try:
            if accepted:
                replay = info.get("replay_api") or []
                code_txt = ""
                if isinstance(replay, list) and replay:
                    val = str(replay[0]).strip()
                    if val:
                        code_txt = f"\n\n\U0001f39f *\u0627\u0644\u0643\u0648\u062f:*\n`{val}`"
                new_bal = ((await asyncio.to_thread(db.get_user, user_id)) or {}).get("balance") or 0
                await context.bot.send_message(
                    user_id,
                    f"\u2705 *\u062a\u0645 \u062a\u0646\u0641\u064a\u0630 \u0637\u0644\u0628\u0643 \u0628\u0646\u062c\u0627\u062d!*\n"
                    f"\U0001f4cb \u0631\u0642\u0645 \u0627\u0644\u0637\u0644\u0628: #{order_id}"
                    f"{code_txt}\n\n"
                    f"\U0001f4bc \u0631\u0635\u064a\u062f\u0643: {new_bal:,.0f} \u0644.\u0633".replace(",", "\u060c"),
                    parse_mode="Markdown",
                )
            else:
                price = order.get("amount") or 0
                if price:
                    await asyncio.to_thread(db.update_balance, user_id, price)
                new_bal = ((await asyncio.to_thread(db.get_user, user_id)) or {}).get("balance") or 0
                await context.bot.send_message(
                    user_id,
                    f"\u274c *\u062a\u0639\u0630\u0651\u0631 \u062a\u0646\u0641\u064a\u0630 \u0627\u0644\u0637\u0644\u0628 \u0648\u062a\u0645 \u0627\u0633\u062a\u0631\u062c\u0627\u0639 \u0627\u0644\u0645\u0628\u0644\u063a.*\n"
                    f"\U0001f4cb \u0631\u0642\u0645 \u0627\u0644\u0637\u0644\u0628: #{order_id}\n"
                    f"\U0001f4bc \u0631\u0635\u064a\u062f\u0643: {new_bal:,.0f} \u0644.\u0633".replace(",", "\u060c"),
                    parse_mode="Markdown",
                )
        except Exception as e:
            logger.warning(f"notify user {user_id} order {order_id}: {e}")


# ─────────────────────────────────────────────
# فحص تحويلات USDT
# ─────────────────────────────────────────────

async def check_usdt_transactions(context: ContextTypes.DEFAULT_TYPE) -> None:
    """يفحص التحويلات الجديدة على محفظة USDT كل دقيقة."""
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
                f"\u2705 *\u062a\u062d\u0648\u064a\u0644 USDT \u062c\u062f\u064a\u062f!*\n\n"
                f"\U0001f4b0 \u0627\u0644\u0645\u0628\u0644\u063a: `{amount_usdt:.2f}` USDT\n"
                f"\U0001f4b5 \u0628\u0627\u0644\u0644\u064a\u0631\u0629: `{amount_syp:,}` \u0644.\u0633\n".replace(",", "\u060c") +
                f"\U0001f4cd \u0645\u0646: `{from_address}`\n"
                f"\U0001f517 [BSCScan](https://bscscan.com/tx/{tx_hash})\n"
            )
            await notify_admin(context.application.bot, message)
    except Exception as e:
        logger.error(f"check_usdt_transactions failed: {e}")


# ─────────────────────────────────────────────
# تسجيل المهام
# ─────────────────────────────────────────────

def schedule_jobs(app: Application) -> None:
    """تسجيل كل المهام المجدولة."""
    jq = app.job_queue

    # فحص تحويلات USDT كل دقيقة
    if usdt.is_enabled():
        jq.run_repeating(
            check_usdt_transactions,
            interval=config.USDT_CHECK_INTERVAL,
            first=5,
            name="check_usdt_transactions",
        )
        logger.info("USDT transaction checker scheduled")

    # متابعة الطلبات المعلقة كل دقيقتين
    jq.run_repeating(
        check_pending_api_orders,
        interval=120,
        first=60,
        name="check_pending_api_orders",
    )

    logger.info("All jobs scheduled successfully")


# compat alias
setup_jobs = schedule_jobs
