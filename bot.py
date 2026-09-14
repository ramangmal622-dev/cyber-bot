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
                <h1>🛡️ أكاديمية الأمن السيبراني (Cyber-Ops Empire v4.6) 🛡️</h1>
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
                "🥷 **مرحباً بك في أكاديمية الأمن السيبراني (Cyber-Ops Empire v4.6)**\n\n"
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

        if data == "admin_main":
            if not role:
                await query.answer("مرفوض! هذه المنطقة خاصة بالسيد والمشرفين فقط.", show_alert=True)
                return
            
            keyboard = [
                [InlineKeyboardButton("➕ إضافة قسم أساسي جديد", callback_data="admin_add_main_sec")],
                [InlineKeyboardButton("✏️ تعديل وإعادة تسمية الأقسام الرئيسية", callback_data="admin_edit_main_sec")],
                [InlineKeyboardButton("➕ إضافة فرع/قسم جديد داخل الأقسام", callback_data="admin_add_sub_sec")],
                [InlineKeyboardButton("✏️ تعديل وإعادة تسمية الأقسام والفروع", callback_data="admin_edit_sub_sec")],
                [InlineKeyboardButton("📢 البث الإذاعي الشامل لجميع الرعية", callback_data="admin_broadcast")],
                [InlineKeyboardButton("🧠 زرع تحدي واختبار سيبراني (Quiz)", callback_data="admin_add_quiz")],
                [InlineKeyboardButton("📤 رفع أداة أو ملف استخباراتي جديد", callback_data="admin_upload_file")],
                [InlineKeyboardButton("🗑️ حذف ملف أو عنصر من الأرشيف", callback_data="admin_delete_file")],
                [InlineKeyboardButton("🎓 إدارة الطلاب والتقييمات والدرجات", callback_data="admin_manage_students")],
                [InlineKeyboardButton("📬 فحص ومراجعة الواجبات المقدمة", callback_data="admin_view_submissions")],
                [InlineKeyboardButton("🛡️ مراجعة تقارير الثغرات الأمنية", callback_data="admin_view_vulns")],
                [InlineKeyboardButton("📞 متابعة تذاكر دعم ورسائل الرعية", callback_data="admin_support_tickets")],
                [InlineKeyboardButton("👥 لوحة التحكم بالمشرفين والصلاحيات", callback_data="admin_manage_admins")],
                [InlineKeyboardButton("📜 سجل تدقيق نشاطات المشرفين (Logs)", callback_data="admin_view_audit_logs")],
                [InlineKeyboardButton("⛔ حظر طالب من النظام", callback_data="admin_ban_student")],
                [InlineKeyboardButton("🟢 إلغاء حظر طالب", callback_data="admin_unban_student")],
                [InlineKeyboardButton("💬 إرسال تنبيه فردي لطالب", callback_data="admin_send_private_msg")],
                [InlineKeyboardButton("📊 عرض إحصائيات الأكاديمية", callback_data="admin_academy_stats")],
                [InlineKeyboardButton("🧹 تصفير نقاط طالب", callback_data="admin_reset_points")],
                [InlineKeyboardButton("⬅️ رجوع للرئيسية", callback_data="back_home")]
            ]
            
            await query.edit_message_text(
                text=f"👑 **غرفة القيادة العليا (مستوى السيادة: `{role}`):**\nاختر العملية الإدارية المطلوبة:",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

        elif data == "admin_view_audit_logs":
            if not role:
                return
            conn = sqlite3.connect("dark_cyber_academy.db")
            cursor = conn.cursor()
            cursor.execute("SELECT admin_id, action_desc, timestamp FROM audit_logs ORDER BY id DESC LIMIT 10")
            rows = cursor.fetchall()
            conn.close()
            text = "📊 **آخر سجلات العمليات والإدارة:**\n\n"
            for r in rows:
                text += f"👤 المشرف: `{r[0]}`\n⚙️ الإجراء: {r[1]}\n⏱️ الوقت: {r[2]}\n------------------\n"
            await query.message.reply_text(text, parse_mode="Markdown")

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
        else:
            if role:
                await query.message.reply_text(f"⚙️ تم الاستلام بنجاح. هذه الوظيفة قيد التفعيل الكامل.")
    except Exception as e:
        logger.error(f"Error in button_handler: {e}")

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_user.id
        text = update.message.text
        
        if is_student_banned(user_id) or user_id not in admin_state:
            return

        state = admin_state[user_id]
        action = state.get("action")

        if action == "wait_self_registration_name":
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
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
        
        print("Starting Flask Web Server & Telegram Bot Polling simultaneously...")
        app.run_polling()
    except Exception as e:
        logger.critical(f"Critical error starting bot: {e}")

if __name__ == "__main__":
    main()
