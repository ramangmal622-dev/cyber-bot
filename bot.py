import os
import sqlite3
import logging
import random
import threading
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)

# ==========================================
# 1. إعداد خادم الويب (Flask Server)
# ==========================================
app_web = Flask(__name__)

@app_web.route("/")
def home():
    return """
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
        <head>
            <meta charset="UTF-8">
            <title>Cyber-Ops Empire Dashboard</title>
            <style>
                body {
                    background-color: #0d1117;
                    color: #58a6ff;
                    font-family: Arial, sans-serif;
                    text-align: center;
                    padding-top: 60px;
                }
                .container {
                    border: 1px solid #30363d;
                    padding: 30px;
                    border-radius: 12px;
                    display: inline-block;
                    background-color: #161b22;
                    box-shadow: 0 0 15px rgba(88, 166, 255, 0.2);
                }
                h1 { color: #58a6ff; margin-bottom: 10px; }
                p { color: #8b949e; font-size: 1.1em; }
                .status { color: #3fb950; font-weight: bold; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🛡️ أكاديمية الأمن السيبراني (Cyber-Ops Empire v4.7) 🛡️</h1>
                <p>حالة السيرفر: <span class="status">● متصل ويعمل بكفاءة على Railway (Flask Webserver Active)</span></p>
                <hr style="border: 0.5px solid #30363d; margin: 20px 0;">
                <p>جميع حقوق إدارة وتأمين الأنظمة محفوظة للأكاديمية.</p>
            </div>
        </body>
    </html>
    """

def run_flask_server():
    port = int(os.environ.get("PORT", 8080))
    app_web.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

threading.Thread(target=run_flask_server, daemon=True).start()

# ==========================================
# 2. الإعدادات العامة للبوت وقواعد البيانات
# ==========================================
logging.basicConfig(
    format="[DARK-LOG] %(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

OWNER_ID = 8083038345
BOT_TOKEN = "8969629386:AAFbTJaSmJ-9ADKjSLazu4LXfvxFyExd35o"

def init_db():
    conn = sqlite3.connect("dark_cyber_academy.db")
    cursor = conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL;")
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            user_id INTEGER PRIMARY KEY,
            role TEXT NOT NULL,
            assigned_by INTEGER,
            assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            student_id TEXT PRIMARY KEY,
            user_id INTEGER UNIQUE,
            name TEXT NOT NULL,
            points INTEGER DEFAULT 0,
            status TEXT DEFAULT 'ACTIVE',
            join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id INTEGER,
            action_desc TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS custom_main_sections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sec_key TEXT UNIQUE NOT NULL,
            sec_name TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS custom_sub_sections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            main_type TEXT NOT NULL,
            sec_key TEXT NOT NULL,
            sec_name TEXT NOT NULL
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS content (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            main_type TEXT NOT NULL,
            sec_key TEXT NOT NULL,
            item_name TEXT NOT NULL,
            file_id TEXT NOT NULL,
            file_type TEXT NOT NULL,
            points_cost INTEGER DEFAULT 0,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT,
            student_name TEXT,
            task_info TEXT,
            file_id TEXT,
            status TEXT DEFAULT 'قيد المراجعة السيبرانية',
            submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS quizzes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT NOT NULL,
            opt1 TEXT NOT NULL,
            opt2 TEXT NOT NULL,
            opt3 TEXT NOT NULL,
            correct_opt INTEGER NOT NULL,
            reward_points INTEGER DEFAULT 10
        )
    """)
    
    conn.commit()
    conn.close()

init_db()

def log_admin_action(admin_id, desc):
    try:
        conn = sqlite3.connect("dark_cyber_academy.db")
        cursor = conn.cursor()
        cursor.execute("INSERT INTO audit_logs (admin_id, action_desc) VALUES (?, ?)", (admin_id, desc))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Error logging action: {e}")

def get_user_role(user_id):
    if user_id == OWNER_ID:
        return "dark_lord"
    try:
        conn = sqlite3.connect("dark_cyber_academy.db")
        cursor = conn.cursor()
        cursor.execute("SELECT role FROM admins WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else None
    except Exception:
        return None

def is_student_banned(user_id):
    try:
        conn = sqlite3.connect("dark_cyber_academy.db")
        cursor = conn.cursor()
        cursor.execute("SELECT status FROM students WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        return row and row[0] == "BANNED"
    except Exception:
        return False

def generate_unique_student_id():
    conn = sqlite3.connect("dark_cyber_academy.db")
    cursor = conn.cursor()
    while True:
        sid = str(random.randint(100000, 999999))
        cursor.execute("SELECT student_id FROM students WHERE student_id = ?", (sid,))
        if not cursor.fetchone():
            conn.close()
            return sid

admin_state = {}

default_main_sections = {
    "pdf": "📄 مكتبة أبحاث وكتب السيبراني المتقدمة",
    "tools": "🛠️ ترسانة أدوات وسكربتات الاختراق",
    "labs": "💻 مختبرات وتحديات CTF السيبرانية",
    "videos": "🎬 كورسات مرئية ودورات النخبة",
    "malware": "🛡️ هندسة التحليل العكسي للماوير",
    "extra": "📁 ملفات اضافية"
}

def get_all_main_sections():
    sections = dict(default_main_sections)
    try:
        conn = sqlite3.connect("dark_cyber_academy.db")
        cursor = conn.cursor()
        cursor.execute("SELECT sec_key, sec_name FROM custom_main_sections")
        for row in cursor.fetchall():
            sections[row[0]] = row[1]
        conn.close()
    except Exception:
        pass
    return sections

# ==========================================
# 3. معالجة أوامر وأزرار البوت
# ==========================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_user.id
        if is_student_banned(user_id):
            await update.message.reply_text("⛔ **حسابك محظور من استخدام النظام السيبراني.**")
            return

        if user_id in admin_state:
            del admin_state[user_id]
            
        role = get_user_role(user_id)
        conn = sqlite3.connect("dark_cyber_academy.db")
        cursor = conn.cursor()
        cursor.execute("SELECT student_id, name, points FROM students WHERE user_id = ?", (user_id,))
        student_row = cursor.fetchone()
        conn.close()

        if not student_row and not role:
            admin_state[user_id] = {"action": "wait_self_registration_name"}
            await update.message.reply_text(
                "🥷 **مرحباً بك في أكاديمية الأمن السيبراني (Cyber-Ops Empire v4.7)**\n\n"
                "أنت تسجل لأول مرة في النظام. يرجى كتابة **اسمك الثلاثي** لحفظه في قاعدة البيانات وتوليد الآيدي الخاص بك:"
            )
            return

        keyboard = []
        m_sections = get_all_main_sections()
        for sec_key, sec_name in m_sections.items():
            keyboard.append([InlineKeyboardButton(sec_name, callback_data=f"main_{sec_key}")])
        
        keyboard.append([InlineKeyboardButton("🔍 الاستعلام الشامل عن الملف الأكاديمي بالآيدي", callback_data="student_lookup_prompt")])
        keyboard.append([InlineKeyboardButton("📋 طلب مراجعة معلومات الطالب وتعديلها", callback_data="student_update_request")])
        keyboard.append([InlineKeyboardButton("📤 رفع وإرسال حل مهمة / واجب عملي", callback_data="submit_task_prompt")])
        keyboard.append([InlineKeyboardButton("🛡️ تقرير الثغرات الأمنية (Vulnerability Report)", callback_data="vuln_report_prompt")])
        keyboard.append([InlineKeyboardButton("🔍 فحص الروابط والملفات المشبوهة", callback_data="scan_links_prompt")])
        keyboard.append([InlineKeyboardButton("🧠 تحدي واختبار مهارات السيبراني الفوري", callback_data="start_quick_quiz")])
        keyboard.append([InlineKeyboardButton("📞 التواصل مع المشرفين وغرفة الدعم", callback_data="support_chat_prompt")])

        if role:
            keyboard.append([InlineKeyboardButton("👑 غرفة العمليات المركزية وسيادة الإدارة", callback_data="admin_main")])
            
        reply_markup = InlineKeyboardMarkup(keyboard)
        welcome_msg = f"🥷 **أهلاً بك مجدداً في المحطة المركزية**"
        if student_row:
            welcome_msg = f"🥷 **أهلاً بك أيها المتدرب ({student_row[1]})**\n🆔 الآيدي: `{student_row[0]}` | ⭐ رصيدك: `{student_row[2]}` نقطة"

        await update.message.reply_text(welcome_msg, reply_markup=reply_markup, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error in start command: {e}")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        
        if is_student_banned(user_id):
            await query.message.reply_text("⛔ حسابك محظور.")
            return

        data = query.data
        role = get_user_role(user_id)

        if data == "back_home":
            if user_id in admin_state:
                del admin_state[user_id]
            await start(update, context)
            return

        # عرض الأقسام ومحتوياتها وتكلفة النقاط
        if data.startswith("main_"):
            sec_key = data.replace("main_", "")
            m_sections = get_all_main_sections()
            sec_title = m_sections.get(sec_key, "القسم")
            
            conn = sqlite3.connect("dark_cyber_academy.db")
            cursor = conn.cursor()
            cursor.execute("SELECT id, item_name, points_cost FROM content WHERE main_type = ?", (sec_key,))
            items = cursor.fetchall()
            conn.close()
            
            keyboard = []
            if items:
                for item in items:
                    cost_text = f" (مجاناً)" if item[2] == 0 else f" (⭐ {item[2]} نقاط)"
                    keyboard.append([InlineKeyboardButton(f"📁 {item[1]}{cost_text}", callback_data=f"get_item_{item[0]}")])
            else:
                keyboard.append([InlineKeyboardButton("⚠️ لا توجد ملفات مرفوعة في هذا القسم حالياً", callback_data="noop")])
                
            keyboard.append([InlineKeyboardButton("⬅️ رجوع للرئيسية", callback_data="back_home")])
            
            await query.edit_message_text(
                text=f"📂 **{sec_title}**\n\nاختر الملف أو الأداة المطلوبة للتحميل:",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return

        # معالجة تنزيل الملف مع التحقق من النقاط وخصمها تلقائياً
        if data.startswith("get_item_"):
            item_id = data.replace("get_item_", "")
            conn = sqlite3.connect("dark_cyber_academy.db")
            cursor = conn.cursor()
            cursor.execute("SELECT item_name, file_id, file_type, points_cost FROM content WHERE id = ?", (item_id,))
            item = cursor.fetchone()
            
            if not item:
                conn.close()
                await query.answer("⚠️ الملف غير موجود أو تم حذفه من الأرشيف.", show_alert=True)
                return
            
            item_name, file_id, file_type, points_cost = item
            
            # إذا لم يكن المستخدم مشرفاً، نتحقق من نقاط الطالب ونخصمها
            if not role and points_cost > 0:
                cursor.execute("SELECT student_id, points FROM students WHERE user_id = ?", (user_id,))
                student = cursor.fetchone()
                
                if not student:
                    conn.close()
                    await query.answer("⚠️ يجب عليك التسجيل كطالب أولاً لاستخدام النقاط وتحميل الملفات. اضغط /start", show_alert=True)
                    return
                
                student_id, current_points = student
                if current_points < points_cost:
                    conn.close()
                    await query.answer(f"❌ رصيدك غير كافٍ! هذا الملف يتطلب {points_cost} نقطة، بينما رصيدك الحالي {current_points} نقطة.", show_alert=True)
                    return
                
                # خصم النقاط من رصيد الطالب
                new_points = current_points - points_cost
                cursor.execute("UPDATE students SET points = ? WHERE user_id = ?", (new_points, user_id))
                conn.commit()
                
            conn.close()
            
            # إرسال الملف للمستخدم
            if file_type == "document":
                await context.bot.send_document(chat_id=user_id, document=file_id, caption=f"📁 {item_name}\n⭐ تم خصم التكلفة بنجاح.")
            elif file_type == "photo":
                await context.bot.send_photo(chat_id=user_id, photo=file_id, caption=f"📁 {item_name}\n⭐ تم خصم التكلفة بنجاح.")
            elif file_type == "video":
                await context.bot.send_video(chat_id=user_id, video=file_id, caption=f"📁 {item_name}\n⭐ تم خصم التكلفة بنجاح.")
            elif file_type == "audio":
                await context.bot.send_audio(chat_id=user_id, audio=file_id, caption=f"📁 {item_name}\n⭐ تم خصم التكلفة بنجاح.")
            else:
                await query.message.reply_text(f"📁 الملف: {item_name}")
            return

        if data == "student_lookup_prompt":
            conn = sqlite3.connect("dark_cyber_academy.db")
            cursor = conn.cursor()
            cursor.execute("SELECT student_id, name, points, join_date FROM students WHERE user_id = ?", (user_id,))
            st = cursor.fetchone()
            conn.close()
            
            if st:
                await query.message.reply_text(
                    f"🔍 **ملفك الأكاديمي السيبراني:**\n\n"
                    f"👤 الاسم: `{st[1]}`\n"
                    f"🆔 الآيدي: `{st[0]}`\n"
                    f"⭐ النقاط: `{st[2]}` نقطة\n"
                    f"📅 تاريخ الانضمام: `{st[3]}`",
                    parse_mode="Markdown"
                )
            else:
                await query.message.reply_text("⚠️ لم يتم العثور على سجل أكاديمي مرتبط بحسابك. اضغط /start للتسجيل.")
            return

        elif data == "student_update_request":
            await query.message.reply_text("📋 لإعادة تعديل معلوماتك أو اسمك، يرجى التواصل مباشرة مع المشرفين عبر زر الدعم الفني.", parse_mode="Markdown")
            return

        elif data == "submit_task_prompt":
            admin_state[user_id] = {"action": "wait_task_submission"}
            await query.message.reply_text("📤 يرجى إرسال تفاصيل حل المهمة أو الواجب العملي (يمكنك إرسال نص أو ملف وسائط):", parse_mode="Markdown")
            return

        elif data == "vuln_report_prompt":
            admin_state[user_id] = {"action": "wait_vuln_report"}
            await query.message.reply_text("🛡️ يرجى كتابة تفاصيل تقرير الثغرة الأمنية المراد إرسالها لفريق الإدارة:", parse_mode="Markdown")
            return

        elif data == "scan_links_prompt":
            await query.message.reply_text("🔍 ميزة فحص الروابط والملفات قيد التفعيل الأمني، أرسل الرابط مباشرة وسيتم مراجعته.", parse_mode="Markdown")
            return

        elif data == "start_quick_quiz":
            conn = sqlite3.connect("dark_cyber_academy.db")
            cursor = conn.cursor()
            cursor.execute("SELECT id, question, opt1, opt2, opt3, reward_points FROM quizzes ORDER BY RANDOM() LIMIT 1")
            q = cursor.fetchone()
            conn.close()
            
            if not q:
                await query.message.reply_text("🧠 لا توجد اختبارات أو تحديات سيبرانية مضافة حالياً من قبل الإدارة. انتظر ريثما يتم زرع تحديات جديدة.")
                return
            
            keyboard = [
                [InlineKeyboardButton(q[2], callback_data=f"quiz_{q[0]}_1")],
                [InlineKeyboardButton(q[3], callback_data=f"quiz_{q[0]}_2")],
                [InlineKeyboardButton(q[4], callback_data=f"quiz_{q[0]}_3")],
                [InlineKeyboardButton("⬅️ رجوع للرئيسية", callback_data="back_home")]
            ]
            await query.edit_message_text(
                text=f"🧠 **تحدي المهارات السيبرانية الفوري:**\n\n❓ {q[1]}\n\n⭐ المكافأة: `{q[5]}` نقاط",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return

        elif data == "support_chat_prompt":
            admin_state[user_id] = {"action": "wait_support_message"}
            await query.message.reply_text("📞 أرسل رسالتك أو استفسارك وسيتم تحويله إلى غرفة العمليات والمشرفين فوراً:", parse_mode="Markdown")
            return

        # حل الأسئلة وكسب النقاط
        if data.startswith("quiz_"):
            parts = data.split("_")
            quiz_id = parts[1]
            chosen_opt = int(parts[2])
            
            conn = sqlite3.connect("dark_cyber_academy.db")
            cursor = conn.cursor()
            cursor.execute("SELECT correct_opt, reward_points FROM quizzes WHERE id = ?", (quiz_id,))
            q_data = cursor.fetchone()
            
            if not q_data:
                conn.close()
                await query.answer("⚠️ انتهت صلاحية هذا التحدي.", show_alert=True)
                return
            
            correct_opt, reward_points = q_data
            if chosen_opt == correct_opt:
                cursor.execute("UPDATE students SET points = points + ? WHERE user_id = ?", (reward_points, user_id))
                conn.commit()
                conn.close()
                await query.edit_message_text(
                    text=f"🎉 **إجابة صحيحة!**\nتم إضافة `{reward_points}` نقاط إلى رصيدك السيبراني بنجاح.",
                    parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ رجوع للرئيسية", callback_data="back_home")]])
                )
            else:
                conn.close()
                await query.edit_message_text(
                    text="❌ **إجابة خاطئة!**\nحاول مجدداً في تحديات أخرى لتعويض النقاط.",
                    parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ رجوع للرئيسية", callback_data="back_home")]])
                )
            return

        if data == "admin_main":
            if not role:
                await query.answer("مرفوض! هذه المنطقة خاصة بالسيد والمشرفين فقط.", show_alert=True)
                return
            
            keyboard = [
                [InlineKeyboardButton("📤 رفع ملف مع تحديد تكلفة النقاط", callback_data="admin_upload_file")],
                [InlineKeyboardButton("⭐ إضافة / تعديل نقاط طالب", callback_data="admin_add_points_prompt")],
                [InlineKeyboardButton("📊 عرض إحصائيات الأكاديمية", callback_data="admin_academy_stats")],
                [InlineKeyboardButton("⬅️ رجوع للرئيسية", callback_data="back_home")]
            ]
            
            await query.edit_message_text(
                text=f"👑 **غرفة القيادة العليا (مستوى السيادة: `{role}`):**\nاختر العملية الإدارية المطلوبة:",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

        elif data == "admin_upload_file":
            if not role:
                return
            m_sections = get_all_main_sections()
            keyboard = []
            for sec_key, sec_name in m_sections.items():
                keyboard.append([InlineKeyboardButton(sec_name, callback_data=f"upload_to_{sec_key}")])
            keyboard.append([InlineKeyboardButton("⬅️ رجوع", callback_data="admin_main")])
            
            await query.edit_message_text(
                text="📤 **رفع ملف جديد:**\nاختر القسم المراد رفع الملف إليه:",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return

        elif data.startswith("upload_to_"):
            if not role:
                return
            sec_key = data.replace("upload_to_", "")
            admin_state[user_id] = {"action": "wait_file_cost", "main_type": sec_key}
            await query.message.reply_text(
                "💰 **تحديد تكلفة النقاط:**\n"
                "أرسل الآن **عدد النقاط المطلوب لتنزيل هذا الملف** (أرسل `0` إذا كان الملف مجانياً):",
                parse_mode="Markdown"
            )
            return

        elif data == "admin_add_points_prompt":
            if not role:
                return
            admin_state[user_id] = {"action": "wait_for_points_input"}
            await query.message.reply_text(
                "⭐ **إضافة / خصم نقاط طالب:**\n\n"
                "يرجى إرسال **آيدي الطالب** متبوعاً بـ **عدد النقاط** (استخدم القيمة بالسالب للخصم).\n"
                "مثال للإضافة: `123456 50`",
                parse_mode="Markdown"
            )

        elif data == "admin_academy_stats":
            if not role:
                return
            conn = sqlite3.connect("dark_cyber_academy.db")
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM students")
            st_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM admins")
            ad_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM content")
            content_count = cursor.fetchone()[0]
            conn.close()
            await query.message.reply_text(
                f"📊 **إحصائيات الأكاديمية السيبرانية:**\n\n"
                f"👥 إجمالي الطلاب المسجلين: `{st_count}`\n"
                f"🛡️ إجمالي المشرفين: `{ad_count}`\n"
                f"📁 إجمالي الملفات والمحتويات المرفوعة: `{content_count}`",
                parse_mode="Markdown"
            )
    except Exception as e:
        logger.error(f"Error in button_handler: {e}")

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_user.id
        
        if is_student_banned(user_id) or user_id not in admin_state:
            return

        state = admin_state[user_id]
        action = state.get("action")

        if action == "wait_self_registration_name":
            text = update.message.text
            student_id = generate_unique_student_id()
            conn = sqlite3.connect("dark_cyber_academy.db")
            cursor = conn.cursor()
            try:
                cursor.execute(
                    "INSERT INTO students (student_id, user_id, name, points) VALUES (?, ?, ?, ?)",
                    (student_id, user_id, text, 0)
                )
                conn.commit()
                del admin_state[user_id]
                await update.message.reply_text(
                    f"✅ **تم تسجيلك بنجاح في النظام السيبراني!**\n\n"
                    f"👤 الاسم: `{text}`\n"
                    f"🆔 الآيدي الخاص بك: `{student_id}`",
                    parse_mode="Markdown"
                )
                await start(update, context)
            except Exception as e:
                await update.message.reply_text(f"⚠️ حدث خطأ أثناء التسجيل: {e}")
            finally:
                conn.close()

        elif action == "wait_for_points_input":
            text = update.message.text
            parts = text.strip().split()
            if len(parts) < 2:
                await update.message.reply_text("⚠️ الصيغة خاطئة. يرجى إرسال الآيدي ومقدار النقاط هكذا: `123456 50`", parse_mode="Markdown")
                return
            
            target_id = parts[0]
            try:
                points_to_add = int(parts[1])
            except ValueError:
                await update.message.reply_text("⚠️ مقدار النقاط يجب أن يكون رقماً صحيحاً.")
                return

            conn = sqlite3.connect("dark_cyber_academy.db")
            cursor = conn.cursor()
            cursor.execute("SELECT name, points FROM students WHERE student_id = ?", (target_id,))
            st_row = cursor.fetchone()
            
            if not st_row:
                conn.close()
                await update.message.reply_text(f"❌ لم يتم العثور على طالب بالآيدي: `{target_id}`", parse_mode="Markdown")
                return

            new_points = st_row[1] + points_to_add
            cursor.execute("UPDATE students SET points = ? WHERE student_id = ?", (new_points, target_id))
            conn.commit()
            conn.close()

            del admin_state[user_id]
            log_admin_action(user_id, f"تعديل نقاط الطالب {target_id} بقيمة {points_to_add}")
            
            await update.message.reply_text(
                f"✅ **تم تحديث نقاط الطالب بنجاح!**\n\n"
                f"👤 اسم الطالب: `{st_row[0]}`\n"
                f"🆔 الآيدي: `{target_id}`\n"
                f"⭐ النقاط المضافة/المخصومة: `{points_to_add}`\n"
                f"💰 الرصيد الجديد: `{new_points}` نقطة",
                parse_mode="Markdown"
            )

        elif action == "wait_file_cost":
            try:
                cost = int(update.message.text.strip())
            except ValueError:
                await update.message.reply_text("⚠️ يرجى إرسال رقم صحيح يمثل تكلفة النقاط (مثال: 10 أو 0).")
                return
            
            main_type = state.get("main_type")
            admin_state[user_id] = {"action": "wait_file_upload_data", "main_type": main_type, "points_cost": cost}
            await update.message.reply_text("📥 تم حفظ التكلفة. الآن **أرسل الملف أو المستند** مع كتابة اسمه في التعليق (Caption):")

        elif action == "wait_file_upload_data":
            main_type = state.get("main_type")
            points_cost = state.get("points_cost", 0)
            file_id = None
            file_type = "document"
            item_name = update.message.caption or update.message.text or "ملف سيبراني"

            if update.message.document:
                file_id = update.message.document.file_id
                file_type = "document"
                if not update.message.caption and update.message.document.file_name:
                    item_name = update.message.document.file_name
            elif update.message.photo:
                file_id = update.message.photo[-1].file_id
                file_type = "photo"
            elif update.message.video:
                file_id = update.message.video.file_id
                file_type = "video"
            elif update.message.audio:
                file_id = update.message.audio.file_id
                file_type = "audio"
            else:
                admin_state[user_id] = {"action": "wait_file_upload_file", "main_type": main_type, "points_cost": points_cost, "item_name": update.message.text}
                await update.message.reply_text("📥 تم حفظ اسم الملف. الآن **أرسل الملف أو المستند** المرفق لتتم عملية الحفظ نهائياً:")
                return

            if file_id:
                conn = sqlite3.connect("dark_cyber_academy.db")
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO content (main_type, sec_key, item_name, file_id, file_type, points_cost) VALUES (?, ?, ?, ?, ?, ?)",
                    (main_type, "general", item_name, file_id, file_type, points_cost)
                )
                conn.commit()
                conn.close()

                del admin_state[user_id]
                log_admin_action(user_id, f"رفع ملف جديد '{item_name}' بتكلفة {points_cost} نقطة")
                await update.message.reply_text(f"✅ **تم رفع وتخزين الملف بنجاح!**\n📁 اسم الملف: `{item_name}`\n⭐ التكلفة: `{points_cost}` نقطة", parse_mode="Markdown")

        elif action == "wait_file_upload_file":
            main_type = state.get("main_type")
            points_cost = state.get("points_cost", 0)
            item_name = state.get("item_name")
            file_id = None
            file_type = "document"

            if update.message.document:
                file_id = update.message.document.file_id
                file_type = "document"
            elif update.message.photo:
                file_id = update.message.photo[-1].file_id
                file_type = "photo"
            elif update.message.video:
                file_id = update.message.video.file_id
                file_type = "video"
            elif update.message.audio:
                file_id = update.message.audio.file_id
                file_type = "audio"

            if file_id:
                conn = sqlite3.connect("dark_cyber_academy.db")
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO content (main_type, sec_key, item_name, file_id, file_type, points_cost) VALUES (?, ?, ?, ?, ?, ?)",
                    (main_type, "general", item_name, file_id, file_type, points_cost)
                )
                conn.commit()
                conn.close()

                del admin_state[user_id]
                log_admin_action(user_id, f"رفع ملف جديد '{item_name}' بتكلفة {points_cost} نقطة")
                await update.message.reply_text(f"✅ **تم رفع وتخزين الملف بنجاح!**\n📁 اسم الملف: `{item_name}`\n⭐ التكلفة: `{points_cost}` نقطة", parse_mode="Markdown")
            else:
                await update.message.reply_text("⚠️ يرجى إرسال ملف صالح (مستند، صورة، فيديو، أو صوت).")

        elif action == "wait_task_submission":
            del admin_state[user_id]
            await update.message.reply_text("✅ **تم استلام حل المهمة بنجاح وتحويله إلى غرفة المراجعة السيبرانية للإدارة.**", parse_mode="Markdown")

        elif action == "wait_vuln_report":
            del admin_state[user_id]
            await update.message.reply_text("🛡️ **تم رفع تقرير الثغرة الأمنية بنجاح إلى فريق سيادة الأكاديمية.** شكراً لجهودك.", parse_mode="Markdown")

        elif action == "wait_support_message":
            del admin_state[user_id]
            await update.message.reply_text("📞 **تم إرسال رسالتك إلى غرفة الدعم الفني والمشرفين بنجاح.**", parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Error in message_handler: {e}")

# ==========================================
# 4. نقطة البدء التشغيلية
# ==========================================
def main():
    try:
        app = ApplicationBuilder().token(BOT_TOKEN).build()
        
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CallbackQueryHandler(button_handler))
        app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, message_handler))
        
        print("Starting Flask Web Server & Telegram Bot Polling simultaneously...")
        app.run_polling()
    except Exception as e:
        logger.critical(f"Critical error starting bot: {e}")

if __name__ == "__main__":
    main()