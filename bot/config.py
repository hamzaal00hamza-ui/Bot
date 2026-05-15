

# =============================================================================
# _DBOfferList — قائمة عروض ديناميكية مدعومة من قاعدة البيانات
# =============================================================================
class _DBOfferList:
    """
    تُستخدم بدلاً من list فارغة.
    عند كل وصول (تكرار / bool / len) تجلب العروض من جدول fc_offers تلقائياً.
    """
    def __init__(self, prefix: str):
        self._prefix = prefix

    def _fetch(self):
        try:
            import bot.database as _db
            return _db.get_fc_offers(self._prefix)
        except Exception:
            return []

    def __iter__(self):
        return iter(self._fetch())

    def __bool__(self):
        return len(self._fetch()) > 0

    def __len__(self):
        return len(self._fetch())

    def __getitem__(self, idx):
        return self._fetch()[idx]


# =============================================================================
# قوائم العروض — تُملأ تلقائياً من DB عبر لوحة الأدمن (/setproduct)
# =============================================================================

# ───── ببجي موبايل ─────
PUBG_MEMBERSHIPS   = _DBOfferList("pm")
PUBG_CODE_OFFERS   = _DBOfferList("pc")

# ───── فري فاير ─────
FREEFIRE_MEMBERSHIPS = _DBOfferList("fm")
FREEFIRE_CODE_OFFERS = _DBOfferList("fc")

# ───── Supercell ─────
BRAWL_STARS_OFFERS    = _DBOfferList("bs")
CLASH_OF_CLANS_OFFERS = _DBOfferList("coc")
CLASH_ROYALE_OFFERS   = _DBOfferList("cr")
HAY_DAY_OFFERS        = _DBOfferList("hd")

# ───── COD ─────
COD_OFFERS    = _DBOfferList("cod")
COD_BP_OFFERS = _DBOfferList("cdbp")

# ───── ألعاب أخرى ─────
DELTA_FORCE_OFFERS = _DBOfferList("df")
MINECRAFT_OFFERS   = _DBOfferList("mc")
FORTNITE_OFFERS    = _DBOfferList("fn")

# ───── لودو ─────
LUDO_WORLD_OFFERS = _DBOfferList("lw")
LUDO_CLUB_OFFERS  = _DBOfferList("lc")
YALLA_LUDO_OFFERS = _DBOfferList("yl")

# ───── بطاقات ─────
NINTENDO_US_OFFERS = _DBOfferList("nt_us")
NETFLIX_OFFERS     = _DBOfferList("nflx")
VISA_OFFERS        = _DBOfferList("vs")
PSN_US_OFFERS = _DBOfferList("ps_us")
PSN_SA_OFFERS = _DBOfferList("ps_sa")
PSN_LB_OFFERS = _DBOfferList("ps_lb")
PSN_AE_OFFERS = _DBOfferList("ps_ae")
STEAM_US_OFFERS = _DBOfferList("st_us")
STEAM_SA_OFFERS = _DBOfferList("st_sa")
STEAM_TR_OFFERS = _DBOfferList("st_tr")
ITUNES_US_OFFERS = _DBOfferList("it_us")
ITUNES_SA_OFFERS = _DBOfferList("it_sa")
ITUNES_UK_OFFERS = _DBOfferList("it_uk")
GPLAY_US_OFFERS = _DBOfferList("gp_us")
GPLAY_SA_OFFERS = _DBOfferList("gp_sa")
GPLAY_TR_OFFERS = _DBOfferList("gp_tr")
XBOX_US_OFFERS  = _DBOfferList("xb_us")
XBOX_SA_OFFERS  = _DBOfferList("xb_sa")
RAZER_GL_OFFERS = _DBOfferList("rz_gl")
RAZER_US_OFFERS = _DBOfferList("rz_us")
RAZER_TR_OFFERS = _DBOfferList("rz_tr")

# ───── اشتراكات ─────
SHAHID_OFFERS         = _DBOfferList("sh")
YOUTUBE_OFFERS        = _DBOfferList("yt")
ANGHAMI_OFFERS        = _DBOfferList("an")
OSN_OFFERS            = _DBOfferList("osn")
CHATGPT_OFFERS        = _DBOfferList("gpt")
CANVA_OFFERS          = _DBOfferList("cv")
SNAPCHAT_OFFERS       = _DBOfferList("snap")
NORDVPN_OFFERS        = _DBOfferList("nv")
EXPRESSVPN_OFFERS     = _DBOfferList("ev")
LAGOFAST_OFFERS       = _DBOfferList("lv")
GEARUP_OFFERS         = _DBOfferList("gu")
TELEGRAM_BOOST_OFFERS = _DBOfferList("tg")

# ───── SMM ─────
IGF_OFFERS = _DBOfferList("igf")
IGL_OFFERS = _DBOfferList("igl")
IGV_OFFERS = _DBOfferList("igv")
FBF_OFFERS = _DBOfferList("fbf")
TGV_OFFERS = _DBOfferList("tgv")
TGR_OFFERS = _DBOfferList("tgr")


# =============================================================================
# FASTCARD_CATEGORIES
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
    "pm":  _f("👑 ببجي — عضويات",        "PUBG_MEMBERSHIPS",     back="store:pubg"),
    "pc":  _f("🎟️ ببجي — أكواد شدات",   "PUBG_CODE_OFFERS",     back="store:pubg"),
    "fm":  _f("👑 فري فاير — عضويات",    "FREEFIRE_MEMBERSHIPS", back="store:freefire"),
    "fc":  _f("🎟️ فري فاير — أكواد",    "FREEFIRE_CODE_OFFERS", back="store:freefire"),
    "bs":  _f("🎮 Brawl Stars",  "BRAWL_STARS_OFFERS",    fields=_sc_f(),  back="store:supercell"),
    "coc": _f("🏰 Clash of Clans","CLASH_OF_CLANS_OFFERS", fields=_sc_f(),  back="store:supercell"),
    "cr":  _f("👑 Clash Royale", "CLASH_ROYALE_OFFERS",   fields=_sc_f(),  back="store:supercell"),
    "hd":  _f("🌾 Hay Day",      "HAY_DAY_OFFERS",        fields=_sc_f(),  back="store:supercell"),
    "cod":  _f("💎 COD — شدات",        "COD_OFFERS",    fields=_cod_f(), back="store:cod"),
    "cdbp": _f("🎫 COD — Battle Pass", "COD_BP_OFFERS", fields=_id_f(),  back="store:cod"),
    "df": _f("🪖 Delta Force",  "DELTA_FORCE_OFFERS", fields=_id_f(), back="store:games"),
    "mc": _f("⛏️ Minecraft",    "MINECRAFT_OFFERS",   back="store:games"),
    "fn": _f("🎮 Fortnite",     "FORTNITE_OFFERS",    back="store:games"),
    "lw": _f("🎲 Ludo World", "LUDO_WORLD_OFFERS", fields=_id_f(), back="store:ludo"),
    "lc": _f("🎲 Ludo Club",  "LUDO_CLUB_OFFERS",  fields=_id_f(), back="store:ludo"),
    "yl": _f("🎲 Yalla Ludo", "YALLA_LUDO_OFFERS", fields=_id_f(), back="store:ludo"),
    "nt_us": _f("🎮 Nintendo US",     "NINTENDO_US_OFFERS", back="store:cards"),
    "nflx":  _f("📺 Netflix",         "NETFLIX_OFFERS",     back="store:cards"),
    "vs":    _f("💳 VISA",            "VISA_OFFERS",        back="store:cards"),
    "ps_us": _f("🎮 PSN أمريكي",     "PSN_US_OFFERS",  back="cards:psn"),
    "ps_sa": _f("🎮 PSN سعودي",      "PSN_SA_OFFERS",  back="cards:psn"),
    "ps_lb": _f("🎮 PSN لبناني",     "PSN_LB_OFFERS",  back="cards:psn"),
    "ps_ae": _f("🎮 PSN إماراتي",    "PSN_AE_OFFERS",  back="cards:psn"),
    "st_us": _f("🚂 Steam أمريكي",   "STEAM_US_OFFERS",  back="cards:steam"),
    "st_sa": _f("🚂 Steam سعودي",    "STEAM_SA_OFFERS",  back="cards:steam"),
    "st_tr": _f("🚂 Steam تركي",     "STEAM_TR_OFFERS",  back="cards:steam"),
    "it_us": _f("🍎 iTunes أمريكي",  "ITUNES_US_OFFERS", back="cards:itunes"),
    "it_sa": _f("🍎 iTunes سعودي",   "ITUNES_SA_OFFERS", back="cards:itunes"),
    "it_uk": _f("🍎 iTunes بريطاني", "ITUNES_UK_OFFERS", back="cards:itunes"),
    "gp_us": _f("📱 Google Play US",  "GPLAY_US_OFFERS",  back="cards:gplay"),
    "gp_sa": _f("📱 Google Play SA",  "GPLAY_SA_OFFERS",  back="cards:gplay"),
    "gp_tr": _f("📱 Google Play TR",  "GPLAY_TR_OFFERS",  back="cards:gplay"),
    "xb_us": _f("🎮 Xbox أمريكي",   "XBOX_US_OFFERS",   back="cards:xbox"),
    "xb_sa": _f("🎮 Xbox سعودي",    "XBOX_SA_OFFERS",   back="cards:xbox"),
    "rz_gl": _f("🟢 Razer عالمي",   "RAZER_GL_OFFERS",  back="cards:razer"),
    "rz_us": _f("🟢 Razer أمريكي",  "RAZER_US_OFFERS",  back="cards:razer"),
    "rz_tr": _f("🟢 Razer تركي",    "RAZER_TR_OFFERS",  back="cards:razer"),
    "sh":   _f("📺 Shahid VIP",       "SHAHID_OFFERS",        back="store:subs"),
    "yt":   _f("📹 YouTube Premium",  "YOUTUBE_OFFERS",       back="store:subs"),
    "an":   _f("🎵 Anghami Plus",     "ANGHAMI_OFFERS",       back="store:subs"),
    "osn":  _f("🍿 OSN+",            "OSN_OFFERS",           back="store:subs"),
    "gpt":  _f("🤖 ChatGPT Plus",     "CHATGPT_OFFERS",       back="store:subs"),
    "cv":   _f("🎨 Canva Pro",        "CANVA_OFFERS",         back="store:subs"),
    "snap": _f("👻 Snapchat+",        "SNAPCHAT_OFFERS",      back="store:subs"),
    "nv":   _f("🛡️ NordVPN",         "NORDVPN_OFFERS",       back="store:subs"),
    "ev":   _f("🟦 ExpressVPN",       "EXPRESSVPN_OFFERS",    back="store:subs"),
    "lv":   _f("⚡ LagoFast",         "LAGOFAST_OFFERS",      back="store:subs"),
    "gu":   _f("🚀 GearUP Booster",   "GEARUP_OFFERS",        back="store:subs"),
    "tg":   _f("📢 تعزيز تلغرام",    "TELEGRAM_BOOST_OFFERS",back="store:subs"),
    "igf": _f("📸 متابعين انستغرام", "IGF_OFFERS", fields=_smm_f(), back="store:smm"),
    "igl": _f("❤️ لايكات انستغرام",  "IGL_OFFERS", fields=_smm_f(), back="store:smm"),
    "igv": _f("👁️ مشاهدات انستغرام", "IGV_OFFERS", fields=_smm_f(), back="store:smm"),
    "fbf": _f("👍 متابعين فيسبوك",   "FBF_OFFERS", fields=_smm_f(), back="store:smm"),
    "tgv": _f("📊 مشاهدات تلغرام",  "TGV_OFFERS", fields=_smm_f(), back="store:smm"),
    "tgr": _f("💯 تفاعل تلغرام",    "TGR_OFFERS", fields=_smm_f(), back="store:smm"),
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
    cat = FASTCARD_CATEGORIES.get(prefix)
    if not cat:
        return None
    if custom_offer:
        return custom_offer
    import sys
    offers = getattr(sys.modules.get("bot.config", sys.modules[__name__]),
                     cat["offers_attr"], [])
    return next((o for o in offers if o.get("id") == offer_id), None)


def sanitize_for_storage(data, extra_redact_values=None) -> str:
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
    SENSITIVE = {"password", "pass"}
    if key.lower() in SENSITIVE:
        return "***"
    if len(value) > 4:
        return value[:2] + "***" + value[-2:]
    return "***"


def summarize_fields_for_db(fields: list, user_data: dict) -> str:
    parts = []
    for f in fields:
        k = f["key"]
        v = user_data.get(k, "")
        parts.append(f"{f.get('label', k)}: {mask_field_value(k, str(v))}")
    return " | ".join(parts)


def build_custom_balance_offer(prefix: str, amount: int):
    cat = FASTCARD_CATEGORIES.get(prefix)
    if not cat or not cat.get("custom_amount"):
        return None, "هذا القسم لا يدعم المبالغ المخصصة"
    product_id = cat.get("product_id", "")
    if not product_id:
        return None, "product_id غير مضبوط — استخدم /setproduct لإضافته"
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
