import json
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
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

def save_records(records):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=4)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Welcome to the Women's Health Hospital Bot. 🏥\n"
        "Use /units to view hospital units or send a photo of a patient sheet."
    )

async def units_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    records = load_records()
    if not records:
        await update.message.reply_text("No patient records found yet.")
        return

    keyboard = []
    # Assuming records can be structured or mapped to units
    keyboard.append([InlineKeyboardButton("Recent Patients", callback_data="recent_patients")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Please select an option:", reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    # Acknowledge the button click immediately to stop the loading spinner
    await query.answer()
    
    data = query.data
    if data == "recent_patients":
        records = load_records()
        if isinstance(records, dict):
            patients_list = list(records.values())
        else:
            patients_list = records
            
        recent_batch = patients_list[-6:]
        if not recent_batch:
            await query.message.reply_text("No recent patients found.")
            return

        for patient in recent_batch:
            name = patient.get("name", "Unknown")
            unit = patient.get("unit", "N/A")
            diagnosis = patient.get("diagnosis", "N/A")
            notes = patient.get("notes", "N/A")
            
            info_text = (
                f"👤 **Name:** {name}\n"
                f"🏥 **Unit:** {unit}\n"
                f"🩺 **Diagnosis:** {diagnosis}\n"
                f"📝 **Notes:** {notes}"
            )
            photo_id = patient.get("photo_id")
            if photo_id:
                await query.message.reply_photo(photo=photo_id, caption=info_text, parse_mode="Markdown")
            else:
                await query.message.reply_text(info_text, parse_mode="Markdown")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Photo received! Processing record...")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().lower()
    if text == "recent":
        records = load_records()
        if isinstance(records, dict):
            patients_list = list(records.values())
        else:
            patients_list = records
            
        recent_batch = patients_list[-6:]
        if not recent_batch:
            await update.message.reply_text("No patient records found.")
            return

        for patient in recent_batch:
            name = patient.get("name", "Unknown")
            unit = patient.get("unit", "N/A")
            diagnosis = patient.get("diagnosis", "N/A")
            notes = patient.get("notes", "N/A")
            
            info_text = (
                f"👤 **Name:** {name}\n"
                f"🏥 **Unit:** {unit}\n"
                f"🩺 **Diagnosis:** {diagnosis}\n"
                f"📝 **Notes:** {notes}"
            )
            photo_id = patient.get("photo_id")
            if photo_id:
                await update.message.reply_photo(photo=photo_id, caption=info_text, parse_mode="Markdown")
            else:
                await update.message.reply_text(info_text, parse_mode="Markdown")
    else:
        await update.message.reply_text("Send 'recent' to view the latest admissions.")

def main():
    TOKEN = "8880459158:AAEjWeGnEfR6X5EqAtL9bpjdmjYvm2vY8Vo"
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("units", units_menu))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    print("Bot running live...")
    # This clears any webhook conflicts and stops button lag
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
