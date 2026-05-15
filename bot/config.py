"""
إعدادات البوت - كل الإعدادات الحساسة تأتي من متغيرات البيئة (Secrets)
"""
import os

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")

ADMIN_ID_RAW = os.environ.get("ADMIN_ID", "0")
try:
    ADMIN_ID = int(ADMIN_ID_RAW)
except (ValueError, TypeError):
    ADMIN_ID = 0

ADMIN_CHANNEL = os.environ.get("ADMIN_CHANNEL", "")

DB_PATH = os.environ.get("DB_PATH", "bot/database.db")

SYRIATEL_CASH_NUMBER = "0982493924"

SHAMCASH_WALLET_CODE = "2ddc70bf6636ab6fc783f957e2fa5d81"
SHAMCASH_WALLET_NAME = "قيس ربيع جمول"

SUPPORT_USERNAME = "@Hamzaalshomari"

REFERRAL_SIGNUP_BONUS = 2000
REFERRAL_COMMISSION_PERCENT = 8

# نظام نقاط الولاء
# كل طلب ناجح = 1% من قيمته نقاط (1 نقطة = 1 ل.س)
# الزبون يستبدل نقاطه برصيد لما يجمع 1000 نقطة على الأقل
LOYALTY_EARN_PERCENT = 1.0          # نسبة كسب النقاط من قيمة الطلب
LOYALTY_REDEEM_RATE = 1             # 1 نقطة = 1 ل.س
LOYALTY_MIN_REDEEM = 1000           # أقل عدد نقاط قابل للاستبدال

# ===== كوبونات تلقائية دورية =====
# البوت يولّد كوبون جديد كل X يوم، صالح لـ Y زبائن، بقيمة Z ل.س ثابتة
AUTO_COUPON_ENABLED = True          # تفعيل/تعطيل التوليد التلقائي
AUTO_COUPON_INTERVAL_DAYS = 10      # كل كم يوم نولّد كوبون جديد
AUTO_COUPON_MAX_USES = 10           # عدد الزبائن المسموح لهم استخدامه
AUTO_COUPON_VALUE_SYP = 5000        # قيمة الكوبون بالليرة السورية (نوع fixed)
AUTO_COUPON_BROADCAST = False       # لا نرسل إعلان للزبائن — الأدمن فقط يستلم الكود وينشره يدوياً

LEVELS = [
    ("🥉 برونزي", 0, 4999),
    ("🥈 فضي", 5000, 14999),
    ("🥇 ذهبي", 15000, 49999),
    ("💎 بلاتيني", 50000, 149999),
    ("💠 ماسي", 150000, 499999),
    ("👑 VIP", 500000, 1499999),
    ("🏆 ملكي", 1500000, float("inf")),
]

# ===== أسعار الصرف =====
# القيم الافتراضية تُستخدم فقط لو الأدمن لم يضبط القيم من لوحة التحكم.
# الأدمن يقدر يعدّل القيم من /admin → 💱 سعر الصرف وتنطبق فوراً على كل العروض.

# سعر تسعير العروض: السعر النهائي = cost_usd × DEFAULT_SYP_PER_USD مدور لـ 500
DEFAULT_SYP_PER_USD = 14700

# سعر تحويل شحن شام كاش دولار → رصيد ل.س
DEFAULT_USD_TO_SYP = float(os.environ.get("USD_TO_SYP", "13100"))


def get_syp_per_usd() -> float:
    """سعر صرف الدولار المستخدم في تسعير العروض. يُقرأ من DB إذا تم ضبطه من لوحة الأدمن."""
    try:
        from . import database as _db
        val = _db.get_setting("syp_per_usd")
        if val:
            return float(val)
    except Exception:
        pass
    return float(DEFAULT_SYP_PER_USD)


def get_usd_to_syp() -> float:
    """سعر تحويل شحن شام كاش دولار → رصيد ل.س. يُقرأ من DB إذا تم ضبطه."""
    try:
        from . import database as _db
        val = _db.get_setting("usd_to_syp")
        if val:
            return float(val)
    except Exception:
        pass
    return float(DEFAULT_USD_TO_SYP)


def round_up_to_500(amount: float) -> int:
    """يدور المبلغ لأعلى لأقرب 500 ل.س."""
    if amount <= 0:
        return 0
    return int(((amount + 499) // 500) * 500)


PRICING_BASE_RATE = 14700  # سعر الصرف المرجعي الذي حُسبت عليه أسعار العروض الأصلية
PRICING_BASE_MARGIN = 0.12  # هامش الربح الأصلي المدمج في أسعار config
PROFIT_MARGIN = 0.05  # هامش الربح الحالي المطبّق على كل العروض


def get_offer_price(offer: dict) -> int:
    """يرجع سعر العرض بالليرة السورية.

    أولوية الحساب:
    1. لو عند الأدمن سعر يدوي محفوظ في DB لهذا العرض → نستخدمه (override).
    2. لو ما فيه `cost_usd` (رصيد محلي بل.س) → السعر ثابت من config.
    3. غير ذلك → نحسب: qty × cost_usd × rate × (1 + PROFIT_MARGIN) مدور لأقرب 500 ل.س.
    """
    # 1) فحص override يدوي من DB
    offer_id = offer.get("id")
    if offer_id:
        try:
            from . import database as _db
            ov = _db.get_price_override(str(offer_id))
            if ov is not None and ov > 0:
                return int(ov)
        except Exception:
            pass

    base_price = int(offer.get("price", 0) or 0)
    if base_price <= 0:
        return 0
    # 2) العروض اللي مالها علاقة بالدولار → سعر ثابت
    cost_usd = offer.get("cost_usd")
    if not cost_usd:
        return base_price
    # 3) العروض المرتبطة بالدولار → نحسب من cost_usd مع هامش الربح الحالي
    qty = offer.get("qty", 1) or 1
    current_rate = get_syp_per_usd()
    cost_syp = float(cost_usd) * qty * current_rate
    return round_up_to_500(cost_syp * (1 + PROFIT_MARGIN))


# ===== خريطة كل أقسام المنتجات للوحة تعديل الأسعار =====
# (مفتاح_القسم, اسم_القائمة_في_config, العنوان_للعرض)
PRICE_EDIT_CATEGORIES = [
    ("pubg_uc",     "PUBG_UC_OFFERS",          "🪙 ببجي - شدات UC"),
    ("pubg_mem",    "PUBG_MEMBERSHIPS",        "👑 ببجي - عضويات"),
    ("pubg_codes",  "PUBG_CODES",              "🎟️ ببجي - أكواد شدات"),
    ("ff_dia",      "FREEFIRE_DIAMOND_OFFERS", "💎 فري فاير - جواهر"),
    ("ff_mem",      "FREEFIRE_MEMBERSHIPS",    "👑 فري فاير - عضويات"),
    ("ff_codes",    "FREEFIRE_CODES",          "🎟️ فري فاير - أكواد جواهر"),
    ("brawl",       "BRAWL_STARS_OFFERS",      "⭐ Brawl Stars"),
    ("coc",         "CLASH_OF_CLANS_OFFERS",   "🏰 Clash of Clans"),
    ("cor",         "CLASH_ROYALE_OFFERS",     "👑 Clash Royale"),
    ("hayday",      "HAY_DAY_OFFERS",          "🌾 Hay Day"),
    ("cod",         "COD_OFFERS",              "🔫 Call of Duty"),
    ("cod_pass",    "COD_PASS_OFFERS",         "🎟️ COD Battle Pass"),
    ("delta",       "DELTA_FORCE_OFFERS",      "💥 Delta Force"),
    ("minecraft",   "MINECRAFT_OFFERS",        "⛏️ Minecraft"),
    ("fortnite",    "FORTNITE_OFFERS",         "🎯 Fortnite"),
    ("ludo_w",      "LUDO_WORLD_OFFERS",       "🎲 Ludo World"),
    ("ludo_c",      "LUDO_CLUB_OFFERS",        "🎲 Ludo Club"),
    ("ludo_y",      "LUDO_YALLA_OFFERS",       "🎲 Ludo Yalla"),
    ("shahid",      "SHAHID_OFFERS",           "📺 Shahid"),
    ("youtube",     "YOUTUBE_OFFERS",          "▶️ YouTube"),
    ("anghami",     "ANGHAMI_OFFERS",          "🎵 Anghami"),
    ("osn",         "OSN_OFFERS",              "📺 OSN+"),
    ("chatgpt",     "CHATGPT_OFFERS",          "🤖 ChatGPT"),
    ("canva",       "CANVA_OFFERS",            "🎨 Canva"),
    ("snapchat",    "SNAPCHAT_OFFERS",         "👻 Snapchat"),
    ("nordvpn",     "NORDVPN_OFFERS",          "🛡️ NordVPN"),
    ("expressvpn",  "EXPRESSVPN_OFFERS",       "🛡️ ExpressVPN"),
    ("lagofast",    "LAGOFAST_OFFERS",         "⚡ LagoFast"),
    ("gearup",      "GEARUP_OFFERS",           "⚡ GearUP"),
    ("tgboost",     "TGBOOST_OFFERS",          "🚀 Telegram Boost"),
    ("visa",        "VISA_OFFERS",             "💳 Visa"),
    ("psn_us",      "PSN_US_OFFERS",           "🎮 PSN (US)"),
    ("psn_sa",      "PSN_SA_OFFERS",           "🎮 PSN (SA)"),
    ("psn_lb",      "PSN_LB_OFFERS",           "🎮 PSN (LB)"),
    ("psn_ae",      "PSN_AE_OFFERS",           "🎮 PSN (AE)"),
    ("steam_us",    "STEAM_US_OFFERS",         "🟦 Steam (US)"),
    ("steam_sa",    "STEAM_SA_OFFERS",         "🟦 Steam (SA)"),
    ("steam_tr",    "STEAM_TR_OFFERS",         "🟦 Steam (TR)"),
    ("itunes_us",   "ITUNES_US_OFFERS",        "🍎 iTunes (US)"),
    ("itunes_sa",   "ITUNES_SA_OFFERS",        "🍎 iTunes (SA)"),
    ("itunes_uk",   "ITUNES_UK_OFFERS",        "🍎 iTunes (UK)"),
    ("gplay_us",    "GPLAY_US_OFFERS",         "🤖 Google Play (US)"),
    ("gplay_sa",    "GPLAY_SA_OFFERS",         "🤖 Google Play (SA)"),
    ("gplay_tr",    "GPLAY_TR_OFFERS",         "🤖 Google Play (TR)"),
    ("xbox_us",     "XBOX_US_OFFERS",          "🟩 Xbox (US)"),
    ("xbox_sa",     "XBOX_SA_OFFERS",          "🟩 Xbox (SA)"),
    ("razer_gl",    "RAZER_GL_OFFERS",         "💚 Razer Gold (Global)"),
    ("razer_us",    "RAZER_US_OFFERS",         "💚 Razer Gold (US)"),
    ("razer_tr",    "RAZER_TR_OFFERS",         "💚 Razer Gold (TR)"),
    ("nintendo",    "NINTENDO_OFFERS",         "🎮 Nintendo"),
    ("netflix",     "NETFLIX_OFFERS",          "🎬 Netflix"),
    ("syr_bal",     "SYRIATEL_BALANCE_OFFERS", "📲 رصيد سيريتل"),
    ("syr_gas",     "SYRIATEL_GAS_OFFERS",     "🔥 سيريتل غاز"),
    ("syr_faw",     "SYRIATEL_FAWATEER_OFFERS","🧾 سيريتل فواتير"),
    ("syr_cash",    "SYRIATEL_CASH_OFFERS",    "💵 سيريتل كاش"),
    ("mtn_bal",     "MTN_BALANCE_OFFERS",      "📲 رصيد MTN"),
    ("mtn_gas",     "MTN_GAS_OFFERS",          "🔥 MTN غاز"),
    ("mtn_faw",     "MTN_FAWATEER_OFFERS",     "🧾 MTN فواتير"),
    ("mtn_cash",    "MTN_CASH_OFFERS",         "💵 MTN كاش"),
    ("sham_bal",    "SHAMCASH_BAL_OFFERS",     "💳 شام كاش"),
    ("payeer",      "PAYEER_OFFERS",           "💰 Payeer"),
    ("pm",          "PERFECTMONEY_OFFERS",     "💰 Perfect Money"),
    ("payoneer",    "PAYONEER_OFFERS",         "💰 Payoneer"),
    ("cliq_jo",     "CLIQ_JORDAN_OFFERS",      "💰 CliQ الأردن"),
    ("usdt_trc",    "USDT_TRC20_OFFERS",       "₮ USDT TRC20"),
    ("usdt_bep",    "USDT_BEP20_OFFERS",       "₮ USDT BEP20"),
    ("touch",       "TOUCH_OFFERS",            "📲 Touch (لبنان)"),
    ("alfa",        "ALFA_OFFERS",             "📲 Alfa (لبنان)"),
    ("whish",       "WHISH_OFFERS",            "💵 Whish (لبنان)"),
    ("asiacell",    "ASIACELL_OFFERS",         "📲 آسياسيل (العراق)"),
    ("zain_iq",     "ZAIN_IRAQ_OFFERS",        "📲 زين (العراق)"),
    ("turkcell",    "TURKCELL_OFFERS",         "📲 Turkcell (تركيا)"),
    ("tosla",       "TOSLA_OFFERS",            "💰 Tosla (تركيا)"),
    ("oldubil",     "OLDUBIL_OFFERS",          "💰 Oldubil (تركيا)"),
    ("vodafone",    "VODAFONE_CASH_OFFERS",    "💵 فودافون كاش (مصر)"),
    ("rcell",       "RCELL_OFFERS",            "📲 R Cell"),
    ("selam",       "SELAM_TELECOM_OFFERS",    "📲 Selam Telecom"),
    # خدمات الرشق (SMM)
    ("smm_igf",     "INSTAGRAM_FOLLOWERS",     "📸 رشق متابعين إنستغرام"),
    ("smm_igl",     "INSTAGRAM_LIKES",         "❤️ رشق لايكات إنستغرام"),
    ("smm_igv",     "INSTAGRAM_VIEWS",         "👁️ رشق مشاهدات إنستغرام"),
    ("smm_fbf",     "FACEBOOK_FOLLOWERS",      "👍 رشق متابعين فيسبوك"),
    ("smm_tgv",     "TELEGRAM_VIEWS",          "📊 رشق مشاهدات تلغرام"),
    ("smm_tgr",     "TELEGRAM_REACTIONS",      "💯 رشق تفاعل تلغرام"),
]


def get_price_edit_offers(cat_key: str) -> list:
    """يرجع قائمة العروض لقسم معين من PRICE_EDIT_CATEGORIES."""
    import sys
    for key, attr, _title in PRICE_EDIT_CATEGORIES:
        if key == cat_key:
            return getattr(sys.modules[__name__], attr, []) or []
    return []


def get_price_edit_title(cat_key: str) -> str:
    """يرجع عنوان القسم."""
    for key, _attr, title in PRICE_EDIT_CATEGORIES:
        if key == cat_key:
            return title
    return cat_key


def find_offer_anywhere(offer_id: str):
    """يبحث عن عرض في كل قوائم العروض. يرجع (offer, cat_key) أو (None, None)."""
    if not offer_id:
        return None, None
    import sys
    mod = sys.modules[__name__]
    for key, attr, _title in PRICE_EDIT_CATEGORIES:
        offers = getattr(mod, attr, []) or []
        for o in offers:
            if o.get("id") == offer_id:
                return o, key
    return None, None


def build_cost_map() -> dict:
    """يبني قاموس موحد {label: cost_usd} من كل قوائم العروض في الموديول هذا.
    يستخدم لحساب التكلفة الفعلية للطلبات عند بناء تقارير الأرباح."""
    import sys
    mod = sys.modules[__name__]
    cost_map: dict = {}
    for name in dir(mod):
        if not name.endswith("_OFFERS"):
            continue
        val = getattr(mod, name, None)
        if not isinstance(val, list):
            continue
        for offer in val:
            if not isinstance(offer, dict):
                continue
            label = offer.get("label")
            cost = offer.get("cost_usd")
            if label and cost:
                cost_map[label] = float(cost)
    return cost_map


def collect_priced_offers() -> list:
    """يجمع كل العروض اللي فيها product_id+cost_usd من الموديول.
    يرجع قائمة [{id, product_id, cost_usd, label, source, enabled, raw_offer}].
    """
    import sys
    mod = sys.modules[__name__]
    seen: set = set()  # لتفادي تكرار نفس product_id
    result: list = []

    # 1) كل قوائم _OFFERS و _MEMBERSHIPS و _CODES
    for name in dir(mod):
        if not (name.endswith("_OFFERS") or name.endswith("_MEMBERSHIPS") or name.endswith("_CODES")):
            continue
        val = getattr(mod, name, None)
        if not isinstance(val, list):
            continue
        for offer in val:
            if not isinstance(offer, dict):
                continue
            pid = offer.get("product_id")
            cost = offer.get("cost_usd")
            label = offer.get("label", "?")
            if not pid or not cost:
                continue
            try:
                pid_int = int(pid)
            except (ValueError, TypeError):
                continue
            if pid_int in seen:
                continue
            seen.add(pid_int)
            result.append({
                "id": offer.get("id"),
                "product_id": pid_int,
                "cost_usd": float(cost),
                "label": label,
                "source": name,
                "enabled": offer.get("enabled", True),
                "raw_offer": offer,
            })

    # 2) قوائم Fastcard من FASTCARD_CATEGORIES (offers_attr يشير للقائمة)
    cats = getattr(mod, "FASTCARD_CATEGORIES", {})
    if isinstance(cats, dict):
        for prefix, cat in cats.items():
            attr = cat.get("offers_attr") if isinstance(cat, dict) else None
            if not attr:
                continue
            offers = getattr(mod, attr, None)
            if not isinstance(offers, list):
                continue
            for offer in offers:
                if not isinstance(offer, dict):
                    continue
                pid = offer.get("product_id")
                cost = offer.get("cost_usd")
                label = offer.get("label", "?")
                if not pid or not cost:
                    continue
                try:
                    pid_int = int(pid)
                except (ValueError, TypeError):
                    continue
                if pid_int in seen:
                    continue
                seen.add(pid_int)
                result.append({
                    "id": offer.get("id"),
                    "product_id": pid_int,
                    "cost_usd": float(cost),
                    "label": label,
                    "source": f"FC:{prefix}",
                    "enabled": offer.get("enabled", True),
                    "raw_offer": offer,
                })
    return result


# Backward-compat: ثابت قديم — كل الاستخدامات النشطة استبدلت بـ get_usd_to_syp().
USD_TO_SYP = DEFAULT_USD_TO_SYP

PUBG_UC_OFFERS = [
    {"id": "uc_60",   "label": "60 شدة",   "uc": 60,   "price": 15000,  "product_id": 2832, "cost_usd": 0.902466, "manual_price": True},
    {"id": "uc_325",  "label": "325 شدة",  "uc": 325,  "price": 73500,  "product_id": 2833, "cost_usd": 4.43372, "manual_price": True},
    {"id": "uc_660",  "label": "660 شدة",  "uc": 660,  "price": 146500, "product_id": 2834, "cost_usd": 8.86744, "manual_price": True},
    {"id": "uc_1800", "label": "1800 شدة", "uc": 1800, "price": 365500, "product_id": 2835, "cost_usd": 22.1686, "manual_price": True},
]

# ===== Fastcard / Ahminix Store API =====
FASTCARD_TOKEN = os.environ.get("FASTCARD_TOKEN", "")
FASTCARD_BASE = os.environ.get("FASTCARD_BASE", "https://fastcard1.store/client/api")

# ===== BSCScan API for USDT Wallet Tracking =====
BSCSCAN_API_KEY = os.environ.get("BSCSCAN_API_KEY", "")
USDT_ENABLED = os.environ.get("USDT_ENABLED", "true").lower() == "true"
USDT_CHECK_INTERVAL = int(os.environ.get("USDT_CHECK_INTERVAL", "60"))  # كل دقيقة

# ===== Monitoring / Alerts =====
# تنبيه الأدمن لما رصيد المتجر ينخفض (USD)
LOW_BALANCE_THRESHOLD_USD = float(os.environ.get("LOW_BALANCE_THRESHOLD_USD", "5.0"))
# كل كم ثانية يتفقّد البوت رصيد المتجر
BALANCE_CHECK_INTERVAL = int(os.environ.get("BALANCE_CHECK_INTERVAL", "43200"))  # 12 ساعة
# ساعة إرسال التقرير اليومي (UTC). 21 UTC = منتصف الليل بدمشق
DAILY_REPORT_HOUR_UTC = int(os.environ.get("DAILY_REPORT_HOUR_UTC", "21"))
DAILY_REPORT_MINUTE_UTC = int(os.environ.get("DAILY_REPORT_MINUTE_UTC", "0"))
# ساعة فحص أسعار Fastcard اليومي (UTC). 06 UTC = 9 صباحاً بدمشق
PRICE_CHECK_HOUR_UTC = int(os.environ.get("PRICE_CHECK_HOUR_UTC", "6"))
PRICE_CHECK_MINUTE_UTC = int(os.environ.get("PRICE_CHECK_MINUTE_UTC", "0"))
# مدة الانتظار الإجمالية (ثواني) لـ polling حالة الطلب بعد إنشائه
FASTCARD_POLL_TIMEOUT = int(os.environ.get("FASTCARD_POLL_TIMEOUT", "45"))
FASTCARD_POLL_INTERVAL = int(os.environ.get("FASTCARD_POLL_INTERVAL", "3"))

# ===== Sham Cash Auto Integration =====
# توثيق الـ API: https://shamcash-api.com/docs
SHAMCASH_TOKEN = os.environ.get("SHAMCASH_TOKEN", "")
SHAMCASH_API_URL = os.environ.get("SHAMCASH_API_URL", "https://api.shamcash-api.com/v1")
SHAMCASH_ACCOUNT_ID = os.environ.get("SHAMCASH_ACCOUNT_ID", "")  # اختياري — لو فاضي بنجيب أول حساب active
SHAMCASH_AUTO_VERIFY = os.environ.get("SHAMCASH_AUTO_VERIFY", "true").lower() == "true"
SHAMCASH_VERIFY_WINDOW_MIN = int(os.environ.get("SHAMCASH_VERIFY_WINDOW_MIN", "30"))

# ===== Syriatel Cash Auto Integration =====
# توثيق الـ API: https://api.melchersman.com/syr-cash/api-docs
SYRIATEL_CASH_TOKEN = os.environ.get("SYRIATEL_CASH_TOKEN", "")
SYRIATEL_CASH_API_URL = os.environ.get("SYRIATEL_CASH_API_URL", "https://api.melchersman.com/syr-cash/v1")
SYRIATEL_CASH_AUTO_VERIFY = os.environ.get("SYRIATEL_CASH_AUTO_VERIFY", "true").lower() == "true"


def get_level_for_amount(total_recharged: float) -> str:
    for name, low, high in LEVELS:
        if low <= total_recharged <= high:
            return name
    return "برونزي"



# =============================================================================

  # =============================================================================
  # قوائم العروض — أضف product_id من لوحة Fastcard لكل عرض
  # =============================================================================

  # ───── ببجي موبايل ─────
  PUBG_MEMBERSHIPS: list = []   # عضويات ببجي
  PUBG_CODE_OFFERS: list = []   # أكواد شدات ببجي

  # ───── فري فاير ─────
  FREEFIRE_MEMBERSHIPS: list = []   # عضويات فري فاير
  FREEFIRE_CODE_OFFERS: list = []   # أكواد فري فاير

  # ───── ألعاب Supercell ─────
  BRAWL_STARS_OFFERS:      list = []
  CLASH_OF_CLANS_OFFERS:   list = []
  CLASH_ROYALE_OFFERS:     list = []
  HAY_DAY_OFFERS:          list = []

  # ───── كول أوف ديوتي ─────
  COD_OFFERS:  list = []   # شدات COD
  COD_BP_OFFERS: list = []  # Battle Pass

  # ───── ألعاب أخرى ─────
  DELTA_FORCE_OFFERS: list = []
  MINECRAFT_OFFERS:   list = []
  FORTNITE_OFFERS:    list = []

  # ───── ألعاب لودو ─────
  LUDO_WORLD_OFFERS:  list = []
  LUDO_CLUB_OFFERS:   list = []
  YALLA_LUDO_OFFERS:  list = []

  # ───── بطاقات ─────
  NINTENDO_US_OFFERS: list = []
  NETFLIX_OFFERS:     list = []
  VISA_OFFERS:        list = []
  PSN_US_OFFERS: list = []
  PSN_SA_OFFERS: list = []
  PSN_LB_OFFERS: list = []
  PSN_AE_OFFERS: list = []
  STEAM_US_OFFERS: list = []
  STEAM_SA_OFFERS: list = []
  STEAM_TR_OFFERS: list = []
  ITUNES_US_OFFERS: list = []
  ITUNES_SA_OFFERS: list = []
  ITUNES_UK_OFFERS: list = []
  GPLAY_US_OFFERS: list = []
  GPLAY_SA_OFFERS: list = []
  GPLAY_TR_OFFERS: list = []
  XBOX_US_OFFERS: list = []
  XBOX_SA_OFFERS: list = []
  RAZER_GL_OFFERS: list = []
  RAZER_US_OFFERS: list = []
  RAZER_TR_OFFERS: list = []

  # ───── اشتراكات ─────
  SHAHID_OFFERS:        list = []
  YOUTUBE_OFFERS:       list = []
  ANGHAMI_OFFERS:       list = []
  OSN_OFFERS:           list = []
  CHATGPT_OFFERS:       list = []
  CANVA_OFFERS:         list = []
  SNAPCHAT_OFFERS:      list = []
  NORDVPN_OFFERS:       list = []
  EXPRESSVPN_OFFERS:    list = []
  LAGOFAST_OFFERS:      list = []
  GEARUP_OFFERS:        list = []
  TELEGRAM_BOOST_OFFERS: list = []

  # ───── خدمات رشق (SMM) ─────
  IGF_OFFERS: list = []   # متابعين انستغرام
  IGL_OFFERS: list = []   # لايكات انستغرام
  IGV_OFFERS: list = []   # مشاهدات انستغرام
  FBF_OFFERS: list = []   # متابعين فيسبوك
  TGV_OFFERS: list = []   # مشاهدات تلغرام
  TGR_OFFERS: list = []   # تفاعل تلغرام


  # =============================================================================
  # FASTCARD_CATEGORIES — المفاتيح مطابقة تماماً لـ handlers_user.py و keyboards.py
  # =============================================================================
  def _f(title, attr, fields=None, back="menu:store"):
      return {"title": title, "offers_attr": attr,
              "input_fields": fields or [], "back_callback": back}

  def _id_f():
      return [{"key": "player_id", "label": "Player ID", "type": "id"}]

  def _sc_f():
      return [{"key": "email", "label": "إيميل Supercell", "type": "text"},
              {"key": "password", "label": "كلمة مرور", "type": "password"}]

  def _cod_f():
      return [{"key": "player_id", "label": "Player ID", "type": "id"},
              {"key": "email", "label": "الإيميل", "type": "text"},
              {"key": "whatsapp", "label": "واتساب", "type": "text"}]

  def _smm_f():
      return [{"key": "link", "label": "رابط الحساب/المنشور", "type": "text"}]

  def _bal(title, product_id="", markup=10, min_a=1000, max_a=5000000, back="store:balance"):
      return {"title": title, "custom_amount": True, "product_id": product_id,
              "markup_pct": markup, "min_amount": min_a, "max_amount": max_a,
              "back_callback": back,
              "input_fields": [{"key": "number", "label": "الرقم / الحساب", "type": "text"}]}

  FASTCARD_CATEGORIES: dict = {
      # ─── ببجي موبايل ───
      "pm":  _f("👑 ببجي — عضويات",       "PUBG_MEMBERSHIPS",   back="store:pubg"),
      "pc":  _f("🎟️ ببجي — أكواد شدات",   "PUBG_CODE_OFFERS",   back="store:pubg"),

      # ─── فري فاير ───
      "fm":  _f("👑 فري فاير — عضويات",   "FREEFIRE_MEMBERSHIPS", back="store:freefire"),
      "fc":  _f("🎟️ فري فاير — أكواد",    "FREEFIRE_CODE_OFFERS", back="store:freefire"),

      # ─── Supercell ───
      "bs":  _f("🎮 Brawl Stars",  "BRAWL_STARS_OFFERS",    fields=_sc_f(), back="store:supercell"),
      "coc": _f("🏰 Clash of Clans","CLASH_OF_CLANS_OFFERS", fields=_sc_f(), back="store:supercell"),
      "cr":  _f("👑 Clash Royale", "CLASH_ROYALE_OFFERS",   fields=_sc_f(), back="store:supercell"),
      "hd":  _f("🌾 Hay Day",      "HAY_DAY_OFFERS",        fields=_sc_f(), back="store:supercell"),

      # ─── كول أوف ديوتي ───
      "cod":  _f("💎 COD — شدات",        "COD_OFFERS",    fields=_cod_f(), back="store:cod"),
      "cdbp": _f("🎫 COD — Battle Pass", "COD_BP_OFFERS", fields=_id_f(),  back="store:cod"),

      # ─── ألعاب أخرى ───
      "df": _f("🪖 Delta Force",  "DELTA_FORCE_OFFERS", fields=_id_f(), back="store:games"),
      "mc": _f("⛏️ Minecraft",    "MINECRAFT_OFFERS",   back="store:games"),
      "fn": _f("🎮 Fortnite",     "FORTNITE_OFFERS",    back="store:games"),

      # ─── لودو ───
      "lw": _f("🎲 Ludo World", "LUDO_WORLD_OFFERS", fields=_id_f(), back="store:ludo"),
      "lc": _f("🎲 Ludo Club",  "LUDO_CLUB_OFFERS",  fields=_id_f(), back="store:ludo"),
      "yl": _f("🎲 Yalla Ludo", "YALLA_LUDO_OFFERS", fields=_id_f(), back="store:ludo"),

      # ─── بطاقات (أكواد جاهزة) ───
      "nt_us": _f("🎮 Nintendo US",     "NINTENDO_US_OFFERS", back="store:cards"),
      "nflx":  _f("📺 Netflix",         "NETFLIX_OFFERS",     back="store:cards"),
      "vs":    _f("💳 VISA",            "VISA_OFFERS",        back="store:cards"),
      "ps_us": _f("🎮 PSN أمريكي",     "PSN_US_OFFERS",      back="cards:psn"),
      "ps_sa": _f("🎮 PSN سعودي",      "PSN_SA_OFFERS",      back="cards:psn"),
      "ps_lb": _f("🎮 PSN لبناني",     "PSN_LB_OFFERS",      back="cards:psn"),
      "ps_ae": _f("🎮 PSN إماراتي",    "PSN_AE_OFFERS",      back="cards:psn"),
      "st_us": _f("🚂 Steam أمريكي",   "STEAM_US_OFFERS",    back="cards:steam"),
      "st_sa": _f("🚂 Steam سعودي",    "STEAM_SA_OFFERS",    back="cards:steam"),
      "st_tr": _f("🚂 Steam تركي",     "STEAM_TR_OFFERS",    back="cards:steam"),
      "it_us": _f("🍎 iTunes أمريكي",  "ITUNES_US_OFFERS",   back="cards:itunes"),
      "it_sa": _f("🍎 iTunes سعودي",   "ITUNES_SA_OFFERS",   back="cards:itunes"),
      "it_uk": _f("🍎 iTunes بريطاني", "ITUNES_UK_OFFERS",   back="cards:itunes"),
      "gp_us": _f("📱 Google Play US",  "GPLAY_US_OFFERS",    back="cards:gplay"),
      "gp_sa": _f("📱 Google Play SA",  "GPLAY_SA_OFFERS",    back="cards:gplay"),
      "gp_tr": _f("📱 Google Play TR",  "GPLAY_TR_OFFERS",    back="cards:gplay"),
      "xb_us": _f("🎮 Xbox أمريكي",   "XBOX_US_OFFERS",     back="cards:xbox"),
      "xb_sa": _f("🎮 Xbox سعودي",    "XBOX_SA_OFFERS",     back="cards:xbox"),
      "rz_gl": _f("🟢 Razer عالمي",   "RAZER_GL_OFFERS",    back="cards:razer"),
      "rz_us": _f("🟢 Razer أمريكي",  "RAZER_US_OFFERS",    back="cards:razer"),
      "rz_tr": _f("🟢 Razer تركي",    "RAZER_TR_OFFERS",    back="cards:razer"),

      # ─── اشتراكات ───
      "sh":   _f("📺 Shahid VIP",        "SHAHID_OFFERS",        back="store:subs"),
      "yt":   _f("📹 YouTube Premium",   "YOUTUBE_OFFERS",       back="store:subs"),
      "an":   _f("🎵 Anghami Plus",      "ANGHAMI_OFFERS",       back="store:subs"),
      "osn":  _f("🍿 OSN+",             "OSN_OFFERS",           back="store:subs"),
      "gpt":  _f("🤖 ChatGPT Plus",      "CHATGPT_OFFERS",       back="store:subs"),
      "cv":   _f("🎨 Canva Pro",         "CANVA_OFFERS",         back="store:subs"),
      "snap": _f("👻 Snapchat+",         "SNAPCHAT_OFFERS",      back="store:subs"),
      "nv":   _f("🛡️ NordVPN",          "NORDVPN_OFFERS",       back="store:subs"),
      "ev":   _f("🟦 ExpressVPN",        "EXPRESSVPN_OFFERS",    back="store:subs"),
      "lv":   _f("⚡ LagoFast",          "LAGOFAST_OFFERS",      back="store:subs"),
      "gu":   _f("🚀 GearUP Booster",    "GEARUP_OFFERS",        back="store:subs"),
      "tg":   _f("📢 تعزيز تلغرام",     "TELEGRAM_BOOST_OFFERS",back="store:subs"),

      # ─── SMM ───
      "igf": _f("📸 متابعين انستغرام", "IGF_OFFERS", fields=_smm_f(), back="store:smm"),
      "igl": _f("❤️ لايكات انستغرام",  "IGL_OFFERS", fields=_smm_f(), back="store:smm"),
      "igv": _f("👁️ مشاهدات انستغرام", "IGV_OFFERS", fields=_smm_f(), back="store:smm"),
      "fbf": _f("👍 متابعين فيسبوك",   "FBF_OFFERS", fields=_smm_f(), back="store:smm"),
      "tgv": _f("📊 مشاهدات تلغرام",  "TGV_OFFERS", fields=_smm_f(), back="store:smm"),
      "tgr": _f("💯 تفاعل تلغرام",    "TGR_OFFERS", fields=_smm_f(), back="store:smm"),

      # ─── رصيد / تعبئة جوال ───
      "bal_syr":    _bal("📱 رصيد SYRIATEL"),
      "bal_mtn":    _bal("📱 رصيد MTN"),
      "bal_sgas":   _bal("⛽ كازية SYRIATEL"),
      "bal_mgas":   _bal("⛽ كازية MTN"),
      "bal_sfaw":   _bal("🧾 فواتير SYRIATEL"),
      "bal_mfaw":   _bal("🧾 فواتير MTN"),
      "bal_scash":  _bal("💵 SYRIATEL CASH"),
      "bal_mcash":  _bal("💵 MTN CASH"),
      "bal_sham":   _bal("💳 SHAM CASH"),
      "bal_payeer": _bal("🟢 PAYEER"),
      "bal_pm":     _bal("🟡 Perfect Money"),
      "bal_payo":   _bal("🟠 Payoneer"),
      "bal_cliq":   _bal("🏦 CLIQ Jordan"),
      "bal_trc":    _bal("₮ USDT TRC20"),
      "bal_bep":    _bal("₮ USDT BEP20"),
      "bal_touch":  _bal("🇱🇧 Touch"),
      "bal_alfa":   _bal("🇱🇧 Alfa"),
      "bal_whish":  _bal("🇱🇧 Whish Money"),
      "bal_asia":   _bal("🇮🇶 Asia Cell"),
      "bal_zain":   _bal("🇮🇶 Zain Iraq"),
      "bal_turk":   _bal("🇹🇷 Turkcell"),
      "bal_tosla":  _bal("🇹🇷 TOSLA"),
      "bal_oldu":   _bal("🇹🇷 Oldubil"),
      "bal_voda":   _bal("🇪🇬 Vodafone Cash"),
      "bal_rcell":  _bal("📱 R-Cell"),
      "bal_selam":  _bal("📱 Selam Telecom"),
      "bal_papra":  _bal("💳 PAPRA"),
  }


  def get_fastcard_offer(prefix: str, offer_id: str, custom_offer=None):
      """إرجاع بيانات عرض واحد من FASTCARD_CATEGORIES أو custom_offer."""
      import sys
      cat = FASTCARD_CATEGORIES.get(prefix)
      if not cat:
          return None
      if custom_offer:
          return custom_offer
      offers = getattr(sys.modules.get("bot.config", sys.modules[__name__]),
                       cat["offers_attr"], [])
      return next((o for o in offers if o.get("id") == offer_id), None)


  def sanitize_for_storage(data, extra_redact_values=None) -> str:
      """تحويل dict لنص آمن مع إخفاء كلمات المرور."""
      import json
      SENSITIVE = {"password", "pass", "كلمة مرور", "كلمة_مرور"}
      extras = set(extra_redact_values or [])
      if not isinstance(data, dict):
          return str(data)
      out = {}
      for k, v in data.items():
          if k.lower() in SENSITIVE or str(v) in extras:
              out[k] = "***"
          else:
              out[k] = v
      return json.dumps(out, ensure_ascii=False)


  def mask_field_value(key: str, value: str) -> str:
      """إخفاء جزئي لقيمة حساسة (كلمة مرور)."""
      SENSITIVE = {"password", "pass"}
      if key.lower() in SENSITIVE:
          return "***"
      if len(value) > 4:
          return value[:2] + "***" + value[-2:]
      return "***"


  def summarize_fields_for_db(fields: list, user_data: dict) -> str:
      """نص موجز لحقول الطلب يُخزَّن في قاعدة البيانات."""
      parts = []
      for f in fields:
          k = f["key"]
          v = user_data.get(k, "")
          parts.append(f"{f.get('label', k)}: {mask_field_value(k, str(v))}")
      return " | ".join(parts)


  def build_custom_balance_offer(prefix: str, amount: int):
      """بناء عرض مؤقت لأقسام الرصيد المفتوح المبلغ."""
      cat = FASTCARD_CATEGORIES.get(prefix)
      if not cat or not cat.get("custom_amount"):
          return None, "هذا القسم لا يدعم المبالغ المخصصة"
      product_id = cat.get("product_id", "")
      if not product_id:
          return None, "product_id غير مضبوط — أضفه في FASTCARD_CATEGORIES"
      markup = int(cat.get("markup_pct", 10))
      final_price = int(amount * (1 + markup / 100))
      offer = {
          "id": f"custom_{prefix}_{amount}",
          "label": f"{cat['title']} — {amount:,} ل.س".replace(",", "،"),
          "product_id": product_id,
          "price_syp": final_price,
          "quantity": amount,
      }
      return offer, None
  