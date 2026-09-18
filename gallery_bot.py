import json
import os
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
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


# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
  text = (
      "🏥 **Clinic Ward & Patient Bot**\n\n"
      "• Type any **patient name** to search records.\n"
      "• Type /units to view and browse patients by hospital unit."
  )
  await update.message.reply_text(text, parse_mode="Markdown")


# Command to view units list
async def units_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
  keyboard = [
      [
          InlineKeyboardButton("🏥 Unit 1", callback_data="showunit_Unit 1"),
          InlineKeyboardButton("🏥 Unit 2", callback_data="showunit_Unit 2"),
      ],
      [
          InlineKeyboardButton("🏥 Unit 3", callback_data="showunit_Unit 3"),
          InlineKeyboardButton("🏥 Unit 4", callback_data="showunit_Unit 4"),
      ],
      [InlineKeyboardButton("🏥 Unit 5", callback_data="showunit_Unit 5")],
  ]
  await update.message.reply_text(
      "Select a hospital unit to view its assigned patients:",
      reply_markup=InlineKeyboardMarkup(keyboard),
  )


# Helper to show patient card AND automatically send attached photos
async def show_patient_card(
    update: Update, context: ContextTypes.DEFAULT_TYPE, name: str, data: dict
):
  chat_id = update.effective_chat.id
  unit = data.get("unit", "Unassigned")
  diagnosis = data.get("diagnosis", "Not specified")
  labs_text = (
      "\n".join([f"• {lab}" for lab in data.get("labs", [])])
      if data.get("labs")
      else "No labs recorded yet."
  )
  photos = data.get("photos", [])
  photos_count = len(photos)

  text = (
      f"👤 **Patient:** {name}\n"
      f"🏥 **Unit:** {unit}\n"
      f"🏷️ **Diagnosis:** {diagnosis}\n"
      f"📄 **Saved Sheets / Photos:** {photos_count} attached\n\n"
      f"🧪 **Labs & Notes:**\n{labs_text}\n\n"
      "👇 Choose an action below:"
  )

  keyboard = [
      [InlineKeyboardButton("📄 Add Sheet (Photo)", callback_data=f"addphoto_{name}")],
      [InlineKeyboardButton("🏷️ Set Diagnosis", callback_data=f"dxmenu_{name}")],
      [InlineKeyboardButton("✏️ Add Lab / Note", callback_data=f"addlab_{name}")],
      [InlineKeyboardButton("🚪 Discharge Patient", callback_data=f"discharge_{name}")],
  ]
  markup = InlineKeyboardMarkup(keyboard)

  # 1. Send text profile card
  if update.callback_query:
    await update.callback_query.message.reply_text(
        text, reply_markup=markup, parse_mode="Markdown"
    )
  else:
    await update.message.reply_text(
        text, reply_markup=markup, parse_mode="Markdown"
    )

  # 2. Automatically send all attached sheet photos right below it
  for file_id in photos:
    try:
      await context.bot.send_photo(
          chat_id=chat_id, photo=file_id, caption=f"📄 Sheet for {name}"
      )
    except Exception:
      pass


# Main text handler (Search or Add Note/Labs)
async def handle_text_message(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
  user_text = update.message.text.strip()
  records = load_records()

  active_patient = context.user_data.get("adding_labs_for")
  if active_patient:
    if active_patient not in records:
      records[active_patient] = {
          "unit": "Unassigned",
          "diagnosis": "Not specified",
          "labs": [],
          "photos": [],
      }
    if "labs" not in records[active_patient]:
      records[active_patient]["labs"] = []

    records[active_patient]["labs"].append(user_text)
    save_records(records)
    context.user_data["adding_labs_for"] = None

    await update.message.reply_text(
        f"✅ **Saved note for {active_patient}:**\n`{user_text}`",
        parse_mode="Markdown",
    )
    return

  query_name = user_text.lower()
  matches = [p for p in records if query_name in p.lower()]

  if not matches:
    context.user_data["pending_new_patient"] = user_text
    keyboard = [
        [
            InlineKeyboardButton(
                "Unit 1", callback_data=f"newunit_Unit 1_{user_text}"
            ),
            InlineKeyboardButton(
                "Unit 2", callback_data=f"newunit_Unit 2_{user_text}"
            ),
        ],
        [
            InlineKeyboardButton(
                "Unit 3", callback_data=f"newunit_Unit 3_{user_text}"
            ),
            InlineKeyboardButton(
                "Unit 4", callback_data=f"newunit_Unit 4_{user_text}"
            ),
        ],
        [
            InlineKeyboardButton(
                "Unit 5", callback_data=f"newunit_Unit 5_{user_text}"
            )
        ],
    ]
    await update.message.reply_text(
        f"❌ Patient **'{user_text}'** not found in records.\n\nChoose a unit"
        " below to create a new patient profile:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )
  elif len(matches) == 1:
    await show_patient_card(update, context, matches[0], records[matches[0]])
  else:
    keyboard = [
        [InlineKeyboardButton(name, callback_data=f"select_{name}")]
        for name in matches
    ]
    await update.message.reply_text(
        "Found multiple matching patients. Select one:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


# Handler for receiving photos (Sheet / Lab images)
async def handle_photo_message(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
  active_patient = context.user_data.get("adding_photo_for")
  if not active_patient:
    await update.message.reply_text(
        "Please search for a patient first and tap 'Add Sheet (Photo)' before"
        " sending a photo."
    )
    return

  records = load_records()
  if active_patient not in records:
    records[active_patient] = {
        "unit": "Unassigned",
        "diagnosis": "Not specified",
        "labs": [],
        "photos": [],
    }
  if "photos" not in records[active_patient]:
    records[active_patient]["photos"] = []

  photo_file_id = update.message.photo[-1].file_id
  records[active_patient]["photos"].append(photo_file_id)
  save_records(records)

  context.user_data["adding_photo_for"] = None

  await update.message.reply_text(
      f"📸 **Sheet saved successfully for {active_patient}!**",
      parse_mode="Markdown",
  )
  await show_patient_card(update, context, active_patient, records[active_patient])


# Callback Query Handler for Buttons
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
  query = update.callback_query
  await query.answer()
  data = query.data

  if data.startswith("newunit_"):
    parts = data.replace("newunit_", "").split("_", 1)
    unit_name = parts[0]
    patient_name = parts[1]

    records = load_records()
    records[patient_name] = {
        "unit": unit_name,
        "diagnosis": "Not specified",
        "labs": [],
        "photos": [],
    }
    save_records(records)

    await query.message.reply_text(
        f"✅ Created new profile for **{patient_name}** under **{unit_name}**!",
        parse_mode="Markdown",
    )
    await show_patient_card(update, context, patient_name, records[patient_name])

  elif data.startswith("showunit_"):
    target_unit = data.replace("showunit_", "")
    records = load_records()

    unit_patients = [
        name for name, info in records.items() if info.get("unit") == target_unit
    ]

    if not unit_patients:
      await query.message.reply_text(
          f"📂 No patients currently registered in **{target_unit}**.",
          parse_mode="Markdown",
      )
    else:
      keyboard = [
          [InlineKeyboardButton(name, callback_data=f"select_{name}")]
          for name in unit_patients
      ]
      await query.message.reply_text(
          f"📋 **Patients in {target_unit}:**",
          reply_markup=InlineKeyboardMarkup(keyboard),
          parse_mode="Markdown",
      )

  elif data.startswith("addphoto_"):
    patient_name = data.replace("addphoto_", "")
    context.user_data["adding_photo_for"] = patient_name
    await query.message.reply_text(
        f"📷 **Ready for {patient_name} (Sheet):**\nNow take a photo or upload an"
        " image of the patient sheet/labs from your gallery.",
        parse_mode="Markdown",
    )

  elif data.startswith("dxmenu_"):
    patient_name = data.replace("dxmenu_", "")
    keyboard = [
        [
            InlineKeyboardButton("Term", callback_data=f"setdx_{patient_name}_Term"),
            InlineKeyboardButton("Pre-term", callback_data=f"setdx_{patient_name}_Pre-term"),
        ],
        [
            InlineKeyboardButton("Preeclampsia", callback_data=f"setdx_{patient_name}_Preeclampsia"),
            InlineKeyboardButton("Previa", callback_data=f"setdx_{patient_name}_Previa"),
        ],
        [
            InlineKeyboardButton("Hyperemesis", callback_data=f"setdx_{patient_name}_Hyperemesis"),
            InlineKeyboardButton("PROM", callback_data=f"setdx_{patient_name}_PROM"),
        ],
        [
            InlineKeyboardButton("Anemia", callback_data=f"setdx_{patient_name}_Anemia"),
            InlineKeyboardButton("Abortion", callback_data=f"setdx_{patient_name}_Abortion"),
        ],
        [
            InlineKeyboardButton("Molar", callback_data=f"setdx_{patient_name}_Molar"),
            InlineKeyboardButton("Ectopic", callback_data=f"setdx_{patient_name}_Ectopic"),
        ],
    ]
    await query.message.reply_text(
        f"Select diagnosis for **{patient_name}**:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )

  elif data.startswith("setdx_"):
    parts = data.replace("setdx_", "").split("_", 1)
    patient_name = parts[0]
    dx_value = parts[1]

    records = load_records()
    if patient_name in records:
      records[patient_name]["diagnosis"] = dx_value
      save_records(records)
      await query.message.reply_text(
          f"✅ Updated diagnosis for **{patient_name}** to: **{dx_value}**",
          parse_mode="Markdown",
      )
      await show_patient_card(update, context, patient_name, records[patient_name])

  elif data.startswith("addlab_"):
    patient_name = data.replace("addlab_", "")
    context.user_data["adding_labs_for"] = patient_name
    await query.message.reply_text(
        f"📝 **Ready for {patient_name}:**\nSend the lab results or clinical notes"
        " now as a text message.",
        parse_mode="Markdown",
    )

  elif data.startswith("discharge_"):
    patient_name = data.replace("discharge_", "")
    records = load_records()
    if patient_name in records:
      del records[patient_name]
      save_records(records)
      await query.message.reply_text(
          f"🚪 **Patient {patient_name} has been discharged and removed from active records.**",
          parse_mode="Markdown",
      )
    else:
      await query.message.reply_text("Patient record not found or already discharged.")

  elif data.startswith("select_"):
    patient_name = data.replace("select_", "")
    records = load_records()
    await show_patient_card(update, context, patient_name, records.get(patient_name, {}))


def main():
  TOKEN = "8880459158:AAEjWeGnEfR6X5EqAtL9bpjdmjYvm2vY8Vo"
  app = ApplicationBuilder().token(TOKEN).build()

  app.add_handler(CommandHandler("start", start))
  app.add_handler(CommandHandler("units", units_menu))
  app.add_handler(CallbackQueryHandler(button_handler))
  app.add_handler(MessageHandler(filters.PHOTO, handle_photo_message))
  app.add_handler(
      MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message)
  )

  print("Bot running with automatic photo viewing, diagnoses, and unit workflow!")
  app.run_polling()


if __name__ == "__main__":
  main()
