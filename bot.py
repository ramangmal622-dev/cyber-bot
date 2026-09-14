import os
import sqlite3
import logging
import random
import re
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

# إعداد خادم ويب بسيط لمنصة Railway لكي تظل الحاوية مفتوحة ولا تتوقف
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Cyber-Ops Empire Bot v4.6 is active and running!")

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), SimpleHandler)
    server.serve_forever()

# بدء تشغيل السيرفر الوهمي في خلفية منفصلة
threading.Thread(target=run_web_server, daemon=True).start()

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

    if data == "student_lookup_prompt":
        admin_state[user_id] = {"action": "wait_student_query_id"}
        await query.message.reply_text("🔍 **الاستعلام الأكاديمي:**\nأرسل الآن **الآيدي الرقمي الخاص بك (المكون من 6 أرقام)**:")

    elif data == "student_update_request":
        admin_state[user_id] = {"action": "wait_student_update_info"}
        await query.message.reply_text("📋 **طلب مراجعة وتعديل المعلومات:**\nأرسل الآيدي الخاص بك مع التعديل المطلوب (الاسم الجديد):")

    elif data == "submit_task_prompt":
        admin_state[user_id] = {"action": "wait_student_task_submission"}
        await query.message.reply_text("📤 **رفع مهمة عملية:**\nأرسل الملف مع كتابة (آيدي الطالب + اسم المهمة) في خانة التعليق (Caption).\nمثال: `482910 تحليل الثغرة`")

    elif data == "vuln_report_prompt":
        admin_state[user_id] = {"action": "wait_vuln_report"}
        await query.message.reply_text("🛡️ **تقرير الثغرات الأمنية:**\nاكتب تفاصيل الثغرة المكتشفة أو ارفق الأدلة وسيقوم النظام بتوجيهها للإدارة فوراً:")

    elif data == "scan_links_prompt":
        admin_state[user_id] = {"action": "wait_link_scan"}
        await query.message.reply_text("🔍 **فحص الروابط والملفات:**\nأرسل الرابط أو النص المراد فحصه:")

    elif data == "support_chat_prompt":
        admin_state[user_id] = {"action": "wait_support_message"}
        await query.message.reply_text("📞 **غرفة الدعم والمشرفين:**\nاكتب رسالتك أو استفسارك وسيتم تحويله لفريق الإدارة والدعم الفني:")

    elif data == "start_quick_quiz":
        conn = sqlite3.connect("dark_cyber_academy.db")
        cursor = conn.cursor()
        cursor.execute("SELECT id, question, opt1, opt2, opt3 FROM quizzes ORDER BY RANDOM() LIMIT 1")
        q_row = cursor.fetchone()
        conn.close()
        
        if not q_row:
            await query.message.reply_text("⚠️ لم يتم إدراج اختبارات سيبرانية في بنك الأسئلة من قبل الإدارة بعد.")
            return
            
        q_id, q_text, o1, o2, o3 = q_row
        keyboard = [
            [InlineKeyboardButton(o1, callback_data=f"ans_{q_id}_1")],
            [InlineKeyboardButton(o2, callback_data=f"ans_{q_id}_2")],
            [InlineKeyboardButton(o3, callback_data=f"ans_{q_id}_3")],
            [InlineKeyboardButton("⬅️ رجوع", callback_data="back_home")]
        ]
        await query.edit_message_text(text=f"🧠 **اختبار التقييم السيبراني الفوري:**\n\n{q_text}", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("ans_"):
        parts = data.split("_")
        q_id, chosen_opt = int(parts[1]), int(parts[2])
        
        conn = sqlite3.connect("dark_cyber_academy.db")
        cursor = conn.cursor()
        cursor.execute("SELECT correct_opt, reward_points FROM quizzes WHERE id = ?", (q_id,))
        q_data = cursor.fetchone()
        
        if q_data:
            correct, points = q_data
            if chosen_opt == correct:
                cursor.execute("SELECT student_id, points FROM students WHERE user_id = ?", (user_id,))
                st_row = cursor.fetchone()
                if st_row:
                    st_id, current_pts = st_row
                    new_pts = current_pts + points
                    cursor.execute("UPDATE students SET points = ? WHERE student_id = ?", (new_pts, st_id))
                    conn.commit()
                    await query.edit_message_text(text=f"🔥 **إجابة عبقرية وصحيحة!**\nتمت إضافة +{points} نقطة لملفك السيبراني.")
                else:
                    await query.edit_message_text(text="✅ إجابة صحيحة، لكنك غير مسجل كطالب رسمي في النظام.")
            else:
                await query.edit_message_text(text="❌ **إجابة خاطئة!**\nعليك بمراجعة مكتبة الأبحاث وتطوير مهاراتك.")
        conn.close()

    elif data.startswith("main_"):
        main_type = data.replace("main_", "")
        sections_dict = get_all_sub_sections(main_type)
        m_sections = get_all_main_sections()
        
        conn = sqlite3.connect("dark_cyber_academy.db")
        cursor = conn.cursor()
        keyboard = []
        for sec_key, sec_name in sections_dict.items():
            cursor.execute("SELECT COUNT(*) FROM content WHERE main_type = ? AND sec_key = ?", (main_type, sec_key))
            count = cursor.fetchone()[0]
            keyboard.append([InlineKeyboardButton(f"{sec_name} ({count})", callback_data=f"view_{main_type}_{sec_key}")])
        conn.close()
        
        keyboard.append([InlineKeyboardButton("⬅️ رجوع للرئيسية", callback_data="back_home")])
        await query.edit_message_text(text=f"📂 {m_sections.get(main_type, 'القسم')}:\nاختر الفرع المستهدف:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("view_"):
        parts = data.split("_", 2)
        main_type, sec_key = parts[1], parts[2]
        
        conn = sqlite3.connect("dark_cyber_academy.db")
        cursor = conn.cursor()
        cursor.execute("SELECT id, item_name, points_cost FROM content WHERE main_type = ? AND sec_key = ?", (main_type, sec_key))
        items = cursor.fetchall()
        conn.close()
        
        keyboard = []
        if not items:
            keyboard.append([InlineKeyboardButton("⚠️ القطاع فارغ حالياً", callback_data="none")])
        else:
            for item in items:
                row_id, item_name, p_cost = item
                cost_label = f"🔓 [مجاني]" if p_cost == 0 else f"🔐 [🛒 {p_cost} نقطة]"
                keyboard.append([InlineKeyboardButton(f"{item_name} {cost_label}", callback_data=f"getfile_{row_id}")])
        
        keyboard.append([InlineKeyboardButton("⬅️ رجوع للأقسام", callback_data=f"main_{main_type}")])
        await query.edit_message_text(text="اختر العنصر لتحميله (الملفات المقفلة تتطلب رصيد نقاط):", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("getfile_"):
        file_row_id = data.replace("getfile_", "")
        
        conn = sqlite3.connect("dark_cyber_academy.db")
        cursor = conn.cursor()
        cursor.execute("SELECT file_id, file_type, item_name, points_cost FROM content WHERE id = ?", (file_row_id,))
        row = cursor.fetchone()
        
        if not row:
            conn.close()
            await query.message.reply_text("❌ لم يتم العثور على الملف في قاعدة البيانات.")
            return
            
        f_id, f_type, item_name, p_cost = row
        
        if p_cost > 0:
            cursor.execute("SELECT student_id, points FROM students WHERE user_id = ?", (user_id,))
            st_row = cursor.fetchone()
            if not st_row:
                conn.close()
                await query.answer("مرفوض! يجب أن تكون طالباً مسجلاً لتنزيل الملفات المقفلة.", show_alert=True)
                return
            
            st_id, current_pts = st_row
            if current_pts < p_cost:
                conn.close()
                await query.answer(f"❌ رصيدك الحالي ({current_pts} نقطة) لا يكفي لشراء هذا الملف! التكلفة المطلوبة: {p_cost} نقطة.", show_alert=True)
                return
            
            new_pts = current_pts - p_cost
            cursor.execute("UPDATE students SET points = ? WHERE student_id = ?", (new_pts, st_id))
            conn.commit()
            
        conn.close()
        
        cost_msg = f" (تم خصم {p_cost} نقطة بنجاح)" if p_cost > 0 else ""
        await query.message.reply_text(f"🔄 جاري سحب وإرسال الملف المطلوب ({item_name}){cost_msg}...")
        try:
            if f_type == "document":
                await context.bot.send_document(chat_id=query.message.chat_id, document=f_id)
            elif f_type == "photo":
                await context.bot.send_photo(chat_id=query.message.chat_id, photo=f_id)
            elif f_type == "video":
                await context.bot.send_video(chat_id=query.message.chat_id, video=f_id)
        except Exception as e:
            await query.message.reply_text(f"⚠️ تعذر إرسال الملف: {e}")

    elif data == "admin_main":
        if not role:
            await query.answer("مرفوض! هذه المنطقة خاصة بالسيد والمشرفين فقط.", show_alert=True)
            return
        keyboard = [
            [InlineKeyboardButton("➕ إضافة قسم أساسي جديد", callback_data="admin_add_main_section")],
            [InlineKeyboardButton("✏️ تعديل وإعادة تسمية الأقسام الرئيسية", callback_data="admin_rename_main_section")],
            [InlineKeyboardButton("➕ إضافة فرع/قسم جديد داخل الأقسام", callback_data="admin_add_sub_section")],
            [InlineKeyboardButton("✏️ تعديل وإعادة تسمية الأقسام والفروع", callback_data="admin_rename_sub_section")],
            [InlineKeyboardButton("📢 البث الإذاعي الشامل لجميع الرعية", callback_data="admin_broadcast_prompt")],
            [InlineKeyboardButton("🧠 زرع تحدي واختبار سيبراني (Quiz)", callback_data="admin_add_quiz")],
            [InlineKeyboardButton("📤 رفع أداة أو ملف استخباراتي جديد", callback_data="upload_choose_main")],
            [InlineKeyboardButton("🗑️ حذف ملف أو عنصر من الأرشيف", callback_data="admin_delete_menu")],
            [InlineKeyboardButton("🎓 إدارة الطلاب والتقييمات والدرجات", callback_data="manage_students_scores")],
            [InlineKeyboardButton("📥 فحص ومراجعة الواجبات المقدمة", callback_data="review_submissions")],
            [InlineKeyboardButton("🛡️ مراجعة تقارير الثغرات الأمنية", callback_data="admin_review_vulns")],
            [InlineKeyboardButton("📞 متابعة تذاكر دعم ورسائل الرعية", callback_data="admin_review_support")],
            [InlineKeyboardButton("👥 لوحة التحكم بالمشرفين والصلاحيات", callback_data="manage_admins_panel")],
            [InlineKeyboardButton("📜 سجل تدقيق نشاطات المشرفين (Logs)", callback_data="admin_view_logs")],
            [InlineKeyboardButton("⬅️ رجوع للرئيسية", callback_data="back_home")]
        ]
        await query.edit_message_text(text=f"👑 **غرفة القيادة العليا (مستوى السيادة: {role}):**", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "manage_students_scores":
        if not role:
            await query.answer("مرفوض!", show_alert=True)
            return
        keyboard = [
            [InlineKeyboardButton("➕ إضافة نقاط للطالب", callback_data="admin_add_points_prompt")],
            [InlineKeyboardButton("➖ خصم نقاط من الطالب", callback_data="admin_sub_points_prompt")],
            [InlineKeyboardButton("⬅️ رجوع", callback_data="admin_main")]
        ]
        await query.edit_message_text(text="🎓 **إدارة الطلاب والدرجات والتقييمات:**", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "admin_add_points_prompt":
        if not role:
            await query.answer("مرفوض!", show_alert=True)
            return
        admin_state[user_id] = {"action": "wait_admin_add_points_id"}
        await query.message.reply_text("➕ **إضافة نقاط:**\nأرسل الآن **آيدي الطالب** المراد إضافة النقاط له:")

    elif data == "admin_view_logs":
        if role != "dark_lord":
            await query.answer("مرفوض! هذه الصلاحية للمالك حصرياً.", show_alert=True)
            return
        conn = sqlite3.connect("dark_cyber_academy.db")
        cursor = conn.cursor()
        cursor.execute("SELECT admin_id, action_desc, timestamp FROM audit_logs ORDER BY id DESC LIMIT 15")
        logs = cursor.fetchall()
        conn.close()
        
        text = "📜 **آخر سجلات نشاطات المشرفين:**\n\n"
        if not logs:
            text += "لا توجد سجلات مسجلة حتى الآن."
        else:
            for l in logs:
                text += f"👤 المشرف: `{l[0]}`\n⚡ الفعل: {l[1]}\n⏱️ الوقت: {l[2]}\n-------------------\n"
        await query.message.reply_text(text)

# معالج الرسائل النصية ومدخلات الإدارة والطلاب (هنا تم حل مشكلة الحفظ وعدم التوقف)
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    
    if is_student_banned(user_id):
        return

    if user_id not in admin_state:
        return

    state = admin_state[user_id]
    action = state.get("action")

    # 1. التسجيل الذاتي للطالب الجديد
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
                f"🆔 الآيدي الخاص بك: `{student_id}`\n"
                f"⭐ رصيدك الابتدائي: `0` نقطة\n\n"
                f"احتفظ بالآيدي الخاص بك جيداً، يمكنك الآن استخدام لوحة التحكم بالأسفل.",
                parse_mode="Markdown"
            )
            await start(update, context)
        except Exception as e:
            await update.message.reply_text(f"⚠️ حدث خطأ أثناء التسجيل: {e}")
        finally:
            conn.close()

    # 2. إضافة نقاط للطالب من قبل المشرف (الخطوة الأولى: استقبال الآيدي)
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
        await update.message.reply_text(f"✅ تم العثور على الطالب: **{st[1]}** (الرصيد الحالي: {st[2]})\n\nأرسل الآن **عدد النقاط** المراد إضافتها (رقم صحيح):")

    # 3. إضافة نقاط للطالب من قبل المشرف (الخطوة الثانية: استقبال القيمة وحفظها بقاعدة البيانات)
    elif action == "wait_admin_add_points_value":
        target_sid = state.get("target_student_id")
        try:
            points_to_add = int(text.strip())
        except ValueError:
            await update.message.reply_text("❌ يرجى إرسال رقم صحيح فقط لعدد النقاط:")
            return
            
        conn = sqlite3.connect("dark_cyber_academy.db")
        cursor = conn.cursor()
        cursor.execute("SELECT points, name FROM students WHERE student_id = ?", (target_sid,))
        st = cursor.fetchone()
        
        if st:
            current_pts, st_name = st
            new_pts = current_pts + points_to_add
            cursor.execute("UPDATE students SET points = ? WHERE student_id = ?", (new_pts, target_sid))
            conn.commit()  # <-- الحفظ الإجباري لضمان ثبات النقاط
            
            log_admin_action(user_id, f"إضافة {points_to_add} نقطة للطالب {st_name} ({target_sid})")
            del admin_state[user_id]
            
            await update.message.reply_text(
                f"✅ **تمت إضافة النقاط بنجاح وثزبت في النظام!**\n\n"
                f"👤 الطالب: {st_name}\n"
                f"➕ النقاط المضافة: +{points_to_add}\n"
                f"⭐ الرصيد الجديد: `{new_pts}` نقطة"
            )
        else:
            await update.message.reply_text("❌ حدث خطأ، لم يتم العثور على الطالب في قاعدة البيانات.")
            
        conn.close()
        await start(update, context)

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    
    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
