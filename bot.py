import os
import requests
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# ================= الإعدادات =================
# تم وضع التوكن الخاص بك هنا مباشرة
TELEGRAM_TOKEN = "9139384093:AAGGravTcDX_Xf2DvD8v9yZjDYU7iEadkrw" 

# مفتاح كرة القدم الخاص بك
FOOTBALL_API_KEY = "313d3f63571a44f38dd6e08b89de1e6e" 

# رابط منصة Render (سنضيفه في إعدادات Render)
WEBHOOK_URL = os.environ.get("WEBHOOK_URL") 
# ==============================================

LEAGUES = {
    "PL": {"name": "🏴󠁧󠁢󠁥󠁮󠁧󠁿 الدوري الإنجليزي", "id": "PL"},
    "PD": {"name": "🇪🇸 الدوري الإسباني", "id": "PD"},
    "SA": {"name": "🇮🇹 الدوري الإيطالي", "id": "SA"},
    "BL1": {"name": "🇩🇪 الدوري الألماني", "id": "BL1"},
    "FL1": {"name": "🇫🇷 الدوري الفرنسي", "id": "FL1"},
    "CL": {"name": "🏆 دوري أبطال أوروبا", "id": "CL"}
}

def get_main_menu():
    """إنشاء لوحة الأزرار الرئيسية"""
    keyboard = [
        [InlineKeyboardButton("🏴󠁧󠁢󠁥󠁮󠁧󠁿 إنجلترا", callback_data="PL"), InlineKeyboardButton("🇪🇸 إسبانيا", callback_data="PD")],
        [InlineKeyboardButton("🇮🇹 إيطاليا", callback_data="SA"), InlineKeyboardButton("🇩🇪 ألمانيا", callback_data="BL1")],
        [InlineKeyboardButton("🇫🇷 فرنسا", callback_data="FL1"), InlineKeyboardButton("🏆 أبطال أوروبا", callback_data="CL")],
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "⚽ أهلاً بك في بوت كورة لايف!\n\n"
        "اختر الدوري الذي تريد معرفة مبارياته اليوم:",
        reply_markup=get_main_menu()
    )

async def league_matches(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    league_id = query.data
    league_name = LEAGUES[league_id]["name"]
    
    await query.edit_message_text(text=f"⏳ جاري جلب مباريات {league_name}...")

    today = datetime.now().strftime("%Y-%m-%d")
    url = f"https://api.football-data.org/v4/competitions/{league_id}/matches?dateFrom={today}&dateTo={today}"
    headers = {"X-Auth-Token": FOOTBALL_API_KEY}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 429:
            await query.edit_message_text("⏳ تم تجاوز الحد المسموح به (10 طلبات في الدقيقة). يرجى الانتظار قليلاً.")
            return
            
        response.raise_for_status()
        data = response.json()
        
        matches = data.get("matches", [])
        if not matches:
            await query.edit_message_text(
                f"📅 لا توجد مباريات اليوم في {league_name}.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 العودة للدوريات", callback_data="BACK"), InlineKeyboardButton("🚪 خروج", callback_data="EXIT")]
                ])
            )
            return

        text = f"📅 *مباريات {league_name} اليوم:*\n\n"
        
        for match in matches:
            home = match["homeTeam"]["name"] or match["homeTeam"]["shortName"]
            away = match["awayTeam"]["name"] or match["awayTeam"]["shortName"]
            status = match["status"]
            utc_time = match["utcDate"][11:16]
            
            if status in ["FINISHED", "IN_PLAY", "PAUSED"]:
                score_home = match["score"]["fullTime"]["home"] or 0
                score_away = match["score"]["fullTime"]["away"] or 0
                result = f"*{score_home} - {score_away}*"
                status_icon = "🔴 مباشر" if status in ["IN_PLAY", "PAUSED"] else "✅ انتهت"
            else:
                result = f"🕒 {utc_time}"
                status_icon = "⏳ لم تبدأ"

            text += f"🆚 {home} {result} {away}\n"
            text += f"{status_icon}\n"
            text += "------------------------\n"
        
        keyboard = [
            [InlineKeyboardButton("🔙 العودة للدوريات", callback_data="BACK"), InlineKeyboardButton("🚪 خروج", callback_data="EXIT")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=reply_markup)

    except Exception as e:
        await query.edit_message_text(
            f"❌ حدث خطأ أثناء جلب البيانات.\nالخطأ: {str(e)}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 العودة للدوريات", callback_data="BACK"), InlineKeyboardButton("🚪 خروج", callback_data="EXIT")]
            ])
        )

async def back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "⚽ اختر الدوري الذي تريد معرفة مبارياته اليوم:", 
        reply_markup=get_main_menu()
    )

async def exit_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("تم إغلاق البوت بنجاح. أرسل /start للبدء من جديد.")
    await query.delete_message()
    await context.bot.send_message(
        chat_id=query.message.chat_id,
        text="👋 تم إنهاء الجلسة. إذا أردت استخدام البوت مجدداً، أرسل /start."
    )

def main():
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(league_matches, pattern="^(PL|PD|SA|BL1|FL1|CL)$"))
    application.add_handler(CallbackQueryHandler(back_to_menu, pattern="^BACK$"))
    application.add_handler(CallbackQueryHandler(exit_bot, pattern="^EXIT$"))

    # ================= تشغيل البوت بنظام Webhook =================
    PORT = int(os.environ.get("PORT", 10000))
    
    if WEBHOOK_URL:
        print(f"البوت يعمل الآن بنظام Webhook على المنفذ {PORT}...")
        application.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path="webhook",
            webhook_url=f"{WEBHOOK_URL}/webhook"
        )
    else:
        print("تنبيه: لم يتم تعيين WEBHOOK_URL. البوت سيعمل بنظام Polling.")
        application.run_polling()

if __name__ == "__main__":
    main()
