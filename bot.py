import subprocess
import sys

try:
    import telebot
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyTelegramBotAPI"])
    import telebot

import sqlite3
from telebot import types

TOKEN = "8912899117:AAEm3AIIort2GI7G6fOC7nVvKOQSa9SAVaQ"
bot = telebot.TeleBot(TOKEN)
OWNER_ID = 8083038345  

# ==================== قاعدة البيانات والجدولة (Database Setup) ====================
def init_db():
    conn = sqlite3.connect('bot_database.db', check_same_thread=False)
    cursor = conn.cursor()
    
    # جدول المستخدمين والطلاب
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
    
    # جدول صلاحيات المشرفين على الأقسام والمستويات
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admin_permissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            section_key TEXT
        )
    ''')
    
    # جدول الملفات والملازم
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
    
    # جدول الأساتذة (ديناميكي)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS instructors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE
        )
    ''')
    cursor.execute("INSERT OR IGNORE INTO instructors (name) VALUES ('د. أكرم الحداد')")
    cursor.execute("INSERT OR IGNORE INTO instructors (name) VALUES ('أ. فريال المقطري')")
    cursor.execute("INSERT OR IGNORE INTO instructors (name) VALUES ('أ. مصطفى')")

    # جدول السجلات (Logs)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS logs (
            log_id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id INTEGER,
            action TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # جدول الإعدادات العامة (مثل وضع الصيانة)
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

def has_section_permission(user_id, section_key):
    if user_id == OWNER_ID:
        return True
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM admin_permissions WHERE user_id = ? AND section_key = ?", (user_id, section_key))
    res = cursor.fetchone()
    conn.close()
    return res is not None

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
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("🛡️ الأمن السيبراني", callback_data="fac_cyber"),
        types.InlineKeyboardButton("💻 تقنية معلومات (IT)", callback_data="fac_it"),
        types.InlineKeyboardButton("🏛️ هندسة معمارية", callback_data="fac_arch")
    )
    bot.send_message(message.chat.id, "📂 **اختر التخصص الدراسي المطلوب:**", reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data in ["fac_cyber", "fac_it", "fac_arch"])
def show_levels_for_faculty(call):
    prefix = call.data.replace("fac_", "")
    fac_names = {"cyber": "🛡️ الأمن السيبراني", "it": "💻 تقنية معلومات (IT)", "arch": "🏛️ هندسة معمارية"}
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("1️⃣ المستوى الأول", callback_data=f"lvl_{prefix}_1"),
        types.InlineKeyboardButton("2️⃣ المستوى الثاني", callback_data=f"lvl_{prefix}_2"),
        types.InlineKeyboardButton("3️⃣ المستوى الثالث", callback_data=f"lvl_{prefix}_3"),
        types.InlineKeyboardButton("4️⃣ المستوى الرابع", callback_data=f"lvl_{prefix}_4"),
        types.InlineKeyboardButton("🔙 العودة للتخصصات", callback_data="back_to_faculties")
    )
    try:
        bot.edit_message_text(f"📚 **{fac_names.get(prefix)}**\nاختر المستوى الدراسي المطلوب:", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")
    except Exception:
        pass

@bot.callback_query_handler(func=lambda call: call.data.startswith("lvl_") and not call.data.startswith("adm_lvl_"))
def show_level_content_and_controls(call):
    _, prefix, level_num = call.data.split("_")
    fac_titles = {"cyber": "الأمن السيبراني", "it": "تقنية المعلومات", "arch": "الهندسة المعمارية"}
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("📁 عرض ملازم وكتب هذا المستوى", callback_data=f"getfiles_{prefix}_{level_num}"),
        types.InlineKeyboardButton("🔙 العودة للمستويات", callback_data=f"fac_{prefix}")
    )
    try:
        bot.edit_message_text(f"🎓 **تخصص {fac_titles.get(prefix)} - المستوى {level_num}**\nاختر الإجراء:", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")
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
        file_tg, f_name, f_type, inst = f[0], f[1], f[2], f[3]
        caption = f"📄 {f_name}\n👨‍🏫 الأستاذ: {inst}"
        try:
            if f_type == 'document':
                bot.send_document(call.message.chat.id, file_tg, caption=caption)
            elif f_type == 'photo':
                bot.send_photo(call.message.chat.id, file_tg, caption=caption)
        except Exception:
            pass

@bot.callback_query_handler(func=lambda call: call.data == "back_to_faculties")
def back_to_faculties_handler(call):
    show_student_faculties(call.message)


# ==================== قسم الأساتذة والمواد (ديناميكي) ====================

@bot.message_handler(func=lambda msg: msg.text == "👨‍🏫 قسم الأساتذة والمواد")
def show_instructors(message):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM instructors")
    instructors = cursor.fetchall()
    conn.close()

    markup = types.InlineKeyboardMarkup(row_width=1)
    for inst in instructors:
        inst_name = inst[0]
        markup.add(types.InlineKeyboardButton(f"📚 ملفات {inst_name}", callback_data=f"inst_{inst_name}"))
    
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
        file_tg, f_name, f_type, cat = f[0], f[1], f[2], f[3]
        caption = f"📄 {f_name}\n📌 القسم: {cat}"
        try:
            if f_type == 'document':
                bot.send_document(call.message.chat.id, file_tg, caption=caption)
            elif f_type == 'photo':
                bot.send_photo(call.message.chat.id, file_tg, caption=caption)
        except Exception:
            pass


# ==================== الملف الشخصي والنقاط والدعم ====================

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


# ==================== لوحة تحكم الأدمن الشاملة (التحكم الكامل) ====================

@bot.message_handler(func=lambda msg: msg.text == "👑 لوحة تحكم الأدمن الشاملة")
def admin_main_panel(message):
    user_id = message.from_user.id
    if not is_admin(user_id):
        bot.reply_to(message, "❌ عذراً، هذا القسم مخصص للمشرفين فقط.")
        return

    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("🛡️ أدمن قسم الأمن السيبراني", callback_data="adm_fac_cyber"),
        types.InlineKeyboardButton("💻 أدمن قسم تقنية المعلومات (IT)", callback_data="adm_fac_it"),
        types.InlineKeyboardButton("🏛️ أدمن قسم الهندسة المعمارية", callback_data="adm_fac_arch"),
        types.InlineKeyboardButton("👥 إدارة الطلاب والنقاط والحظر", callback_data="adm_users_mgmt"),
        types.InlineKeyboardButton("👑 إدارة المشرفين والصلاحيات", callback_data="adm_perms_mgmt"),
        types.InlineKeyboardButton("➕ إضافة أستاذ جديد للقائمة", callback_data="adm_add_instructor"),
        types.InlineKeyboardButton("📢 الإذاعة والتنبيهات العامة", callback_data="adm_broadcast_start"),
        types.InlineKeyboardButton("🛠️ وضع الصيانة والإحصائيات", callback_data="adm_sec_system")
    )
    bot.send_message(message.chat.id, "👑 **لوحة التحكم الإدارية المركزية الشاملة:**\nاختر القسم المطلوب للإدارة والتحكم الكامل:", reply_markup=markup, parse_mode="Markdown")


@bot.callback_query_handler(func=lambda call: call.data.startswith("adm_") or call.data.startswith("up_lvl_") or call.data.startswith("del_lvl_") or call.data.startswith("inst_pick_") or call.data.startswith("user_") or call.data.startswith("perm_"))
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

    # أقسام الكليات للإدارة
    if call.data == "adm_fac_cyber":
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("1️⃣ المستوى الأول", callback_data="adm_lvl_cyber_1"),
            types.InlineKeyboardButton("2️⃣ المستوى الثاني", callback_data="adm_lvl_cyber_2"),
            types.InlineKeyboardButton("3️⃣ المستوى الثالث", callback_data="adm_lvl_cyber_3"),
            types.InlineKeyboardButton("4️⃣ المستوى الرابع", callback_data="adm_lvl_cyber_4"),
            types.InlineKeyboardButton("🔙 رجوع", callback_data="adm_back_main")
        )
        try:
            bot.edit_message_text("🛡️ **إدارة قسم الأمن السيبراني:**\nاختر المستوى:", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")
        except Exception:
            pass

    elif call.data == "adm_fac_it":
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("1️⃣ المستوى الأول", callback_data="adm_lvl_it_1"),
            types.InlineKeyboardButton("2️⃣ المستوى الثاني", callback_data="adm_lvl_it_2"),
            types.InlineKeyboardButton("3️⃣ المستوى الثالث", callback_data="adm_lvl_it_3"),
            types.InlineKeyboardButton("4️⃣ المستوى الرابع", callback_data="adm_lvl_it_4"),
            types.InlineKeyboardButton("🔙 رجوع", callback_data="adm_back_main")
        )
        try:
            bot.edit_message_text("💻 **إدارة قسم تقنية المعلومات:**\nاختر المستوى:", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")
        except Exception:
            pass

    elif call.data == "adm_fac_arch":
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("1️⃣ المستوى الأول", callback_data="adm_lvl_arch_1"),
            types.InlineKeyboardButton("2️⃣ المستوى الثاني", callback_data="adm_lvl_arch_2"),
            types.InlineKeyboardButton("3️⃣ المستوى الثالث", callback_data="adm_lvl_arch_3"),
            types.InlineKeyboardButton("4️⃣ المستوى الرابع", callback_data="adm_lvl_arch_4"),
            types.InlineKeyboardButton("🔙 رجوع", callback_data="adm_back_main")
        )
        try:
            bot.edit_message_text("🏛️ **إدارة قسم الهندسة المعمارية:**\nاختر المستوى:", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")
        except Exception:
            pass

    # مستويات الإدارة والتحقق من الصلاحيات للمشرف الفرعي
    elif call.data.startswith("adm_lvl_"):
        _, _, prefix, lvl = call.data.split("_")
        sec_key = f"{prefix}_{lvl}"
        
        if not is_owner(user_id) and not has_section_permission(user_id, sec_key):
            bot.answer_callback_query(call.id, "❌ عذراً، لست مشرفاً مخولاً لهذا المستوى المخصص!", show_alert=True)
            conn.close()
            return
            
        fac_names = {"cyber": "الأمن السيبراني", "it": "تقنية المعلومات", "arch": "الهندسة المعمارية"}
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("➕ رفع ملف جديد لهذا المستوى", callback_data=f"up_lvl_{sec_key}"),
            types.InlineKeyboardButton("🗑️ حذف ملفات هذا المستوى", callback_data=f"del_lvl_{sec_key}"),
            types.InlineKeyboardButton(f"🔙 رجوع", callback_data=f"adm_fac_{prefix}")
        )
        try:
            bot.edit_message_text(f"⚙️ **إدارة مشرف: {fac_names.get(prefix)} - المستوى {lvl}**", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")
        except Exception:
            pass

    # إضافة أستاذ جديد ديناميكياً
    elif call.data == "adm_add_instructor":
        bot.answer_callback_query(call.id)
        msg = bot.send_message(call.message.chat.id, "✍️ أرسل الآن **اسم الأستاذ الجديد** (مثال: `د. أحمد محمد`) لإضافته إلى قائمة الأزرار فوراً:")
        bot.register_next_step_handler(msg, save_new_instructor_to_db)

    # رفع ملف واختيار الأستاذ
    elif call.data.startswith("up_lvl_"):
        sec_key = call.data.replace("up_lvl_", "")
        cursor.execute("SELECT name FROM instructors")
        instructors = cursor.fetchall()
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        for inst in instructors:
            inst_name = inst[0]
            markup.add(types.InlineKeyboardButton(f"👨‍🏫 {inst_name}", callback_data=f"inst_pick_{sec_key}_{inst_name}"))
        markup.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="adm_back_main"))
        try:
            bot.edit_message_text("👨‍🏫 **اختر الأستاذ التابع له هذا الملف:**", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")
        except Exception:
            pass

    elif call.data.startswith("inst_pick_"):
        parts = call.data.replace("inst_pick_", "").split("_")
        sec_key = f"{parts[0]}_{parts[1]}"
        instructor_name = "_".join(parts[2:])
        
        bot.answer_callback_query(call.id)
        msg = bot.send_message(call.message.chat.id, f"📥 تم اختيار الأستاذ: **{instructor_name}**\n\nأرسل الآن الملف (مستند PDF أو صورة) ليتم حفظه وربطه به مباشرة:")
        bot.register_next_step_handler(msg, save_uploaded_file_with_instructor, sec_key, instructor_name)

    elif call.data.startswith("del_lvl_"):
        sec_key = call.data.replace("del_lvl_", "")
        cursor.execute("DELETE FROM files WHERE category = ?", (sec_key,))
        conn.commit()
        bot.answer_callback_query(call.id, "🗑️ تم حذف جميع ملفات هذا المستوى بنجاح!", show_alert=True)

    # ==================== إدارة الطلاب (إضافة/خصم نقاط، حظر) ====================
    elif call.data == "adm_users_mgmt":
        if not is_owner(user_id) and not is_admin(user_id):
            return
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
        msg = bot.send_message(call.message.chat.id, "✍️ أرسل **آيدي الطالب** و **عدد النقاط** للإضافة (مثال هكذا:\n`123456789 50`):")
        bot.register_next_step_handler(msg, process_add_points)

    elif call.data == "user_sub_points":
        bot.answer_callback_query(call.id)
        msg = bot.send_message(call.message.chat.id, "✍️ أرسل **آيدي الطالب** و **عدد النقاط** للخصم (مثال هكذا:\n`123456789 20`):")
        bot.register_next_step_handler(msg, process_sub_points)

    elif call.data == "user_ban_toggle":
        bot.answer_callback_query(call.id)
        msg = bot.send_message(call.message.chat.id, "✍️ أرسل **آيدي الطالب** لحظره أو إلغاء حظره:")
        bot.register_next_step_handler(msg, process_ban_user)

    # ==================== إدارة المشرفين والصلاحيات ====================
    elif call.data == "adm_perms_mgmt":
        if not is_owner(user_id):
            bot.answer_callback_query(call.id, "❌ قسم إعطاء الصلاحيات مخصص لمالك البوت فقط!", show_alert=True)
            conn.close()
            return
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("👑 تعيين أدمن عام للبوت", callback_data="perm_set_general"),
            types.InlineKeyboardButton("⚙️ إعطاء صلاحية لمستوى محدد", callback_data="perm_set_level"),
            types.InlineKeyboardButton("🔙 رجوع", callback_data="adm_back_main")
        )
        try:
            bot.edit_message_text("👑 **إدارة المشرفين والصلاحيات الأكاديمية:**", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")
        except Exception:
            pass

    elif call.data == "perm_set_general":
        bot.answer_callback_query(call.id)
        msg = bot.send_message(call.message.chat.id, "✍️ أرسل **آيدي المستخدم** لتعيينه مشرفاً عاماً على البوت:")
        bot.register_next_step_handler(msg, process_make_general_admin)

    elif call.data == "perm_set_level":
        bot.answer_callback_query(call.id)
        msg = bot.send_message(call.message.chat.id, "✍️ أرسل **آيدي المستخدم** و **مفتاح القسم والمستوى** (مثال:\n`123456789 cyber_1`):\n\n*(المفتاح للتخصصات: `cyber_1` للأمن السيبراني أول، `it_2` لتقنية معلومات ثانٍ، إلخ).*")
        bot.register_next_step_handler(msg, process_assign_section_perm)

    # ==================== الإذاعة والنظام ====================
    elif call.data == "adm_broadcast_start":
        if not is_owner(user_id):
            return
        msg = bot.send_message(call.message.chat.id, "📢 أرسل الرسالة أو الإعلان المراد إذاعته لجميع الطلاب الآن:")
        bot.register_next_step_handler(msg, process_global_broadcast)

    elif call.data == "adm_sec_system":
        cursor.execute("SELECT COUNT(*) FROM users")
        total_u = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM files")
        total_f = cursor.fetchone()[0]
        cursor.execute("SELECT value FROM settings WHERE key='maintenance'")
        maint = cursor.fetchone()[0].upper()
        
        stats = f"🛠️ **إحصائيات البوت:**\n- إجمالي الطلاب: `{total_u}`\n- إجمالي الملفات: `{total_f}`\n- وضع الصيانة: `{maint}`"
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
        bot.answer_callback_query(call.id, f"تم تغيير وضع الصيانة إلى: {new_s.upper()}", show_alert=True)

    conn.close()


# ==================== الدوال التنفيذية لإدارة الطلاب والنقاط والصلاحيات ====================

def save_new_instructor_to_db(message):
    if not is_admin(message.from_user.id):
        return
    new_name = message.text.strip()
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO instructors (name) VALUES (?)", (new_name,))
        conn.commit()
        bot.reply_to(message, f"✅ **تم إضافة الأستاذ ({new_name}) بنجاح للقائمة والأزرار!**")
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
    bot.reply_to(message, f"✅ **تم حفظ الملف بنجاح!**\n- مرتبط بالأستاذ: `{instructor_name}`.")

def process_add_points(message):
    if not is_admin(message.from_user.id):
        return
    try:
        parts = message.text.strip().split()
        target_id = int(parts[0])
        pts = int(parts[1])
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET points = points + ? WHERE user_id = ?", (pts, target_id))
        conn.commit()
        conn.close()
        bot.reply_to(message, f"✅ **تم إضافة عدد ({pts}) نقطة** للطالب صاحب الآيدي: `{target_id}` بنجاح.")
    except Exception:
        bot.reply_to(message, "⚠️ صيغة خاطئة. تأكد من إرسال الآيدي ومسافة ثم عدد النقاط.")

def process_sub_points(message):
    if not is_admin(message.from_user.id):
        return
    try:
        parts = message.text.strip().split()
        target_id = int(parts[0])
        pts = int(parts[1])
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET points = MAX(0, points - ?) WHERE user_id = ?", (pts, target_id))
        conn.commit()
        conn.close()
        bot.reply_to(message, f"✅ **تم خصم عدد ({pts}) نقطة** من رصيد الطالب صاحب الآيدي: `{target_id}` بنجاح.")
    except Exception:
        bot.reply_to(message, "⚠️ صيغة خاطئة. تأكد من إرسال الآيدي ومسافة ثم عدد النقاط للخصم.")

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
            bot.reply_to(message, "⚠️ هذا المستخدم غير مسجل في قاعدة بيانات البوت.")
            conn.close()
            return
            
        new_ban = 0 if row[0] == 1 else 1
        cursor.execute("UPDATE users SET is_banned = ? WHERE user_id = ?", (new_ban, target_id))
        conn.commit()
        conn.close()
        
        status_text = "تم حظر الطالب بنجاح 🚫" if new_ban == 1 else "تم إلغاء حظر الطالب بنجاح ✅"
        bot.reply_to(message, status_text)
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
        bot.reply_to(message, f"👑 **تم تعيين المستخدم ({target_id}) كأدمن عام** للبوت بنجاح!")
    except Exception:
        bot.reply_to(message, "⚠️ آيدي غير صالح.")

def process_assign_section_perm(message):
    if not is_owner(message.from_user.id):
        return
    try:
        parts = message.text.strip().split()
        target_id = int(parts[0])
        sec_key = parts[1]
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO admin_permissions (user_id, section_key) VALUES (?, ?)", (target_id, sec_key))
        conn.commit()
        conn.close()
        bot.reply_to(message, f"✅ **تم منح صلاحية الإشراف** على القسم/المستوى (`{sec_key}`) للمستخدم (`{target_id}`) بنجاح.")
    except Exception:
        bot.reply_to(message, "⚠️ صيغة خاطئة. أرسل الآيدي مسافة ثم مفتاح المستوى (مثال: `123456 cyber_1`).")

def process_global_broadcast(message):
    if not is_owner(message.from_user.id):
        return
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users WHERE is_banned = 0")
    users = cursor.fetchall()
    conn.close()

    success, failed = 0, 0
    status_msg = bot.send_message(message.chat.id, "⏳ جاري إرسال الإذاعة لجميع الطلاب...")

    for u in users:
        try:
            bot.copy_message(chat_id=u[0], from_chat_id=message.chat.id, message_id=message.message_id)
            success += 1
        except Exception:
            failed += 1

    try:
        bot.edit_message_text(f"✅ **تمت الإذاعة بنجاح!**\n- تم الإرسال إلى: `{success}` طالب", message.chat.id, status_msg.message_id, parse_mode="Markdown")
    except Exception:
        pass

def admin_main_panel_edit(call):
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("🛡️ أدمن قسم الأمن السيبراني", callback_data="adm_fac_cyber"),
        types.InlineKeyboardButton("💻 أدمن قسم تقنية المعلومات (IT)", callback_data="adm_fac_it"),
        types.InlineKeyboardButton("🏛️ أدمن قسم الهندسة المعمارية", callback_data="adm_fac_arch"),
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


if __name__ == "__main__":
    print("🚀 البوت يعمل الآن بكفاءة 100% ومحمي من أخطاء السجلات...")
    while True:
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout=60)
        except Exception as e:
            print(f"⚠️ تنبيه إعادة اتصال: {e}")
