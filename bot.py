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

# إعداد الذكاء الاصطناعي (تم تحديث النموذج إلى 2.5-flash)
try:
    genai.configure(api_key=GEMINI_API_KEY)
    ai_model = genai.GenerativeModel('gemini-2.5-flash')
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
    """القائمة الرئيسية مع كل الأزرار"""
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
    # تصفير حالة الذكاء الاصطناعي عند بدء البوت
    context.user_data['in_ai_mode'] = False
    
    await update.message.reply_text(
        "⚽ أهلاً بك في بوت كورة لايف!\n\n"
        "اختر الدوري الذي تريد معرفة مبارياته اليوم، أو اضغط على (Live).\n"
        "💡 يمكنك التحدث مع الذكاء الاصطناعي بالضغط على الزر المخصص.",
        reply_markup=get_main_menu()
    )

# ================= دوال الذكاء الاصطناعي =================
async def start_ai_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عند الضغط على زر التحدث مع الذكاء الاصطناعي"""
    query = update.callback_query
    await query.answer()
    
    context.user_data['in_ai_mode'] = True
    
    keyboard = [[InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="BACK")]]
    
    await query.edit_message_text(
        "🤖 *أهلاً بك في قسم الذكاء الاصطناعي!*\n\n"
        "أنا خبير في كرة القدم. يمكنك سؤالي أي شيء الآن.\n"
        "أرسل سؤالك كرسالة نصية وسأجيبك فوراً.\n\n"
        "_(للعودة، اضغط على زر العودة بالأسفل)_",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def ai_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """التعامل مع الرسائل النصية عندما يكون المستخدم في وضع الذكاء الاصطناعي"""
    if not context.user_data.get('in_ai_mode', False):
        return
    
    user_message = update.message.text
    wait_message = await update.message.reply_text("🤖 جاري التفكير...")
    
    try:
        prompt = f"أنت خبير ومحلل رياضي في كرة القدم. أجب على السؤال التالي بإيجاز وباللغة العربية: {user_message}"
        response = ai_model.generate_content(prompt)
        
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

            text += f"🆚 {home} {result} {away}\n{status_icon}\n------------------------\n"
        
        keyboard = [[InlineKeyboardButton("🔙 العودة للدوريات", callback_data="BACK"), InlineKeyboardButton("🚪 خروج", callback_data="EXIT")]]
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

    except Exception as e:
        await query.edit_message_text(
            f"❌ حدث خطأ.\nالخطأ: {str(e)}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 العودة", callback_data="BACK")]])
        )

async def live_matches(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['in_ai_mode'] = False
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text("⏳ جاري البحث عن المباريات الجارية الآن...")

    today = datetime.now().strftime("%Y-%m-%d")
    url = f"https://api.football-data.org/v4/matches?dateFrom={today}&dateTo={today}"
    headers = {"X-Auth-Token": FOOTBALL_API_KEY}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        matches = data.get("matches", [])
        
        live_matches_list = [m for m in matches if m["status"] in ["IN_PLAY", "PAUSED"]]
        
        if not live_matches_list:
            await query.edit_message_text(
                "😴 لا توجد مباريات تُلعب حالياً في الدوريات المتاحة.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 العودة", callback_data="BACK")]])
            )
            return

        text = "🔴 *المباريات الجارية الآن:*\n\n"
        for match in live_matches_list:
            home = match["homeTeam"]["name"] or match["homeTeam"]["shortName"]
            away = match["awayTeam"]["name"] or match["awayTeam"]["shortName"]
            score_home = match["score"]["fullTime"]["home"] or 0
            score_away = match["score"]["fullTime"]["away"] or 0
            comp = match["competition"]["name"]
            
            text += f"🏆 {comp}\n"
            text += f"🆚 {home} *{score_home} - {score_away}* {away}\n"
            
            search_query = f"بث مباشر {home} ضد {away}"
            search_url = f"https://www.google.com/search?q={requests.utils.quote(search_query)}"
            
            text += f"🔗 [اضغط هنا للبحث عن البث]({search_url})\n"
            text += "------------------------\n"
        
        keyboard = [[InlineKeyboardButton("🔙 العودة للقائمة", callback_data="BACK"), InlineKeyboardButton("🚪 خروج", callback_data="EXIT")]]
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard), disable_web_page_preview=True)

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
    
    # معالجات الأزرار
    application.add_handler(CallbackQueryHandler(start_ai_chat, pattern="^AI_CHAT$"))
    application.add_handler(CallbackQueryHandler(live_matches, pattern="^LIVE_NOW$"))
    application.add_handler(CallbackQueryHandler(league_matches, pattern="^(PL|PD|SA|BL1|FL1|CL)$"))
    application.add_handler(CallbackQueryHandler(back_to_menu, pattern="^BACK$"))
    application.add_handler(CallbackQueryHandler(exit_bot, pattern="^EXIT$"))

    # معالج الذكاء الاصطناعي
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, ai_chat))

    PORT = int(os.environ.get("PORT", 10000))
    if WEBHOOK_URL:
        application.run_webhook(listen="0.0.0.0", port=PORT, url_path="webhook", webhook_url=f"{WEBHOOK_URL}/webhook")
    else:
        application.run_polling()

if __name__ == "__main__":
    main()
