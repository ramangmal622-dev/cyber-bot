import os
import subprocess
import sys

# التحقق التلقائي وتثبيت المكتبات اللازمة
try:
    import telebot
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyTelegramBotAPI"])
    import telebot

try:
    from flask import Flask, request
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "flask"])
    from flask import Flask, request

import sqlite3
from telebot import types

TOKEN = "8912899117:AAEm3AIIort2GI7G6fOC7nVvKOQSa9SAVaQ"
bot = telebot.TeleBot(TOKEN)
OWNER_ID = 8083038345  

# إعداد تطبيق Flask لاستقبال الـ Webhook من Railway
app = Flask(__name__)

# ==================== قاعدة البيانات والجدولة (Database Setup) ====================
def init_db():
    conn = sqlite3.connect('bot_database.db', check_same_thread=False)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            fullname TEXT,
            points INTEGER DEFAULT 0,
            is_admin INTEGER DEFAULT 0,
            is_banned INTEGER DEFAULT 0
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admin_permissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            section_key TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS faculties (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fac_key TEXT UNIQUE,
            fac_name TEXT
        )
    ''')
    cursor.execute("INSERT OR IGNORE INTO faculties (fac_key, fac_name) VALUES ('cyber', '🛡️ الأمن السيبراني')")
    cursor.execute("INSERT OR IGNORE INTO faculties (fac_key, fac_name) VALUES ('it', '💻 تقنية معلومات (IT)')")
    cursor.execute("INSERT OR IGNORE INTO faculties (fac_key, fac_name) VALUES ('arch', '🏛️ هندسة معمارية')")

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS level_buttons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT,
            button_name TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS files (
            file_id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT,
            instructor TEXT,
            file_id_tg TEXT,
            file_type TEXT,
            file_name TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS instructors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE
        )
    ''')
    cursor.execute("INSERT OR IGNORE INTO instructors (name) VALUES ('د. أكرم الحداد')")
    cursor.execute("INSERT OR IGNORE INTO instructors (name) VALUES ('أ. فريال المقطري')")
    cursor.execute("INSERT OR IGNORE INTO instructors (name) VALUES ('أ. مصطفى')")

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS logs (
            log_id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id INTEGER,
            action TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('maintenance', 'off')")
    
    conn.commit()
    conn.close()

init_db()

def get_db():
    return sqlite3.connect('bot_database.db', check_same_thread=False)

def is_owner(user_id):
    return user_id == OWNER_ID

def is_admin(user_id):
    if user_id == OWNER_ID:
        return True
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT is_admin FROM users WHERE user_id = ?", (user_id,))
    res = cursor.fetchone()
    conn.close()
    return res and res[0] == 1

def check_maintenance(user_id):
    if user_id == OWNER_ID or is_admin(user_id):
        return False
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key = 'maintenance'")
    res = cursor.fetchone()
    conn.close()
    return res and res[0] == 'on'


# ==================== الأوامر الرئيسية (Start & Welcome) ====================

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    username = message.from_user.username
    fullname = message.from_user.full_name
    
    if check_maintenance(user_id):
        bot.reply_to(message, "🛠️ البوت في وضع الصيانة حالياً للتحديثات. يرجى العودة لاحقاً.")
        return

    conn = get_db()
    cursor = conn.cursor()
    admin_val = 1 if user_id == OWNER_ID else 0
    
    cursor.execute("SELECT is_banned FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    
    if row and row[0] == 1 and user_id != OWNER_ID:
        bot.reply_to(message, "❌ عذراً، تم حظرك من استخدام هذا البوت من قبل الإدارة.")
        conn.close()
        return
        
    if not row:
        cursor.execute("INSERT INTO users (user_id, username, fullname, is_admin) VALUES (?, ?, ?, ?)",
                       (user_id, username, fullname, admin_val))
    conn.commit()
    conn.close()

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("📂 تصفح الأقسام والملازم", "👨‍🏫 قسم الأساتذة والمواد")
    markup.add("⭐ نقاطي ومعلوماتي", "📞 التواصل والدعم الفني")
    
    if is_admin(user_id):
        markup.add("👑 لوحة تحكم الأدمن الشاملة")
        
    bot.send_message(message.chat.id, f"مرحباً بك يا {fullname} في البوت الأكاديمي الشامل 🎓\nاختر من الأزرار بالأسفل للبدء:", reply_markup=markup)


# ==================== تصفح الطلاب للأقسام والمستويات ====================

@bot.message_handler(func=lambda msg: msg.text == "📂 تصفح الأقسام والملازم")
def show_student_faculties(message):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT fac_key, fac_name FROM faculties")
    facs = cursor.fetchall()
    conn.close()

    markup = types.InlineKeyboardMarkup(row_width=1)
    for f in facs:
        markup.add(types.InlineKeyboardButton(f[1], callback_data=f"fac_{f[0]}"))
    
    bot.send_message(message.chat.id, "📂 **اختر التخصص الدراسي المطلوب:**", reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("fac_") and not call.data.startswith("adm_fac_"))
def show_levels_for_faculty(call):
    prefix = call.data.replace("fac_", "")
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT fac_name FROM faculties WHERE fac_key = ?", (prefix,))
    res = cursor.fetchone()
    fac_title = res[0] if res else prefix
    conn.close()
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("1️⃣ المستوى الأول", callback_data=f"lvl_{prefix}_1"),
        types.InlineKeyboardButton("2️⃣ المستوى الثاني", callback_data=f"lvl_{prefix}_2"),
        types.InlineKeyboardButton("3️⃣ المستوى الثالث", callback_data=f"lvl_{prefix}_3"),
        types.InlineKeyboardButton("4️⃣ المستوى الرابع", callback_data=f"lvl_{prefix}_4"),
        types.InlineKeyboardButton("🔙 العودة للتخصصات", callback_data="back_to_faculties")
    )
    try:
        bot.edit_message_text(f"📚 **{fac_title}**\nاختر المستوى الدراسي المطلوب:", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")
    except Exception:
        pass

@bot.callback_query_handler(func=lambda call: call.data.startswith("lvl_") and not call.data.startswith("adm_lvl_") and not call.data.startswith("btn_lvl_"))
def show_level_content_and_controls(call):
    _, prefix, level_num = call.data.split("_")
    category = f"{prefix}_{level_num}"
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT fac_name FROM faculties WHERE fac_key = ?", (prefix,))
    res = cursor.fetchone()
    fac_title = res[0] if res else prefix
    
    cursor.execute("SELECT id, button_name FROM level_buttons WHERE category = ?", (category,))
    custom_btns = cursor.fetchall()
    conn.close()
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for b in custom_btns:
        markup.add(types.InlineKeyboardButton(f"👨‍🏫 {b[1]}", callback_data=f"view_cbtn_{b[0]}"))
        
    markup.add(
        types.InlineKeyboardButton("📁 عرض كافة ملفات هذا المستوى", callback_data=f"getfiles_{prefix}_{level_num}"),
        types.InlineKeyboardButton("🔙 العودة للمستويات", callback_data=f"fac_{prefix}")
    )
    try:
        bot.edit_message_text(f"🎓 **{fac_title} - المستوى {level_num}**\nاختر المادة أو الأستاذ:", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")
    except Exception:
        pass

@bot.callback_query_handler(func=lambda call: call.data.startswith("view_cbtn_"))
def view_custom_button_files(call):
    btn_id = call.data.replace("view_cbtn_", "")
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT button_name, category FROM level_buttons WHERE id = ?", (btn_id,))
    b_data = cursor.fetchone()
    if not b_data:
        bot.answer_callback_query(call.id, "⚠️ العنصر غير موجود.", show_alert=True)
        conn.close()
        return
    
    b_name, category = b_data[0], b_data[1]
    cursor.execute("SELECT file_id_tg, file_name, file_type FROM files WHERE category = ? AND instructor = ?", (category, b_name))
    files = cursor.fetchall()
    conn.close()
    
    if not files:
        bot.answer_callback_query(call.id, f"📭 لا توجد ملفات مرفوعة تحت اسم ({b_name}) حالياً.", show_alert=True)
        return
        
    bot.answer_callback_query(call.id, f"📂 جاري إرسال ملفات {b_name}...")
    for f in files:
        try:
            if f[2] == 'document':
                bot.send_document(call.message.chat.id, f[0], caption=f"📄 {f[1]}\n📌 بواسطة: {b_name}")
            elif f[2] == 'photo':
                bot.send_photo(call.message.chat.id, f[0], caption=f"📄 {f[1]}\n📌 بواسطة: {b_name}")
        except Exception:
            pass

@bot.callback_query_handler(func=lambda call: call.data.startswith("getfiles_"))
def student_get_files(call):
    _, prefix, level_num = call.data.split("_")
    category = f"{prefix}_{level_num}"
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT file_id_tg, file_name, file_type, instructor FROM files WHERE category = ?", (category,))
    files = cursor.fetchall()
    conn.close()
    
    if not files:
        bot.answer_callback_query(call.id, "📭 لا توجد ملفات مرفوعة في هذا المستوى حتى الآن.", show_alert=True)
        return
    
    bot.answer_callback_query(call.id, "📂 جاري إرسال الملفات...")
    for f in files:
        try:
            if f[2] == 'document':
                bot.send_document(call.message.chat.id, f[0], caption=f"📄 {f[1]}\n👨‍🏫 الأستاذ: {f[3]}")
            elif f[2] == 'photo':
                bot.send_photo(call.message.chat.id, f[0], caption=f"📄 {f[1]}\n👨‍🏫 الأستاذ: {f[3]}")
        except Exception:
            pass

@bot.callback_query_handler(func=lambda call: call.data == "back_to_faculties")
def back_to_faculties_handler(call):
    show_student_faculties(call.message)


# ==================== قسم الأساتذة والمواد ====================

@bot.message_handler(func=lambda msg: msg.text == "👨‍🏫 قسم الأساتذة والمواد")
def show_instructors(message):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM instructors")
    instructors = cursor.fetchall()
    conn.close()

    markup = types.InlineKeyboardMarkup(row_width=1)
    for inst in instructors:
        markup.add(types.InlineKeyboardButton(f"📚 ملفات {inst[0]}", callback_data=f"inst_{inst[0]}"))
    
    markup.add(types.InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="main_menu_cb"))
    bot.send_message(message.chat.id, "👨‍🏫 **اختر الأستاذ لعرض مواده وملفاته الدراسية:**", reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("inst_") and not call.data.startswith("inst_pick_"))
def show_instructor_files(call):
    instructor_name = call.data.replace("inst_", "")
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT file_id_tg, file_name, file_type, category FROM files WHERE instructor = ?", (instructor_name,))
    files = cursor.fetchall()
    conn.close()
    
    if not files:
        bot.answer_callback_query(call.id, "📭 لا توجد ملفات مسجلة لهذا الأستاذ حالياً.", show_alert=True)
        return
    
    bot.answer_callback_query(call.id, f"📂 ملفات {instructor_name}...")
    for f in files:
        try:
            if f[2] == 'document':
                bot.send_document(call.message.chat.id, f[0], caption=f"📄 {f[1]}\n📌 القسم: {f[3]}")
            elif f[2] == 'photo':
                bot.send_photo(call.message.chat.id, f[0], caption=f"📄 {f[1]}\n📌 القسم: {f[3]}")
        except Exception:
            pass

@bot.message_handler(func=lambda msg: msg.text == "⭐ نقاطي ومعلوماتي")
def my_profile(message):
    user_id = message.from_user.id
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT fullname, points, is_admin FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()

    if row:
        rank = "مشرف (أدمن) 👑" if row[2] == 1 or user_id == OWNER_ID else "طالب 🎓"
        text = (
            f"👤 **الملف الشخصي والبيانات:**\n\n"
            f"▪️ الاسم: `{row[0]}`\n"
            f"▪️ الآيدي: `{user_id}`\n"
            f"▪️ الرتبة الأكاديمية: `{rank}`\n"
            f"▪️ رصيد النقاط: `⭐ {row[1]}`"
        )
        bot.reply_to(message, text, parse_mode="Markdown")

@bot.message_handler(func=lambda msg: msg.text == "📞 التواصل والدعم الفني")
def contact_support(message):
    bot.reply_to(message, "💬 لأي استفسار أو مشكلة تقنية تواجهك داخل البوت، يرجى التواصل مع إدارة البوت أو مشرف القسم.")


# ==================== لوحة تحكم الأدمن الشاملة ====================

@bot.message_handler(func=lambda msg: msg.text == "👑 لوحة تحكم الأدمن الشاملة")
def admin_main_panel(message):
    user_id = message.from_user.id
    if not is_admin(user_id):
        bot.reply_to(message, "❌ عذراً، هذا القسم مخصص للمشرفين فقط.")
        return

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT fac_key, fac_name FROM faculties")
    facs = cursor.fetchall()
    conn.close()

    markup = types.InlineKeyboardMarkup(row_width=1)
    for f in facs:
        markup.add(types.InlineKeyboardButton(f"🛡️ إدارة {f[1]}", callback_data=f"adm_fac_{f[0]}"))
        
    markup.add(
        types.InlineKeyboardButton("➕ إضافة قسم رئيسي جديد", callback_data="adm_add_faculty"),
        types.InlineKeyboardButton("👥 إدارة الطلاب والنقاط والحظر", callback_data="adm_users_mgmt"),
        types.InlineKeyboardButton("👑 إدارة المشرفين والصلاحيات", callback_data="adm_perms_mgmt"),
        types.InlineKeyboardButton("➕ إضافة أستاذ جديد للقائمة", callback_data="adm_add_instructor"),
        types.InlineKeyboardButton("📢 الإذاعة والتنبيهات العامة", callback_data="adm_broadcast_start"),
        types.InlineKeyboardButton("🛠️ وضع الصيانة والإحصائيات", callback_data="adm_sec_system")
    )
    bot.send_message(message.chat.id, "👑 **لوحة التحكم الإدارية المركزية الشاملة:**\nاختر القسم المطلوب للإدارة والتحكم الكامل:", reply_markup=markup, parse_mode="Markdown")


@bot.callback_query_handler(func=lambda call: call.data.startswith("adm_") or call.data.startswith("up_lvl_") or call.data.startswith("del_lvl_") or call.data.startswith("btn_lvl_") or call.data.startswith("inst_pick_") or call.data.startswith("user_") or call.data.startswith("perm_"))
def admin_sections_router(call):
    user_id = call.from_user.id
    if not is_admin(user_id):
        bot.answer_callback_query(call.id, "غير مأذون لك بالدخول!", show_alert=True)
        return

    conn = get_db()
    cursor = conn.cursor()

    if call.data == "adm_back_main":
        admin_main_panel_edit(call)
        conn.close()
        return

    if call.data == "adm_add_faculty":
        bot.answer_callback_query(call.id)
        msg = bot.send_message(call.message.chat.id, "✍️ أرسل **مفتاح القسم بالإنجليزية** و **اسم القسم بالعربي** (مثال:\n`med كلية الطب`):")
        bot.register_next_step_handler(msg, save_new_faculty)
        conn.close()
        return

    if call.data.startswith("adm_fac_"):
        prefix = call.data.replace("adm_fac_", "")
        cursor.execute("SELECT fac_name FROM faculties WHERE fac_key = ?", (prefix,))
        res = cursor.fetchone()
        fac_title = res[0] if res else prefix
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("1️⃣ المستوى الأول", callback_data=f"adm_lvl_{prefix}_1"),
            types.InlineKeyboardButton("2️⃣ المستوى الثاني", callback_data=f"adm_lvl_{prefix}_2"),
            types.InlineKeyboardButton("3️⃣ المستوى الثالث", callback_data=f"adm_lvl_{prefix}_3"),
            types.InlineKeyboardButton("4️⃣ المستوى الرابع", callback_data=f"adm_lvl_{prefix}_4"),
            types.InlineKeyboardButton("🔙 رجوع", callback_data="adm_back_main")
        )
        try:
            bot.edit_message_text(f"📂 **إدارة قسم: {fac_title}**\nاختر المستوى:", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")
        except Exception:
            pass

    elif call.data.startswith("adm_lvl_"):
        _, _, prefix, lvl = call.data.split("_")
        sec_key = f"{prefix}_{lvl}"
        
        cursor.execute("SELECT fac_name FROM faculties WHERE fac_key = ?", (prefix,))
        res = cursor.fetchone()
        fac_title = res[0] if res else prefix
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("➕ إضافة زر أستاذ/مادة لهذا المستوى", callback_data=f"btn_lvl_add_{sec_key}"),
            types.InlineKeyboardButton("➕ رفع ملف جديد لهذا المستوى", callback_data=f"up_lvl_{sec_key}"),
            types.InlineKeyboardButton("🗑️ حذف ملفات هذا المستوى", callback_data=f"del_lvl_{sec_key}"),
            types.InlineKeyboardButton(f"🔙 رجوع", callback_data=f"adm_fac_{prefix}")
        )
        try:
            bot.edit_message_text(f"⚙️ **إدارة: {fac_title} - المستوى {lvl}**", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")
        except Exception:
            pass

    elif call.data.startswith("btn_lvl_add_"):
        sec_key = call.data.replace("btn_lvl_add_", "")
        bot.answer_callback_query(call.id)
        msg = bot.send_message(call.message.chat.id, "✍️ أرسل الآن **اسم الدكتور أو الزر الجديد** الذي تريد إضافته لهذا المستوى (مثال: `د. سامي العبسي`):")
        bot.register_next_step_handler(msg, save_level_custom_button, sec_key)

    elif call.data == "adm_add_instructor":
        bot.answer_callback_query(call.id)
        msg = bot.send_message(call.message.chat.id, "✍️ أرسل الآن **اسم الأستاذ الجديد** للقائمة العامة:")
        bot.register_next_step_handler(msg, save_new_instructor_to_db)

    elif call.data.startswith("up_lvl_"):
        sec_key = call.data.replace("up_lvl_", "")
        
        cursor.execute("SELECT button_name FROM level_buttons WHERE category = ?", (sec_key,))
        lvl_btns = cursor.fetchall()
        cursor.execute("SELECT name FROM instructors")
        general_inst = cursor.fetchall()
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        for b in lvl_btns:
            markup.add(types.InlineKeyboardButton(f"📌 [مستوى] {b[0]}", callback_data=f"inst_pick_{sec_key}_{b[0]}"))
        for inst in general_inst:
            markup.add(types.InlineKeyboardButton(f"👨‍🏫 [عام] {inst[0]}", callback_data=f"inst_pick_{sec_key}_{inst[0]}"))
            
        markup.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="adm_back_main"))
        try:
            bot.edit_message_text("👨‍🏫 **اختر الجهة أو الأستاذ التابع له هذا الملف:**", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")
        except Exception:
            pass

    elif call.data.startswith("inst_pick_"):
        parts = call.data.replace("inst_pick_", "").split("_")
        sec_key = f"{parts[0]}_{parts[1]}"
        instructor_name = "_".join(parts[2:])
        
        bot.answer_callback_query(call.id)
        msg = bot.send_message(call.message.chat.id, f"📥 تم اختيار الموجه: **{instructor_name}**\n\nأرسل الآن الملف (مستند PDF أو صورة):")
        bot.register_next_step_handler(msg, save_uploaded_file_with_instructor, sec_key, instructor_name)

    elif call.data.startswith("del_lvl_"):
        sec_key = call.data.replace("del_lvl_", "")
        cursor.execute("DELETE FROM files WHERE category = ?", (sec_key,))
        conn.commit()
        bot.answer_callback_query(call.id, "🗑️ تم حذف جميع ملفات هذا المستوى بنجاح!", show_alert=True)

    elif call.data == "adm_users_mgmt":
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("➕ إضافة نقاط لطالب", callback_data="user_add_points"),
            types.InlineKeyboardButton("➖ خصم نقاط من طالب", callback_data="user_sub_points"),
            types.InlineKeyboardButton("🚫 حظر أو إلغاء حظر طالب", callback_data="user_ban_toggle"),
            types.InlineKeyboardButton("🔙 رجوع", callback_data="adm_back_main")
        )
        try:
            bot.edit_message_text("👥 **إدارة الطلاب ورصيد النقاط والحظر:**", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")
        except Exception:
            pass

    elif call.data == "user_add_points":
        bot.answer_callback_query(call.id)
        msg = bot.send_message(call.message.chat.id, "✍️ أرسل **آيدي الطالب** و **عدد النقاط** للإضافة (مثال: `123456 50`):")
        bot.register_next_step_handler(msg, process_add_points)

    elif call.data == "user_sub_points":
        bot.answer_callback_query(call.id)
        msg = bot.send_message(call.message.chat.id, "✍️ أرسل **آيدي الطالب** و **عدد النقاط** للخصم (مثال: `123456 20`):")
        bot.register_next_step_handler(msg, process_sub_points)

    elif call.data == "user_ban_toggle":
        bot.answer_callback_query(call.id)
        msg = bot.send_message(call.message.chat.id, "✍️ أرسل **آيدي الطالب** لحظره أو إلغاء حظره:")
        bot.register_next_step_handler(msg, process_ban_user)

    elif call.data == "adm_perms_mgmt":
        if not is_owner(user_id):
            bot.answer_callback_query(call.id, "❌ مخصص لمالك البوت فقط!", show_alert=True)
            conn.close()
            return
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("👑 تعيين أدمن عام للبوت", callback_data="perm_set_general"),
            types.InlineKeyboardButton("🔙 رجوع", callback_data="adm_back_main")
        )
        try:
            bot.edit_message_text("👑 **إدارة المشرفين:**", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")
        except Exception:
            pass

    elif call.data == "perm_set_general":
        bot.answer_callback_query(call.id)
        msg = bot.send_message(call.message.chat.id, "✍️ أرسل **آيدي المستخدم** لتعيينه مشرفاً عاماً:")
        bot.register_next_step_handler(msg, process_make_general_admin)

    elif call.data == "adm_broadcast_start":
        if not is_owner(user_id):
            return
        msg = bot.send_message(call.message.chat.id, "📢 أرسل الإذاعة المراد إرسالها لجميع الطلاب:")
        bot.register_next_step_handler(msg, process_global_broadcast)

    elif call.data == "adm_sec_system":
        cursor.execute("SELECT COUNT(*) FROM users")
        total_u = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM files")
        total_f = cursor.fetchone()[0]
        cursor.execute("SELECT value FROM settings WHERE key='maintenance'")
        maint = cursor.fetchone()[0].upper()
        
        stats = f"🛠️ **الإحصائيات:**\n- إجمالي الطلاب: `{total_u}`\n- إجمالي الملفات: `{total_f}`\n- وضع الصيانة: `{maint}`"
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("🛠️ تبديل وضع الصيانة", callback_data="adm_toggle_maint"),
            types.InlineKeyboardButton("🔙 رجوع", callback_data="adm_back_main")
        )
        try:
            bot.edit_message_text(stats, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")
        except Exception:
            pass

    elif call.data == "adm_toggle_maint":
        cursor.execute("SELECT value FROM settings WHERE key='maintenance'")
        cur = cursor.fetchone()[0]
        new_s = 'off' if cur == 'on' else 'on'
        cursor.execute("UPDATE settings SET value=? WHERE key='maintenance'", (new_s,))
        conn.commit()
        bot.answer_callback_query(call.id, f"تم تغيير الصيانة إلى: {new_s.upper()}", show_alert=True)

    conn.close()


# ==================== دوال الحفظ الإدارية الجديدة ====================

def save_new_faculty(message):
    if not is_admin(message.from_user.id):
        return
    try:
        parts = message.text.strip().split(maxsplit=1)
        fac_key = parts[0].lower()
        fac_name = parts[1]
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO faculties (fac_key, fac_name) VALUES (?, ?)", (fac_key, fac_name))
        conn.commit()
        conn.close()
        bot.reply_to(message, f"✅ **تم إضافة القسم الرئيسي الجديد ({fac_name}) بنجاح!**")
    except Exception:
        bot.reply_to(message, "⚠️ صيغة خاطئة. أرسل المفتاح بالإنجليزية ثم مسافة ثم اسم القسم (مثال: `med كلية الطب`).")

def save_level_custom_button(message, category):
    if not is_admin(message.from_user.id):
        return
    btn_name = message.text.strip()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO level_buttons (category, button_name) VALUES (?, ?)", (category, btn_name))
    conn.commit()
    conn.close()
    bot.reply_to(message, f"✅ **تم إضافة زر الدكتور/المادة ({btn_name}) بنجاح داخل هذا المستوى!**")

def save_new_instructor_to_db(message):
    if not is_admin(message.from_user.id):
        return
    new_name = message.text.strip()
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO instructors (name) VALUES (?)", (new_name,))
        conn.commit()
        bot.reply_to(message, f"✅ **تم إضافة الأستاذ ({new_name}) بنجاح للقائمة العامة!**")
    except sqlite3.IntegrityError:
        bot.reply_to(message, "⚠️ هذا الأستاذ موجود مسبقاً.")
    finally:
        conn.close()

def save_uploaded_file_with_instructor(message, category, instructor_name):
    if not is_admin(message.from_user.id):
        return
    if message.document:
        file_id_tg = message.document.file_id
        file_type = "document"
        file_name = message.document.file_name or "مستند"
    elif message.photo:
        file_id_tg = message.photo[-1].file_id
        file_type = "photo"
        file_name = "صورة توضيحية"
    else:
        bot.reply_to(message, "⚠️ يرجى إرسال ملف صالح.")
        return
        
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO files (category, instructor, file_id_tg, file_type, file_name) VALUES (?, ?, ?, ?, ?)",
                   (category, instructor_name, file_id_tg, file_type, file_name))
    conn.commit()
    conn.close()
    bot.reply_to(message, f"✅ **تم حفظ الملف بنجاح!**\n- مرتبط بـ: `{instructor_name}`.")

def process_add_points(message):
    if not is_admin(message.from_user.id):
        return
    try:
        parts = message.text.strip().split()
        target_id, pts = int(parts[0]), int(parts[1])
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET points = points + ? WHERE user_id = ?", (pts, target_id))
        conn.commit()
        conn.close()
        bot.reply_to(message, f"✅ **تم إضافة ({pts}) نقطة** بنجاح.")
    except Exception:
        bot.reply_to(message, "⚠️ صيغة خاطئة.")

def process_sub_points(message):
    if not is_admin(message.from_user.id):
        return
    try:
        parts = message.text.strip().split()
        target_id, pts = int(parts[0]), int(parts[1])
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET points = MAX(0, points - ?) WHERE user_id = ?", (pts, target_id))
        conn.commit()
        conn.close()
        bot.reply_to(message, f"✅ **تم خصم ({pts}) نقطة** بنجاح.")
    except Exception:
        bot.reply_to(message, "⚠️ صيغة خاطئة.")

def process_ban_user(message):
    if not is_admin(message.from_user.id):
        return
    try:
        target_id = int(message.text.strip())
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT is_banned FROM users WHERE user_id = ?", (target_id,))
        row = cursor.fetchone()
        if not row:
            bot.reply_to(message, "⚠️ المستخدم غير مسجل.")
            conn.close()
            return
        new_ban = 0 if row[0] == 1 else 1
        cursor.execute("UPDATE users SET is_banned = ? WHERE user_id = ?", (new_ban, target_id))
        conn.commit()
        conn.close()
        bot.reply_to(message, "تم حظر الطالب 🚫" if new_ban == 1 else "تم إلغاء الحظر ✅")
    except Exception:
        bot.reply_to(message, "⚠️ آيدي غير صالح.")

def process_make_general_admin(message):
    if not is_owner(message.from_user.id):
        return
    try:
        target_id = int(message.text.strip())
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET is_admin = 1 WHERE user_id = ?", (target_id,))
        conn.commit()
        conn.close()
        bot.reply_to(message, f"👑 **تم تعيين ({target_id}) كأدمن عام** بنجاح!")
    except Exception:
        bot.reply_to(message, "⚠️ آيدي غير صالح.")

def process_global_broadcast(message):
    if not is_owner(message.from_user.id):
        return
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users WHERE is_banned = 0")
    users = cursor.fetchall()
    conn.close()

    success = 0
    status_msg = bot.send_message(message.chat.id, "⏳ جاري الإذاعة...")
    for u in users:
        try:
            bot.copy_message(chat_id=u[0], from_chat_id=message.chat.id, message_id=message.message_id)
            success += 1
        except Exception:
            pass
    try:
        bot.edit_message_text(f"✅ **تمت الإذاعة بنجاح لـ (`{success}`) طالباً.**", message.chat.id, status_msg.message_id, parse_mode="Markdown")
    except Exception:
        pass

def admin_main_panel_edit(call):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT fac_key, fac_name FROM faculties")
    facs = cursor.fetchall()
    conn.close()

    markup = types.InlineKeyboardMarkup(row_width=1)
    for f in facs:
        markup.add(types.InlineKeyboardButton(f"🛡️ إدارة {f[1]}", callback_data=f"adm_fac_{f[0]}"))
        
    markup.add(
        types.InlineKeyboardButton("➕ إضافة قسم رئيسي جديد", callback_data="adm_add_faculty"),
        types.InlineKeyboardButton("👥 إدارة الطلاب والنقاط والحظر", callback_data="adm_users_mgmt"),
        types.InlineKeyboardButton("👑 إدارة المشرفين والصلاحيات", callback_data="adm_perms_mgmt"),
        types.InlineKeyboardButton("➕ إضافة أستاذ جديد للقائمة", callback_data="adm_add_instructor"),
        types.InlineKeyboardButton("📢 الإذاعة والتنبيهات العامة", callback_data="adm_broadcast_start"),
        types.InlineKeyboardButton("🛠️ وضع الصيانة والإحصائيات", callback_data="adm_sec_system")
    )
    try:
        bot.edit_message_text("👑 **لوحة التحكم الإدارية المركزية الشاملة:**\nاختر القسم المطلوب للإدارة والتحكم الكامل:", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")
    except Exception:
        pass

@bot.callback_query_handler(func=lambda call: call.data == "main_menu_cb")
def back_to_main(call):
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
        pass
    send_welcome(call.message)


# ==================== إعدادات Webhook لـ Railway ====================

@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return "!", 200
    else:
        return "Invalid Request", 403

@app.route('/')
def index():
    return "Bot is running successfully via Webhook!", 200


if __name__ == "__main__":
    print("🚀 جاري تهيئة البوت وتفعيل نظام Webhook...")
    
    # الحصول على رابط الدومين الخاص بـ Railway تلقائياً إن وجد، أو استخدام وضع المحلي
    RAILWAY_URL = os.environ.get("RAILWAY_STATIC_URL") or os.environ.get("RAILWAY_PUBLIC_DOMAIN")
    
    if RAILWAY_URL:
        webhook_url = f"https://{RAILWAY_URL}/{TOKEN}"
        bot.remove_webhook()
        bot.set_webhook(url=webhook_url)
        print(f"✅ تم ربط الـ Webhook بنجاح مع الرابط: {webhook_url}")
    else:
        print("⚠️ تنبيه: لم يتم اكتشاف متغير دومين Railway. يجدر التأكد من إعدادات النشر.")
        bot.remove_webhook()

    # تشغيل سيرفر Flask للاستماع لطلبات تيليجرام
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
