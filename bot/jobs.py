import logging
  from telegram.ext import Application
  from . import database as db
  from . import fastcard
  from . import config
  from . import notify

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
              info = await __import__('asyncio').get_event_loop().run_in_executor(
                  None, lambda u=api_uuid: fastcard.check_order(u, by_uuid=True)
              )
          except Exception as e:
              logger.warning(f"Fastcard check_order failed for order {order_id}: {e}")
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
                          code_txt = f"\n\nU0001f39f️ *الكود:*\n`{val}`"
                  new_user = db.get_user(user_id)
                  bal = (new_user.get("balance") or 0)
                  await context.bot.send_message(
                      user_id,
                      f"✅ *تم تنفيذ طلبك بنجاح!*\n"
                      f"📋 رقم الطلب: #{order_id}"
                      f"{code_txt}\n\n"
                      f"💼 رصيدك الحالي: {bal:,.0f} ل.س".replace(",", "،"),
                      parse_mode="Markdown",
                  )
              else:
                  price = order.get("amount") or 0
                  if price:
                      db.update_balance(user_id, price)
                  new_user = db.get_user(user_id)
                  bal = (new_user.get("balance") or 0)
                  await context.bot.send_message(
                      user_id,
                      f"❌ *تعذّر تنفيذ الطلب وتم استرجاع المبلغ.*\n"
                      f"📋 رقم الطلب: #{order_id}\n"
                      f"💼 رصيدك الحالي: {bal:,.0f} ل.س".replace(",", "،"),
                      parse_mode="Markdown",
                  )
          except Exception as e:
              logger.warning(f"Failed to notify user {user_id} for order {order_id}: {e}")


  def setup_jobs(application: Application):
      jq = application.job_queue
      # فحص الطلبات المعلقة كل دقيقتين
      jq.run_repeating(check_pending_api_orders, interval=120, first=60, name="check_pending_api_orders")
  