import subprocess
import sys

# التثبيت التلقائي الإجباري للمكتبة قبل أي عملية استيراد
try:
    import telebot
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyTelegramBotAPI"])
    import telebot

import sqlite3
from telebot import types

TOKEN = "8969629386:AAFbTJaSmJ-9ADKjSLazu4LXfvxFyExd35o"
bot = telebot.TeleBot(TOKEN)

# الآيدي الخاص بك كأدمن أساسي للبوت
OWNER_ID = 8083038345  

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

def is_admin(user_id):
    if user_id == OWNER_ID:
        return True
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT is_admin FROM users WHERE user_id = ?", (user_id,))
    res = cursor.fetchone()
    conn.close()
    return res and res[0] == 1

def log_action(admin_id, action):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO logs (admin_id, action) VALUES (?, ?)", (admin_id, action))
    conn.commit()
    conn.close()

def check_maintenance(user_id):
    if user_id == OWNER_ID or is_admin(user_id):
        return False
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key = 'maintenance'")
    res = cursor.fetchone()
    conn.close()
    return res and res[0] == 'on'


# ==================== الواجهة الرئيسية (Main Handlers) ====================

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    username = message.from_user.username
    fullname = message.from_user.full_name
    
    if check_maintenance(user_id):
        bot.reply_to(message, "🛠️ البوت في وضع الصيانة حالياً للتحديثات الدورية. يرجى العودة لاحقاً.")
        return

    conn = get_db()
    cursor = conn.cursor()
    admin_val = 1 if user_id == OWNER_ID else 0
    
    cursor.execute("SELECT is_banned FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    
    if row and row[0] == 1 and user_id != OWNER_ID:
        bot.reply_to(message, "❌ عذراً، تم حظرك من استخدام هذا البوت.")
        conn.close()
        return
        
    if not row:
        cursor.execute("INSERT INTO users (user_id, username, fullname, is_admin) VALUES (?, ?, ?, ?)",
                       (user_id, username, fullname, admin_val))
    else:
        if user_id == OWNER_ID:
            cursor.execute("UPDATE users SET is_admin = 1 WHERE user_id = ?", (user_id,))
            
    conn.commit()
    conn.close()

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("📂 تصفح الأقسام والملازم", "👨‍🏫 قسم الأساتذة والمواد")
    markup.add("⭐ نقاطي ومعلوماتي", "📞 التواصل والدعم الفني")
    
    if is_admin(user_id):
        markup.add("👑 لوحة تحكم الأدمن الشاملة")
        
    bot.send_message(message.chat.id, f"مرحباً بك يا {fullname} في البوت الأكاديمي الشامل 🎓\nاختر من الأزرار بالأسفل للبدء:", reply_markup=markup)


# ==================== الأقسام الأكاديمية للطلاب (المستويات والتخصصات) ====================

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
    if call.data == "fac_cyber":
        fac_name = "🛡️ الأمن السيبراني"
        prefix = "cyber"
    elif call.data == "fac_it":
        fac_name = "💻 تقنية معلومات (IT)"
        prefix = "it"
    else:
        fac_name = "🏛️ هندسة معمارية"
        prefix = "arch"
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("1️⃣ المستوى الأول", callback_data=f"lvl_{prefix}_1"),
        types.InlineKeyboardButton("2️⃣ المستوى الثاني", callback_data=f"lvl_{prefix}_2"),
        types.InlineKeyboardButton("3️⃣ المستوى الثالث", callback_data=f"lvl_{prefix}_3"),
        types.InlineKeyboardButton("4️⃣ المستوى الرابع", callback_data=f"lvl_{prefix}_4"),
        types.InlineKeyboardButton("🔙 العودة للتخصصات", callback_data="back_to_faculties")
    )
    bot.edit_message_text(f"📚 **{fac_name}**\nاختر المستوى الدراسي المطلوب لعرض محتوياته وأزّراره الخاصة:", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("lvl_"))
def show_level_content_and_controls(call):
    data_parts = call.data.split("_")
    prefix = data_parts[1] # cyber, it or arch
    level_num = data_parts[2] # 1, 2, 3, 4
    
    if prefix == "cyber":
        fac_title = "الأمن السيبراني"
    elif prefix == "it":
        fac_title = "تقنية المعلومات"
    else:
        fac_title = "الهندسة المعمارية"
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("📁 عرض ملازم وكتب هذا المستوى", callback_data=f"getfiles_{prefix}_{level_num}"),
        types.InlineKeyboardButton("📊 جدول المحاضرات والاختبارات", callback_data=f"schedule_{prefix}_{level_num}"),
        types.InlineKeyboardButton("💬 قروب النقاش الخاص بالمستوى", callback_data=f"group_{prefix}_{level_num}"),
        types.InlineKeyboardButton("🔙 العودة للمستويات", callback_data=f"fac_{prefix}")
    )
    bot.edit_message_text(f"🎓 **تخصص {fac_title} - المستوى {level_num}**\nاختر الإجراء أو المحتوى المطلوب:", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("getfiles_") or call.data.startswith("schedule_") or call.data.startswith("group_"))
def handle_level_actions(call):
    bot.answer_callback_query(call.id, "تم استلام الطلب. جاري عرض محتويات هذا القسم للمستوى المحدد.", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data == "back_to_faculties")
def back_to_faculties_handler(call):
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("🛡️ الأمن السيبراني", callback_data="fac_cyber"),
        types.InlineKeyboardButton("💻 تقنية معلومات (IT)", callback_data="fac_it"),
        types.InlineKeyboardButton("🏛️ هندسة معمارية", callback_data="fac_arch")
    )
    bot.edit_message_text("📂 **اختر التخصص الدراسي المطلوب:**", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")


# ==================== الأقسام العامة الأخرى ====================

@bot.message_handler(func=lambda msg: msg.text == "👨‍🏫 قسم الأساتذة والمواد")
def show_instructors(message):
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("📚 ملفات د. أكرم الحداد", callback_data="inst_اكرم_الحداد"),
        types.InlineKeyboardButton("📚 ملفات أ. فريال المقطري", callback_data="inst_فريال_المقطري"),
        types.InlineKeyboardButton("📚 ملفات أ. مصطفى", callback_data="inst_مصطفى"),
        types.InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="main_menu_cb")
    )
    bot.send_message(message.chat.id, "👨‍🏫 **اختر الأستاذ لعرض مواده وملفاته الدراسية:**", reply_markup=markup, parse_mode="Markdown")

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
            f"👤 **الملف الشخصي للطالب:**\n\n"
            f"▪️ الاسم: `{row[0]}`\n"
            f"▪️ الآيدي: `{user_id}`\n"
            f"▪️ الرتبة الأكاديمية: `{rank}`\n"
            f"▪️ رصيد النقاط: `⭐ {row[1]}`"
        )
        bot.reply_to(message, text, parse_mode="Markdown")

@bot.message_handler(func=lambda msg: msg.text == "📞 التواصل والدعم الفني")
def contact_support(message):
    bot.reply_to(message, "💬 لأي استفسار أو مشكلة تقنية تواجهك داخل البوت، يرجى التواصل مع إدارة البوت أو مشرف القسم.")


# ==================== لوحة تحكم الأدمن الرئيسية المقسمة ====================

@bot.message_handler(func=lambda msg: msg.text == "👑 لوحة تحكم الأدمن الشاملة")
def admin_main_panel(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "❌ عذراً، هذا القسم مخصص للمشرفين فقط.")
        return

    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("👥 قسم إدارة الطلاب والمستخدمين", callback_data="adm_sec_students"),
        types.InlineKeyboardButton("📁 قسم إدارة المحتوى والملفات", callback_data="adm_sec_content"),
        types.InlineKeyboardButton("🛡️ قسم إدارة المشرفين والصلاحيات", callback_data="adm_sec_admins"),
        types.InlineKeyboardButton("📢 الإذاعة والتنبيهات العامة", callback_data="adm_broadcast_start"),
        types.InlineKeyboardButton("🛠️ وضع الصيانة والإحصائيات", callback_data="adm_sec_system")
    )
    bot.send_message(message.chat.id, "👑 **لوحة التحكم الإدارية المركزية:**\nاختر القسم المطلوب لإدارة محتوياته بدقة:", reply_markup=markup, parse_mode="Markdown")


@bot.callback_query_handler(func=lambda call: call.data.startswith("adm_"))
def admin_sections_callbacks(call):
    user_id = call.from_user.id
    if not is_admin(user_id):
        bot.answer_callback_query(call.id, "غير مأذون لك بالدخول!", show_alert=True)
        return

    conn = get_db()
    cursor = conn.cursor()

    if call.data == "adm_sec_students":
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("🚫 حظر طالب من النظام", callback_data="user_ban_act"),
            types.InlineKeyboardButton("🟢 إلغاء حظر طالب", callback_data="user_unban_act"),
            types.InlineKeyboardButton("⭐ تعديل / تصفير نقاط طالب", callback_data="user_points_act"),
            types.InlineKeyboardButton("💬 إرسال تنبيه فردي لطالب", callback_data="extra_send_notice"),
            types.InlineKeyboardButton("🔙 رجوع للوحة الرئيسية", callback_data="adm_back_main")
        )
        bot.edit_message_text("👥 **قسم إدارة الطلاب:**\nتحكم بحسابات الطلاب، النقاط، والحظر:", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

    elif call.data == "adm_sec_content":
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("➕ رفع وإضافة ملف جديد للأقسام", callback_data="file_add_step"),
            types.InlineKeyboardButton("🗑️ حذف ملف من الأرشيف", callback_data="file_del_step"),
            types.InlineKeyboardButton("🔙 رجوع للوحة الرئيسية", callback_data="adm_back_main")
        )
        bot.edit_message_text("📁 **قسم إدارة المحتوى والملفات:**\nتحكم بالملازم والملفات الدراسية:", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

    elif call.data == "adm_sec_admins":
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("👥 لوحة التحكم بالمشرفين والصلاحيات", callback_data="extra_perms"),
            types.InlineKeyboardButton("👑 ترقية طالب إلى أدمن", callback_data="user_promote_act"),
            types.InlineKeyboardButton("📦 سجل تدقيق نشاطات المشرفين (Logs)", callback_data="adm_logs_view"),
            types.InlineKeyboardButton("🔙 رجوع للوحة الرئيسية", callback_data="adm_back_main")
        )
        bot.edit_message_text("🛡️ **قسم إدارة المشرفين والصلاحيات:**\nإدارة الصلاحيات وسجلات التدقيق:", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

    elif call.data == "adm_sec_system":
        cursor.execute("SELECT COUNT(*) FROM users")
        total_u = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM files")
        total_f = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM users WHERE is_banned=1")
        banned_u = cursor.fetchone()[0]
        cursor.execute("SELECT value FROM settings WHERE key='maintenance'")
        maint_status = cursor.fetchone()[0].upper()
        
        stats = (
            f"🛠️ **قسم النظام وإحصائيات البوت:**\n\n"
            f"👥 إجمالي الطلاب المسجلين: `{total_u}`\n"
            f"🚫 عدد المحظورين: `{banned_u}`\n"
            f"📁 إجمالي الملفات المرفوعة: `{total_f}`\n"
            f"⚙️ حالة الصيانة الحالية: `{maint_status}`\n"
        )
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("🛠️ تبديل وضع الصيانة (تشغيل/إيقاف)", callback_data="adm_toggle_maint"),
            types.InlineKeyboardButton("📊 عرض الإحصائيات الأكاديمية الشاملة", callback_data="adm_statistics"),
            types.InlineKeyboardButton("🔙 رجوع للوحة الرئيسية", callback_data="adm_back_main")
        )
        bot.edit_message_text(stats, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

    elif call.data == "adm_broadcast_start":
        msg = bot.send_message(call.message.chat.id, "📢 أرسل الرسالة أو الوسائط التي تريد إذاعتها لجميع الطلاب الآن:")
        bot.register_next_step_handler(msg, process_global_broadcast)

    elif call.data == "adm_logs_view":
        cursor.execute("SELECT admin_id, action, timestamp FROM logs ORDER BY log_id DESC LIMIT 12")
        logs = cursor.fetchall()
        text = "📋 **سجلات نشاط المشرفين الأخيرة:**\n\n"
        for l in logs:
            text += f"▪️ المشرف: `{l[0]}`\n⚙️ الإجراء: {l[1]}\n⏱️ الوقت: {l[2]}\n-------------------\n"
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 رجوع لقسم المشرفين", callback_data="adm_sec_admins"))
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

    elif call.data == "adm_toggle_maint":
        cursor.execute("SELECT value FROM settings WHERE key='maintenance'")
        current = cursor.fetchone()[0]
        new_state = 'off' if current == 'on' else 'on'
        cursor.execute("UPDATE settings SET value=? WHERE key='maintenance'", (new_state,))
        conn.commit()
        log_action(user_id, f"تغيير وضع الصيانة إلى: {new_state}")
        bot.answer_callback_query(call.id, f"تم تغيير وضع الصيانة بنجاح ليصبح: {new_state.upper()}", show_alert=True)

    elif call.data == "adm_statistics":
        cursor.execute("SELECT COUNT(*) FROM users")
        total_u = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM files")
        total_f = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM users WHERE is_banned=1")
        banned_u = cursor.fetchone()[0]
        stats = (
            f"📊 **تقرير الإحصائيات الأكاديمية:**\n\n"
            f"👥 إجمالي الطلاب: `{total_u}`\n"
            f"🚫 المحظورين: `{banned_u}`\n"
            f"📁 الملفات والملازم: `{total_f}`\n"
        )
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 رجوع لقسم النظام", callback_data="adm_sec_system"))
        bot.edit_message_text(stats, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

    elif call.data == "extra_perms":
        bot.answer_callback_query(call.id, "تم الاستلام بنجاح. هذه الوظيفة قيد التفعيل الكامل.", show_alert=True)

    elif call.data == "extra_send_notice":
        bot.answer_callback_query(call.id, "تم الاستلام بنجاح. هذه الوظيفة قيد التفعيل الكامل.", show_alert=True)

    elif call.data == "adm_back_main":
        admin_main_panel_edit(call)

    conn.close()

def admin_main_panel_edit(call):
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("👥 قسم إدارة الطلاب والمستخدمين", callback_data="adm_sec_students"),
        types.InlineKeyboardButton("📁 قسم إدارة المحتوى والملفات", callback_data="adm_sec_content"),
        types.InlineKeyboardButton("🛡️ قسم إدارة المشرفين والصلاحيات", callback_data="adm_sec_admins"),
        types.InlineKeyboardButton("📢 الإذاعة والتنبيهات العامة", callback_data="adm_broadcast_start"),
        types.InlineKeyboardButton("🛠️ وضع الصيانة والإحصائيات", callback_data="adm_sec_system")
    )
    bot.edit_message_text("👑 **لوحة التحكم الإدارية المركزية:**\nاختر القسم المطلوب لإدارة محتوياته بدقة:", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")


# ==================== نظام رفع الملفات عبر الأزرار التفاعلية ====================

@bot.callback_query_handler(func=lambda call: call.data == "file_add_step")
def ask_instructor_for_upload(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "غير مأذون لك!", show_alert=True)
        return
    bot.answer_callback_query(call.id)
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("📚 د. أكرم الحداد", callback_data="upinst_د. أكرم الحداد"),
        types.InlineKeyboardButton("📚 أ. فريال المقطري", callback_data="upinst_أ. فريال المقطري"),
        types.InlineKeyboardButton("📚 أ. مصطفى", callback_data="upinst_أ. مصطفى"),
        types.InlineKeyboardButton("📁 قسم عام / أخرى", callback_data="upinst_قسم عام"),
        types.InlineKeyboardButton("🔙 رجوع لقسم المحتوى", callback_data="adm_sec_content")
    )
    bot.edit_message_text("📤 **اختر الأستاذ أو القسم الذي تريد إضافة الملف إليه:**", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("upinst_"))
def receive_instructor_choice(call):
    if not is_admin(call.from_user.id):
        return
    instructor_name = call.data.replace("upinst_", "")
    bot.answer_callback_query(call.id)
    
    msg = bot.send_message(
        call.message.chat.id, 
        f"✅ لقد اخترت القسم: **{instructor_name}**\n\n📥 **أرسل الآن الملف (مستند، PDF، أو محاضرة)** وسيتم حفظه تلقائياً في هذا القسم:"
    )
    bot.register_next_step_handler(msg, lambda m: save_uploaded_file_by_choice(m, instructor_name))

def save_uploaded_file_by_choice(message, instructor_name):
    if not is_admin(message.from_user.id):
        return
    if not message.document and not message.video and not message.audio:
        bot.reply_to(message, "❌ يرجى إرسال ملف صحيح (مستند أو وسائط). أعد المحاولة من لوحة التحكم.")
        return
        
    file_id = message.document.file_id if message.document else message.video.file_id
    file_name = message.document.file_name if message.document else "ملف تعليمي"
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO files (category, instructor, file_id_tg, file_type, file_name) VALUES (?, ?, ?, ?, ?)",
                   (instructor_name, instructor_name, file_id, "document", file_name))
    conn.commit()
    conn.close()
    
    log_action(message.from_user.id, f"رفع ملف تفاعلي: {file_name} إلى {instructor_name}")
    bot.reply_to(message, f"🎉 **تم رفع وحفظ الملف بنجاح!**\n📂 القسم/الأستاذ: `{instructor_name}`\n📄 اسم الملف: `{file_name}`", parse_mode="Markdown")


def process_global_broadcast(message):
    if not is_admin(message.from_user.id):
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

    log_action(message.from_user.id, f"إذاعة عامة (نجاح: {success}, فشل: {failed})")
    bot.edit_message_text(f"✅ **تمت الإذاعة بنجاح!**\n- تم الإرسال إلى: `{success}` طالب\n- فشل لـ: `{failed}` مستخدم", 
                          message.chat.id, status_msg.message_id, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "main_menu_cb")
def back_to_main(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)
    send_welcome(call.message)


if __name__ == "__main__":
    print("🚀 البوت المطور والشامل يعمل الآن بكفاءة واستقرار تام...")
    while True:
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout=60)
        except Exception as e:
            print(f"⚠️ تنبيه - حدث استثناء وتم إعادة الاتصال تلقائياً: {e}")
