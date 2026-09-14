import os
import sqlite3
import logging
import random
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)

# إعداد خادم ويب بسيط لمنصة Railway لكي تظل الحاوية مفتوحة
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Cyber-Ops Empire Bot v4.6 is active and running!")

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), SimpleHandler)
    server.serve_forever()

threading.Thread(target=run_web_server, daemon=True).start()

logging.basicConfig(
    format="[DARK-LOG] %(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

OWNER_ID = 8083038345
BOT_TOKEN = "8969629386:AAFbTJaSmJ-9ADKjSLazu4LXfvxFyExd35o"

# الرابط الخاص بك على Railway
WEBHOOK_URL = "https://cyber-bot-production-e452.up.railway.app"
PORT = int(os.environ.get("PORT", 8080))

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
    conn = sqlite3.connect("dark_cyber_academy.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO audit_logs (admin_id, action_desc) VALUES (?, ?)", (admin_id, desc))
    conn.commit()
    conn.close()

def get_user_role(user_id):
    if user_id == OWNER_ID:
        return "dark_lord"
    conn = sqlite3.connect("dark_cyber_academy.db")
    cursor = conn.cursor()
    cursor.execute("SELECT role FROM admins WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None

def is_student_banned(user_id):
    conn = sqlite3.connect("dark_cyber_academy.db")
    cursor = conn.cursor()
    cursor.execute("SELECT status FROM students WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row and row[0] == "BANNED"

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
    conn = sqlite3.connect("dark_cyber_academy.db")
    cursor = conn.cursor()
    cursor.execute("SELECT sec_key, sec_name FROM custom_main_sections")
    for row in cursor.fetchall():
        sections[row[0]] = row[1]
    conn.close()
    return sections

base_sub_sections = {
    "pdf": {"net_sec": "📁 تأمين الشبكات والبروتوكولات المعقدة", "web_sec": "📁 ثغرات الـ Web العميقة والأمن العالي", "crypto": "📁 علم التشفير المتقدم والـ ECC"},
    "tools": {"recon": "🛠️ أدوات الاستطلاع والـ OSINT السرية", "exploit": "🛠️ إطارات وكور ثغرات الـ Zero-Day", "defend": "🛠️ أنظمة الدفاع والتصدّي الذكي"},
    "labs": {"ctf_easy": "💻 تحديات المبتدئين (Easy CTF)", "ctf_hard": "💻 تحديات الماستر (Advanced Pwn/Rev)", "forensics": "💻 التحقيق الجنائي الرقمي والطب الشرعي"},
    "videos": {"linux_adv": "🎬 احتراف هندسة لينكس والسكربتات الخفية", "pentest_full": "🎬 دبلوم اختبار الهجوم السيبراني الشامل"},
    "malware": {"static_an": "🛡️ التحليل الثابت العكسي للبرمجيات", "dynamic_an": "🛡️ التحليل الديناميكي والعزل في الـ Sandbox"},
    "extra": {"general_files": "📁 الأرشيف العام والملفات الإضافية"}
}

def get_all_sub_sections(main_type):
    subs = dict(base_sub_sections.get(main_type, {}))
    conn = sqlite3.connect("dark_cyber_academy.db")
    cursor = conn.cursor()
    cursor.execute("SELECT sec_key, sec_name FROM custom_sub_sections WHERE main_type = ?", (main_type,))
    for row in cursor.fetchall():
        subs[row[0]] = row[1]
    conn.close()
    return subs

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
            [InlineKeyboardButton("➕ إضافة نقاط للطالب", callback_data="admin_add_points_prompt")],
            [InlineKeyboardButton("⬅️ رجوع للرئيسية", callback_data="back_home")]
        ]
        await query.edit_message_text(text=f"👑 **غرفة القيادة العليا (مستوى السيادة: {role}):**", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "admin_add_points_prompt":
        if not role:
            await query.answer("مرفوض!", show_alert=True)
            return
        admin_state[user_id] = {"action": "wait_admin_add_points_id"}
        await query.message.reply_text("➕ **إضافة نقاط:**\nأرسل الآن **آيدي الطالب** المراد إضافة النقاط له:")

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

    elif action == "wait_admin_add_points_id":
        conn = sqlite3.connect("dark_cyber_academy.db")
        cursor = conn.cursor()
        cursor.execute("SELECT student_id, name, points FROM students WHERE student_id = ?", (text.strip(),))
        st = cursor.fetchone()
        conn.close()
        
        if not st:
            await update.message.reply_text("❌ لم يتم العثور على طالب بهذا الآيدي. أرسل الآيدي الصحيح مجدداً:")
            return
            
        admin_state[user_id] = {"action": "wait_admin_add_points_value", "target_student_id": st[0]}
        await update.message.reply_text(f"✅ تم العثور على الطالب: **{st[1]}** (الرصيد الحالي: {st[2]})\n\nأرسل الآن **عدد النقاط** المراد إضافتها:")

    elif action == "wait_admin_add_points_value":
        target_sid = state.get("target_student_id")
        try:
            points_to_add = int(text.strip())
        except ValueError:
            await update.message.reply_text("❌ يرجى إرسال رقم صحيح فقط:")
            return
            
        conn = sqlite3.connect("dark_cyber_academy.db")
        cursor = conn.cursor()
        cursor.execute("SELECT points, name FROM students WHERE student_id = ?", (target_sid,))
        st = cursor.fetchone()
        
        if st:
            current_pts, st_name = st
            new_pts = current_pts + points_to_add
            cursor.execute("UPDATE students SET points = ? WHERE student_id = ?", (new_pts, target_sid))
            conn.commit()  # الحفظ الإجباري لضمان ثبات النقاط
            
            log_admin_action(user_id, f"إضافة {points_to_add} نقطة للطالب {st_name} ({target_sid})")
            del admin_state[user_id]
            
            await update.message.reply_text(
                f"✅ **تمت إضافة النقاط بنجاح وثبتت في النظام!**\n\n"
                f"👤 الطالب: {st_name}\n"
                f"⭐ الرصيد الجديد: `{new_pts}` نقطة"
            )
        conn.close()
        await start(update, context)

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    
    print("Bot is running via Webhook...")
    
    # تشغيل الـ Webhook الصحيح لمنع التكرار واستقرار السيرفر
    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}"
    )

if __name__ == "__main__":
    main()
