from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ConversationHandler, ContextTypes
import mysql.connector

# Conversation states
API_NAME, API_URL, API_KEY = range(3)

# Database connection config
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': 'your_password',
    'database': 'your_database'
}

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Send API Name:")
    return API_NAME

async def get_api_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['api_name'] = update.message.text
    await update.message.reply_text("Send API URL:")
    return API_URL

async def get_api_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['api_url'] = update.message.text
    await update.message.reply_text("Send API Key:")
    return API_KEY

async def get_api_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['api_key'] = update.message.text

    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        sql = "INSERT INTO api_detail (api_name, api_url, api_key, api_code) VALUES (%s, %s, %s, '1')"
        data = (
            context.user_data['api_name'],
            context.user_data['api_url'],
            context.user_data['api_key']
        )
        cursor.execute(sql, data)
        conn.commit()
        await update.message.reply_text("✅ API details added successfully!")
    except mysql.connector.Error as err:
        await update.message.reply_text(f"❌ Error: {err}")
    finally:
        cursor.close()
        conn.close()

    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Cancelled.")
    return ConversationHandler.END

# Telegram bot setup
app = ApplicationBuilder().token("YOUR_TELEGRAM_BOT_TOKEN").build()

conv_handler = ConversationHandler(
    entry_points=[CommandHandler("addapi", start)],
    states={
        API_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_api_name)],
        API_URL: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_api_url)],
        API_KEY: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_api_key)],
    },
    fallbacks=[CommandHandler("cancel", cancel)]
)

app.add_handler(conv_handler)

if __name__ == "__main__":
    app.run_polling()
