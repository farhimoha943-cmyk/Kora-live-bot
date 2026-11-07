import os
import requests
import google.generativeai as genai
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# ================= الإعدادات =================
TELEGRAM_TOKEN = "9139384093:AAGGravTcDX_Xf2DvD8v9yZjDYU7iEadkrw" 
FOOTBALL_API_KEY = "313d3f63571a44f38dd6e08b89de1e6e" 
GEMINI_API_KEY = "AQ.Ab8RN6L9Yat3WRKQSrJJ1fXXT6aZhFfknmTb_cIV1tPJHossyQ" 

WEBHOOK_URL = os.environ.get("WEBHOOK_URL") 
# ==============================================

# إعداد الذكاء الاصطناعي
try:
    genai.configure(api_key=GEMINI_API_KEY)
    ai_model = genai.GenerativeModel('gemini-pro')
except Exception as e:
    print(f"خطأ في إعداد الذكاء الاصطناعي: {e}")

LEAGUES = {
    "PL": {"name": "🏴󠁧󠁢󠁥󠁮󠁧󠁿 الدوري الإنجليزي", "id": "PL"},
    "PD": {"name": "🇪🇸 الدوري الإسباني", "id": "PD"},
    "SA": {"name": "🇮🇹 الدوري الإيطالي", "id": "SA"},
    "BL1": {"name": "🇩🇪 الدوري الألماني", "id": "BL1"},
    "FL1": {"name": "🇫🇷 الدوري الفرنسي", "id": "FL1"},
    "CL": {"name": "🏆 دوري أبطال أوروبا", "id": "CL"}
}

def get_main_menu():
    """القائمة الرئيسية"""
    keyboard = [
        [InlineKeyboardButton("🏴󠁧󠁢󠁥󠁮󠁧󠁿 إنجلترا", callback_data="PL"), InlineKeyboardButton("🇪🇸 إسبانيا", callback_data="PD")],
        [InlineKeyboardButton("🇮🇹 إيطاليا", callback_data="SA"), InlineKeyboardButton("🇩🇪 ألمانيا", callback_data="BL1")],
        [InlineKeyboardButton("🇫🇷 فرنسا", callback_data="FL1"), InlineKeyboardButton("🏆 أبطال أوروبا", callback_data="CL")],
        [InlineKeyboardButton("🔴 مباريات تُلعب الآن (Live)", callback_data="LIVE_NOW")],
        [InlineKeyboardButton("🤖 التحدث مع الذكاء الاصطناعي", callback_data="AI_CHAT")],
        [InlineKeyboardButton("👨‍💻 المطور", url="https://t.me/lou1ii")] 
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['in_ai_mode'] = False
    await update.message.reply_text(
        "⚽ أهلاً بك في بوت كورة لايف!\n\n"
        "اختر الدوري الذي تريد معرفة مبارياته اليوم، أو اضغط على (Live).\n"
        "💡 يمكنك التحدث مع الذكاء الاصطناعي بالضغط على الزر المخصص.",
        reply_markup=get_main_menu()
    )

# ================= دوال الذكاء الاصطناعي =================
async def start_ai_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['in_ai_mode'] = True
    keyboard = [[InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="BACK")]]
    await query.edit_message_text(
        "🤖 *أهلاً بك في قسم الذكاء الاصطناعي!*\n\n"
        "أنا خبير في كرة القدم. أرسل سؤالك كرسالة نصية وسأجيبك فوراً.",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def ai_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get('in_ai_mode', False):
        return
    user_message = update.message.text
    wait_message = await update.message.reply_text("🤖 جاري التفكير...")
    try:
        prompt = f"أنت خبير كرة قدم. أجب بالعربية وبإيجاز شديد: {user_message}"
        response = ai_model.generate_content(prompt, request_options={"timeout": 15})
        if response.text:
            await wait_message.edit_text(
                response.text,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 العودة للقائمة", callback_data="BACK")]])
            )
        else:
            await wait_message.edit_text("❌ لم أتمكن من العثور على إجابة.")
    except Exception as e:
        await wait_message.edit_text(f"❌ عذراً، حدث خطأ.\nالخطأ: {str(e)}")

# ================= دوال كرة القدم =================
async def league_matches(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['in_ai_mode'] = False
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
            await query.edit_message_text("⏳ تم تجاوز الحد المسموح به. انتظر قليلاً.")
            return
        response.raise_for_status()
        data = response.json()
        matches = data.get("matches", [])
        
        if not matches:
            await query.edit_message_text(
                f"📅 لا توجد مباريات اليوم في {league_name}.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 العودة", callback_data="BACK")]])
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

            text += f"🆚 {home} {result} {away}\n{status_icon}\n------------------------\n"
        
        keyboard = [[InlineKeyboardButton("🔙 العودة للدوريات", callback_data="BACK"), InlineKeyboardButton("🚪 خروج", callback_data="EXIT")]]
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

    except Exception as e:
        await query.edit_message_text(f"❌ حدث خطأ.\nالخطأ: {str(e)}")

async def live_matches(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['in_ai_mode'] = False
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text("⏳ جاري البحث في الدوريات الكبرى عن مباريات اليوم...")

    today = datetime.now().strftime("%Y-%m-%d")
    headers = {"X-Auth-Token": FOOTBALL_API_KEY}
    
    # البحث في الدوريات الثلاثة الكبرى لتجنب تجاوز حد الطلبات
    leagues_to_check = ["PL", "PD", "SA"] 
    
    all_matches_today = []
    live_matches_now = []

    try:
        for league_id in leagues_to_check:
            url = f"https://api.football-data.org/v4/competitions/{league_id}/matches?dateFrom={today}&dateTo={today}"
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                matches = data.get("matches", [])
                for match in matches:
                    match['competition_name'] = LEAGUES[league_id]['name']
                    all_matches_today.append(match)
                    if match["status"] in ["IN_PLAY", "PAUSED"]:
                        live_matches_now.append(match)
        
        # 1. عرض المباريات المباشرة
        if live_matches_now:
            text = "🔴 *المباريات الجارية الآن:*\n\n"
            for match in live_matches_now:
                home = match["homeTeam"]["name"] or match["homeTeam"]["shortName"]
                away = match["awayTeam"]["name"] or match["awayTeam"]["shortName"]
                score_home = match["score"]["fullTime"]["home"] or 0
                score_away = match["score"]["fullTime"]["away"] or 0
                comp = match['competition_name']
                
                text += f"🏆 {comp}\n"
                text += f"🆚 {home} *{score_home} - {score_away}* {away}\n"
                
                search_query = f"بث مباشر {home} ضد {away}"
                search_url = f"https://www.google.com/search?q={requests.utils.quote(search_query)}"
                text += f"🔗 [اضغط هنا للبحث عن البث]({search_url})\n"
                text += "------------------------\n"
            
            keyboard = [[InlineKeyboardButton("🔙 العودة للقائمة", callback_data="BACK")]]
            await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard), disable_web_page_preview=True)
        
        # 2. عرض مباريات اليوم (إذا لم توجد مباشرة)
        elif all_matches_today:
            text = "📅 *لا توجد مباريات مباشرة الآن. إليك مباريات اليوم:*\n\n"
            for match in all_matches_today[:10]:
                home = match["homeTeam"]["name"] or match["homeTeam"]["shortName"]
                away = match["awayTeam"]["name"] or match["awayTeam"]["shortName"]
                status = match["status"]
                utc_time = match["utcDate"][11:16]
                comp = match['competition_name']
                
                text += f"🏆 {comp}\n"
                if status == "FINISHED":
                    sh = match["score"]["fullTime"]["home"] or 0
                    sa = match["score"]["fullTime"]["away"] or 0
                    text += f"✅ {home} *{sh} - {sa}* {away}\n"
                else:
                    text += f"🆚 {home} ضد {away}\n🕒 {utc_time}\n"
                text += "------------------------\n"
                
            keyboard = [[InlineKeyboardButton("🔙 العودة للقائمة", callback_data="BACK")]]
            await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
            
        # 3. لا توجد مباريات اليوم
        else:
            await query.edit_message_text(
                "😴 لا توجد أي مباريات اليوم في الدوريات الكبرى.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 العودة", callback_data="BACK")]])
            )

    except Exception as e:
        await query.edit_message_text(f"❌ حدث خطأ: {str(e)}")

async def back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['in_ai_mode'] = False
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "⚽ اختر الدوري أو خيار البث المباشر:", 
        reply_markup=get_main_menu()
    )

async def exit_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['in_ai_mode'] = False
    query = update.callback_query
    await query.answer("تم إغلاق البوت.")
    await query.delete_message()
    await context.bot.send_message(chat_id=query.message.chat_id, text="👋 أرسل /start للبدء من جديد.")

def main():
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    
    application.add_handler(CallbackQueryHandler(start_ai_chat, pattern="^AI_CHAT$"))
    application.add_handler(CallbackQueryHandler(live_matches, pattern="^LIVE_NOW$"))
    application.add_handler(CallbackQueryHandler(league_matches, pattern="^(PL|PD|SA|BL1|FL1|CL)$"))
    application.add_handler(CallbackQueryHandler(back_to_menu, pattern="^BACK$"))
    application.add_handler(CallbackQueryHandler(exit_bot, pattern="^EXIT$"))

    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, ai_chat))

    PORT = int(os.environ.get("PORT", 10000))
    if WEBHOOK_URL:
        application.run_webhook(listen="0.0.0.0", port=PORT, url_path="webhook", webhook_url=f"{WEBHOOK_URL}/webhook")
    else:
        application.run_polling()

if __name__ == "__main__":
    main()
