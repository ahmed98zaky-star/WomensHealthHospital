import json
import os
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    MessageHandler,
    CommandHandler,
    CallbackQueryHandler,
    filters,
)

DATA_FILE = "patient_records.json"

def load_records():
    if not os.path.exists(DATA_FILE):
        return {}
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {}

# Add your existing functions (start, units_menu, button_handler, etc.) here...

def main():
    TOKEN = "8880459158:AAEjWeGnEfR6X5EqAtL9bpjdmjYvm2vY8Vo"
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("units", units_menu))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text)
    )

    print("Bot running with clear camera UI hints, dual...")
    
    # This runs polling and clears any hanging webhooks to fix button lag
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
