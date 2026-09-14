import sqlite3
import telebot
from telebot import types

TOKEN = "YOUR_BOT_TOKEN_HERE"
bot = telebot.TeleBot(TOKEN)

# الآيدي الخاص بالأدمن الأساسي
OWNER_ID = 123456789  

# ==================== قاعدة البيانات والجدولة (Database Setup) ====================
def init_db():
    conn = sqlite3.connect('bot_database.db', check_same_thread=False)
    cursor = conn.cursor()
    
    # جدول المستخدمين والصلاحيات
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
    
    # جدول الأقسام والمحتوى الدراسي (مرتبط بالأساتذة / المواد)
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
    
    # سجلات النظام (Logs)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS logs (
            log_id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id INTEGER,
            action TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # إعدادات النظام (مثل وضع الصيانة)
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
    cursor.execute("SELECT is_banned FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    
    if row and row[0] == 1:
        bot.reply_to(message, "❌ عذراً، تم حظرك من استخدام هذا البوت.")
        conn.close()
        return
        
    if not row:
        admin_val = 1 if user_id == OWNER_ID else 0
        cursor.execute("INSERT OR IGNORE INTO users (user_id, username, fullname, is_admin) VALUES (?, ?, ?, ?)",
                       (user_id, username, fullname, admin_val))
        conn.commit()
    conn.close()

    # لوحة المفاتيح الرئيسية للطلاب والمستخدمين
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("📂 تصفح الأقسام والملازم", "👨‍🏫 قسم الأساتذة والمواد")
    markup.add("⭐ نقاطي ومعلوماتي", "📞 التواصل والدعم الفني")
    
    if is_admin(user_id):
        markup.add("👑 لوحة تحكم الأدمن الشاملة")
        
    bot.send_message(message.chat.id, f"مرحباً بك يا {fullname} في البوت الأكاديمي الشامل 🎓\nاختر من الأزرار بالأسفل للبدء:", reply_markup=markup)


# ==================== الأقسام التفاعلية العامة ====================

@bot.message_handler(func=lambda msg: msg.text == "📂 تصفح الأقسام والملازم")
def show_categories(message):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT category FROM files")
    cats = cursor.fetchall()
    conn.close()

    markup = types.InlineKeyboardMarkup(row_width=2)
    if cats:
        for c in cats:
            markup.add(types.InlineKeyboardButton(f"📁 قسم: {c[0]}", callback_data=f"showcat_{c[0]}"))
    else:
        markup.add(types.InlineKeyboardButton("⚠️ لا توجد أقسام مضافة حالياً", callback_data="none"))
        
    bot.send_message(message.chat.id, "📁 **قائمة الأقسام الدراسية المتاحة:**", reply_markup=markup, parse_mode="Markdown")

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


# ==================== لوحة تحكم الأدمن الشاملة ومتفرعاتها ====================

@bot.message_handler(func=lambda msg: msg.text == "👑 لوحة تحكم الأدمن الشاملة")
def admin_main_panel(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "❌ عذراً، هذا القسم مخصص للمشرفين فقط.")
        return

    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📁 إدارة الملفات والمحتوى", callback_data="adm_sub_content"),
        types.InlineKeyboardButton("👥 إدارة الطلاب والنقاط", callback_data="adm_sub_users"),
        types.InlineKeyboardButton("📢 الإذاعة والتنبيهات", callback_data="adm_broadcast_start"),
        types.InlineKeyboardButton("📋 سجلات النظام (Logs)", callback_data="adm_logs_view"),
        types.InlineKeyboardButton("🛠️ وضع الصيانة", callback_data="adm_toggle_maint"),
        types.InlineKeyboardButton("📊 إحصائيات البوت", callback_data="adm_statistics")
    )
    bot.send_message(message.chat.id, "👑 **لوحة التحكم الإدارية المركزية:**\nاختر القسم المطلوب للتنفيذ:", reply_markup=markup, parse_mode="Markdown")


# معالجة أزرار الأدمن المتفرعة (Admin Sub-menus Callbacks)
@bot.callback_query_handler(func=lambda call: call.data.startswith("adm_"))
def admin_sub_callbacks(call):
    user_id = call.from_user.id
    if not is_admin(user_id):
        bot.answer_callback_query(call.id, "غير مأذون لك بالدخول!", show_alert=True)
        return

    conn = get_db()
    cursor = conn.cursor()

    # 1. فرع إدارة الملفات
    if call.data == "adm_sub_content":
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("➕ رفع وإضافة ملف جديد", callback_data="file_add_step"),
            types.InlineKeyboardButton("🗑️ حذف ملف من الأرشيف", callback_data="file_del_step"),
            types.InlineKeyboardButton("🔙 العودة للوحة الأدمن", callback_data="adm_back_main")
        )
        bot.edit_message_text("📁 **قسم إدارة المحتوى والملفات:**\nاختر الإجراء المناسب:", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

    # 2. فرع إدارة الطلاب والمستخدمين
    elif call.data == "adm_sub_users":
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("🚫 حظر طالب", callback_data="user_ban_act"),
            types.InlineKeyboardButton("✅ إلغاء حظر", callback_data="user_unban_act"),
            types.InlineKeyboardButton("⭐ تعديل نقاط طالب", callback_data="user_points_act"),
            types.InlineKeyboardButton("👑 ترقية لأدمن", callback_data="user_promote_act"),
            types.InlineKeyboardButton("🔙 العودة للوحة الأدمن", callback_data="adm_back_main")
        )
        bot.edit_message_text("👥 **قسم إدارة الطلاب والمستخدمين:**\nتحكم بصلاحيات وحسابات المستخدمين:", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

    # 3. البث الإذاعي
    elif call.data == "adm_broadcast_start":
        msg = bot.send_message(call.message.chat.id, "📢 أرسل الرسالة أو الوسائط التي تريد إذاعتها لجميع الطلاب الآن:")
        bot.register_next_step_handler(msg, process_global_broadcast)

    # 4. سجلات النظام
    elif call.data == "adm_logs_view":
        cursor.execute("SELECT admin_id, action, timestamp FROM logs ORDER BY log_id DESC LIMIT 12")
        logs = cursor.fetchall()
        text = "📋 **سجلات نشاط الأدمنز الأخيرة:**\n\n"
        for l in logs:
            text += f"▪️ الأدمن: `{l[0]}`\n⚙️ الإجراء: {l[1]}\n⏱️ الوقت: {l[2]}\n-------------------\n"
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="adm_sub_content"))
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

    # 5. وضع الصيانة
    elif call.data == "adm_toggle_maint":
        cursor.execute("SELECT value FROM settings WHERE key='maintenance'")
        current = cursor.fetchone()[0]
        new_state = 'off' if current == 'on' else 'on'
        cursor.execute("UPDATE settings SET value=? WHERE key='maintenance'", (new_state,))
        conn.commit()
        log_action(user_id, f"تغيير وضع الصيانة إلى: {new_state}")
        bot.answer_callback_query(call.id, f"تم تغيير وضع الصيانة بنجاح ليصبح: {new_state.upper()}", show_alert=True)

    # 6. إحصائيات البوت
    elif call.data == "adm_statistics":
        cursor.execute("SELECT COUNT(*) FROM users")
        total_u = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM files")
        total_f = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM users WHERE is_banned=1")
        banned_u = cursor.fetchone()[0]
        
        stats = (
            f"📊 **تقرير إحصائيات البوت الشاملة:**\n\n"
            f"👥 إجمالي الطلاب المسجلين: `{total_u}`\n"
            f"🚫 عدد المحظورين: `{banned_u}`\n"
            f"📁 إجمالي الملفات والملازم المرفوعة: `{total_f}`\n"
        )
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="adm_back_main"))
        bot.edit_message_text(stats, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

    elif call.data == "adm_back_main":
        admin_main_panel(call.message)

    conn.close()

# فرع تفاعلي لرفع الملفات (خطوات الإضافة)
@bot.callback_query_handler(func=lambda call: call.data == "file_add_step")
def ask_file_details(call):
    msg = bot.send_message(call.message.chat.id, "📤 أرسل الآن الملف (مستند، PDF، أو محاضرة) مع كتابة اسم القسم واسم الأستاذ في وصف الملف (Caption).")
    bot.register_next_step_handler(msg, save_uploaded_file)

def save_uploaded_file(message):
    if not is_admin(message.from_user.id):
        return
    if not message.document and not message.video and not message.audio:
        bot.reply_to(message, "❌ يرجى إرسال ملف صحيح (مستند أو وسائط).")
        return
        
    file_id = message.document.file_id if message.document else message.video.file_id
    file_name = message.document.file_name if message.document else "ملف تعليمي"
    caption = message.caption if message.caption else "عام / غير مصنف"
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO files (category, instructor, file_id_tg, file_type, file_name) VALUES (?, ?, ?, ?, ?)",
                   (caption, "عام", file_id, "document", file_name))
    conn.commit()
    conn.close()
    
    log_action(message.from_user.id, f"رفع ملف جديد: {file_name}")
    bot.reply_to(message, f"✅ تم حفظ الملف وتصنيفه بنجاح تحت: [{caption}]")

# معالجة البث الجماعي الآمن
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

# العودة للقائمة الرئيسية عبر الكولباك
@bot.callback_query_handler(func=lambda call: call.data == "main_menu_cb")
def back_to_main(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)
    send_welcome(call.message)


# تشغيل البوت باستقرار تام
if __name__ == "__main__":
    print("🚀 البوت المطور والشامل يعمل الآن بكفاءة واستقرار تام...")
    while True:
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout=60)
        except Exception as e:
            print(f"⚠️ تنبيه - حدث استثناء وتم إعادة الاتصال تلقائياً: {e}")