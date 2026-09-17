import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
import json
import os
from datetime import datetime, timedelta

TOKEN = "8880459158:AAEjWeGnEfR6X5EqAtL9bpjdmjYvm2vY8Vo"
bot = telebot.TeleBot(TOKEN)
DB_FILE = "patient_records.json"

def load_data():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as file:
            return json.load(file)
    return {}

def save_data(data):
    with open(DB_FILE, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=4)

patient_database = load_data()
user_states = {} 

def send_patient_files(chat_id, found_id):
    pdata = patient_database[found_id]
    records = pdata["records"]
    
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("➕ إضافة ملف جديد", callback_data=f"add_{found_id}"))
    
    if not records:
        bot.send_message(chat_id, f"🏥 المريض: {pdata['name']}\n📂 ليس لديه ملفات مسجلة بعد.", reply_markup=markup)
    else:
        bot.send_message(chat_id, f"🏥 المريض: {pdata['name']}\n📂 جاري إرسال جميع الملفات السابقة...", reply_markup=markup)
        
        photos = []
        for r in records[-10:]:
            if r["file_type"] == "photo":
                photos.append(InputMediaPhoto(r["file_id"], caption=r["caption"]))
            elif r["file_type"] == "document":
                bot.send_document(chat_id, r["file_id"], caption=r["caption"])
                
        if photos:
            bot.send_media_group(chat_id, photos)
            
        bot.send_message(chat_id, "إضافة ملف آخر لهذا المريض:", reply_markup=markup)

# --- 1. SMART FIRST-NAME & PARTIAL SEARCH ---
@bot.message_handler(commands=['find'])
def search_patient(message):
    search_query = message.text.replace('/find', '').strip().lower()
    if not search_query:
        bot.reply_to(message, "⚠️ الرجاء كتابة الاسم للبحث. مثال: /find مريم")
        return

    # Find all patients whose name contains the search query
    matching_patients = []
    for pid, pdata in patient_database.items():
        if search_query in pdata["name"].strip().lower():
            matching_patients.append((pid, pdata["name"]))

    if len(matching_patients) == 0:
        # If no match at all, automatically register as a new patient with the typed name
        new_id = str(int(datetime.now().timestamp()))
        patient_name_formatted = message.text.replace('/find', '').strip()
        patient_database[new_id] = {"name": patient_name_formatted, "records": []}
        save_data(patient_database)
        
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("➕ إضافة ملف", callback_data=f"add_{new_id}"))
        bot.send_message(message.chat.id, f"🆕 لم يتم العثور على مطابقة، تم تسجيل المريض الجديد: {patient_name_formatted}", reply_markup=markup)
        return

    elif len(matching_patients) == 1:
        # Exactly one match: show their records immediately
        found_id, _ = matching_patients[0]
        send_patient_files(message.chat.id, found_id)

    else:
        # Multiple matches: show a list of buttons for each matching patient
        markup = InlineKeyboardMarkup(row_width=1)
        for pid, pname in matching_patients:
            markup.add(InlineKeyboardButton(f"👤 {pname}", callback_data=f"viewpat_{pid}"))
        bot.send_message(message.chat.id, f"🔍 تم العثور على عدة مرضى مطابقين لـ '{search_query}'. اختر المريض:", reply_markup=markup)

# --- 2. DATE-BASED VIEWING WORKFLOW ---
@bot.message_handler(commands=['gallery'])
def show_dates(message):
    markup = InlineKeyboardMarkup(row_width=1)
    
    for i in range(5):
        target_date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
        
        label = f"📅 عرض ملفات يوم {target_date}"
        if i == 0: label = f"📅 اليوم ({target_date})"
        elif i == 1: label = f"📅 الأمس ({target_date})"
            
        markup.add(InlineKeyboardButton(label, callback_data=f"date_{target_date}"))
        
    bot.send_message(message.chat.id, "اختر اليوم لعرض قائمة المرضى:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    parts = call.data.split('_', 2)
    action = parts[0]
    
    if action == "date":
        target_date = parts[1]
        markup = InlineKeyboardMarkup(row_width=1)
        found_patients = False
        
        for pat_id, pat_data in patient_database.items():
            has_record_on_date = any(r.get("date_only") == target_date for r in pat_data["records"])
            
            if has_record_on_date:
                found_patients = True
                btn_label = f"👤 {pat_data['name']}"
                markup.add(InlineKeyboardButton(btn_label, callback_data=f"viewpat_{pat_id}"))
                
        if not found_patients:
            bot.edit_message_text(f"لا يوجد مرضى لديهم ملفات في يوم {target_date}.", call.message.chat.id, call.message.message_id)
        else:
            bot.edit_message_text(f"👇 المرضى المسجل لهم ملفات يوم {target_date}:", call.message.chat.id, call.message.message_id, reply_markup=markup)

    elif action == "viewpat":
        patient_id = parts[1]
        send_patient_files(call.message.chat.id, patient_id)
            
    elif action == "add":
        patient_id = parts[1]
        patient_name = patient_database[patient_id]["name"]
        
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton("🩺 سونار", callback_data=f"cat_سونار_{patient_id}"),
            InlineKeyboardButton("🧪 تحاليل", callback_data=f"cat_تحاليل_{patient_id}"),
            InlineKeyboardButton("📝 تاريخ مرضي", callback_data=f"cat_تاريخ_{patient_id}"),
            InlineKeyboardButton("🔍 فحص", callback_data=f"cat_فحص_{patient_id}")
        )
        bot.send_message(call.message.chat.id, f"اختر نوع الملف لإضافته للمريض: {patient_name}", reply_markup=markup)
        
    elif action == "cat":
        category = parts[1]
        patient_id = parts[2]
        patient_name = patient_database[patient_id]["name"]
        
        user_states[call.from_user.id] = {"state": "uploading", "id": patient_id, "category": category}
        bot.send_message(call.message.chat.id, f"📸 بانتظار إرسال ({category}) للمريض {patient_name}.")

@bot.message_handler(content_types=['photo', 'document'])
def handle_file(message):
    user_id = message.from_user.id
    if user_id in user_states and user_states[user_id].get("state") == "uploading":
        state_data = user_states[user_id]
        patient_id = state_data["id"]
        category = state_data["category"]
        
        if message.content_type == 'photo':
            file_id = message.photo[-1].file_id 
            file_type = "photo"
        else:
            file_id = message.document.file_id
            file_type = "document"
            
        doctor_name = message.from_user.first_name
        now = datetime.now()
        current_date_time = now.strftime("%Y-%m-%d %H:%M")
        current_date_only = now.strftime("%Y-%m-%d")
        
        user_note = message.caption if message.caption else ""
        final_caption = f"📌 التصنيف: {category}\n"
        if user_note: final_caption += f"📝 ملاحظات: {user_note}\n"
        final_caption += f"👨‍⚕️ بواسطة: د. {doctor_name}\n📅 التاريخ: {current_date_time}"
        
        patient_database[patient_id]["records"].append({
            "file_id": file_id, 
            "file_type": file_type,
            "caption": final_caption,
            "date_only": current_date_only 
        })
        save_data(patient_database)
        
        del user_states[user_id]
        bot.reply_to(message, f"✅ تم حفظ الملف بنجاح!\n\n{final_caption}")

bot.polling(none_stop=True)