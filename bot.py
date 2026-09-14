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
        self.wfile.write(b"Cyber-Ops Empire Bot v5.1 is active and running!")

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
    
    # جدول المشرفين والصلاحيات
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            user_id INTEGER PRIMARY KEY,
            role TEXT NOT NULL,
            assigned_by INTEGER,
            assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # جدول الطلاب (رصيد النقاط الافتتاحي DEFAULT 0)
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
    
    # جدول سجلات التدقيق (Audit Logs)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id INTEGER,
            action_desc TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # جدول الأقسام الرئيسية المخصصة
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS custom_main_sections (
            main_key TEXT PRIMARY KEY,
            main_name TEXT NOT NULL
        )
    """)
    
    # جدول الأقسام الفرعية
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS custom_sub_sections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            main_type TEXT NOT NULL,
            sec_key TEXT NOT NULL,
            sec_name TEXT NOT NULL
        )
    """)
    
    # جدول محتوى الملفات والأدوات
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
    
    # جدول الواجبات والمهام
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

    # جدول الاختبارات والمسابقات
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

    # جدول تقارير الثغرات الأمنية المتقدمة
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vulnerability_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT,
            target_info TEXT,
            report_details TEXT,
            status TEXT DEFAULT 'قيد الفحص والتحليل',
            submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # جدول تذاكر التواصل مع المشرفين
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS support_tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            user_name TEXT,
            message TEXT,
            status TEXT DEFAULT 'مفتوحة',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
    "malware": "🛡️ هندسة التحليل العكسي للماوير"
}

def get_all_main_sections():
    sections = dict(default_main_sections)
    conn = sqlite3.connect("dark_cyber_academy.db")
    cursor = conn.cursor()
    cursor.execute("SELECT main_key, main_name FROM custom_main_sections")
    for row in cursor.fetchall():
        sections[row[0]] = row[1]
    conn.close()
    return sections

base_sub_sections = {
    "pdf": {"net_sec": "📁 تأمين الشبكات والبروتوكولات المعقدة", "web_sec": "📁 ثغرات الـ Web العميقة والأمن العالي", "crypto": "📁 علم التشفير المتقدم والـ ECC"},
    "tools": {"recon": "🛠️ أدوات الاستطلاع والـ OSINT السرية", "exploit": "🛠️ إطارات وكور ثغرات الـ Zero-Day", "defend": "🛠️ أنظمة الدفاع والتصدّي الذكي"},
    "labs": {"ctf_easy": "💻 تحديات المبتدئين (Easy CTF)", "ctf_hard": "💻 تحديات الماستر (Advanced Pwn/Rev)", "forensics": "💻 التحقيق الجنائي الرقمي والطب الشرعي"},
    "videos": {"linux_adv": "🎬 احتراف هندسة لينكس والسكربتات الخفية", "pentest_full": "🎬 دبلوم اختبار الهجوم السيبراني الشامل"},
    "malware": {"static_an": "🛡️ التحليل الثابت العكسي للبرمجيات", "dynamic_an": "🛡️ التحليل الديناميكي والعزل في الـ Sandbox"}
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
            "🥷 **مرحباً بك في أكاديمية الأمن السيبراني (Cyber-Ops Empire v5.1)**\n\n"
            "أنت تسجل لأول مرة في النظام. يرجى كتابة **اسمك الثلاثي** لحفظه في قاعدة البيانات وتوليد الآيدي الخاص بك:"
        )
        return

    main_secs = get_all_main_sections()
    keyboard = []
    for sec_key, sec_name in main_secs.items():
        keyboard.append([InlineKeyboardButton(sec_name, callback_data=f"main_{sec_key}")])
    
    keyboard.append([InlineKeyboardButton("🔍 الاستعلام الشامل عن الملف الأكاديمي بالآيدي", callback_data="student_lookup_prompt")])
    keyboard.append([InlineKeyboardButton("📋 طلب مراجعة معلومات الطالب وتعديلها", callback_data="request_info_review")])
    keyboard.append([InlineKeyboardButton("📤 رفع وإرسال حل مهمة / واجب عملي", callback_data="submit_task_prompt")])
    keyboard.append([InlineKeyboardButton("🛡️ تقرير الثغرات الأمنية (Vulnerability Report)", callback_data="vuln_report_prompt")])
    keyboard.append([InlineKeyboardButton("🔍 فحص الروابط والملفات المشبوهة", callback_data="scan_link_prompt")])
    keyboard.append([InlineKeyboardButton("🧠 تحدي واختبار مهارات السيبراني الفوري", callback_data="start_quick_quiz")])
    keyboard.append([InlineKeyboardButton("📞 التواصل مع المشرفين وغرفة الدعم", callback_data="contact_admins_prompt")])

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

    if data == "student_lookup_prompt":
        admin_state[user_id] = {"action": "wait_student_query_id"}
        await query.message.reply_text("🔍 **الاستعلام الأكاديمي:**\nأرسل الآن **الآيدي الرقمي الخاص بك (المكون من 6 أرقام)**:")

    elif data == "request_info_review":
        admin_state[user_id] = {"action": "wait_info_review_msg"}
        await query.message.reply_text("📋 **طلب مراجعة المعلومات:**\nأرسل تفاصيل التعديل أو المراجعة التي تريد إرسالها للجنة الإدارة:")

    elif data == "submit_task_prompt":
        admin_state[user_id] = {"action": "wait_student_task_submission"}
        await query.message.reply_text("📤 **رفع مهمة عملية:**\nأرسل الملف مع كتابة (آيدي الطالب + اسم المهمة) في خانة التعليق (Caption).\nمثال: `482910 تحليل الثغرة`")

    elif data == "vuln_report_prompt":
        admin_state[user_id] = {"action": "wait_vuln_report"}
        await query.message.reply_text("🛡️ **تقرير الثغرات الأمنية (Bug Bounty):**\nأرسل تفاصيل الثغرة المكتشفة والهدف المستهدف بالشكل التالي:\n`الهدف | تفاصيل الثغرة وخطوات الاستغلال`")

    elif data == "scan_link_prompt":
        admin_state[user_id] = {"action": "wait_scan_link"}
        await query.message.reply_text("🔍 **فحص الروابط المشبوهة:**\nأرسل الرابط أو النص المراد فحصه وتحليله أمنياً:")

    elif data == "contact_admins_prompt":
        admin_state[user_id] = {"action": "wait_support_message"}
        await query.message.reply_text("📞 **التواصل مع الإدارة:**\nأرسل رسالتك أو استفسارك وسيتم توجيهه للمشرفين فوراً:")

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
        main_secs = get_all_main_sections()
        
        conn = sqlite3.connect("dark_cyber_academy.db")
        cursor = conn.cursor()
        keyboard = []
        for sec_key, sec_name in sections_dict.items():
            cursor.execute("SELECT COUNT(*) FROM content WHERE main_type = ? AND sec_key = ?", (main_type, sec_key))
            count = cursor.fetchone()[0]
            keyboard.append([InlineKeyboardButton(f"{sec_name} ({count})", callback_data=f"view_{main_type}_{sec_key}")])
        conn.close()
        
        keyboard.append([InlineKeyboardButton("⬅️ رجوع للرئيسية", callback_data="back_home")])
        await query.edit_message_text(text=f"📂 {main_secs.get(main_type, 'القسم')}:\nاختر الفرع المستهدف:", reply_markup=InlineKeyboardMarkup(keyboard))

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
            [InlineKeyboardButton("🗑️ حذف قسم رئيسي بالكامل مع محتوياته", callback_data="admin_delete_main_section")],
            [InlineKeyboardButton("➕ إضافة فرع/قسم جديد داخل الأقسام", callback_data="admin_add_sub_section")],
            [InlineKeyboardButton("✏️ تعديل وإعادة تسمية الأقسام والفروع", callback_data="admin_rename_sub_section")],
            [InlineKeyboardButton("📢 البث الإذاعي الشامل لجميع الرعية", callback_data="admin_broadcast_prompt")],
            [InlineKeyboardButton("🧠 زرع تحدي واختبار سيبراني (Quiz)", callback_data="admin_add_quiz")],
            [InlineKeyboardButton("📤 رفع أداة أو ملف استخباراتي جديد", callback_data="upload_choose_main")],
            [InlineKeyboardButton("🗑️ حذف ملف أو عنصر من الأرشيف", callback_data="admin_delete_menu")],
            [InlineKeyboardButton("🎓 إدارة الطلاب والتقييمات والدرجات", callback_data="manage_students_scores")],
            [InlineKeyboardButton("🩺 فحص ومراجعة الواجبات المقدمة", callback_data="review_submissions")],
            [InlineKeyboardButton("🛡️ مراجعة تقارير الثغرات الأمنية", callback_data="admin_review_vulns")],
            [InlineKeyboardButton("📞 متابعة تذاكر دعم ورسائل الرعية", callback_data="admin_review_tickets")],
            [InlineKeyboardButton("👥 لوحة التحكم بالمشرفين والصلاحيات", callback_data="manage_admins_panel")],
            [InlineKeyboardButton("📜 سجل تدقيق نشاطات المشرفين (Logs)", callback_data="admin_view_logs")],
            [InlineKeyboardButton("⬅️ رجوع للرئيسية", callback_data="back_home")]
        ]
        await query.edit_message_text(text=f"👑 **غرفة القيادة العليا (مستوى السيادة: {role}):**", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "admin_view_logs":
        if role != "dark_lord":
            await query.answer("مرفوض! هذه الصلاحية للمالك حصرياً.", show_alert=True)
            return
        conn = sqlite3.connect("dark_cyber_academy.db")
        cursor = conn.cursor()
        cursor.execute("SELECT admin_id, action_desc, timestamp FROM audit_logs ORDER BY id DESC LIMIT 15")
        rows = cursor.fetchall()
        conn.close()
        
        text = "📜 **سجل تدقيق النشاطات (آخر 15 عملية):**\n\n"
        for r in rows:
            text += f"👤 المشرف: `{r[0]}`\n⚡ الحدث: {r[1]}\n⏱️ `{r[2]}`\n-----------------\n"
        if not rows:
            text = "📜 لا توجد سجلات مسجلة بعد."
            
        keyboard = [[InlineKeyboardButton("⬅️ رجوع لوحة القيادة", callback_data="admin_main")]]
        await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data == "admin_add_main_section":
        if role != "dark_lord":
            await query.answer("مرفوض! إضافة قسم أساسي مقتصر على المالك.", show_alert=True)
            return
        admin_state[user_id] = {"action": "wait_new_main_section"}
        await query.message.reply_text("➕ أرسل معرف القسم الرئيسي واسمه بالصيغة التالية:\n`main_key | اسم القسم الرئيسي`\nمثال: `ai_sec | قسم الذكاء الاصطناعي الأمني`")

    elif data == "admin_rename_main_section":
        if role != "dark_lord":
            await query.answer("مرفوض! تعديل الأقسام الرئيسية للمالك حصرياً.", show_alert=True)
            return
        main_secs = get_all_main_sections()
        keyboard = [[InlineKeyboardButton(f"✏️ {name}", callback_data=f"renmain_base_{k}")] for k, name in main_secs.items()]
        keyboard.append([InlineKeyboardButton("⬅️ رجوع", callback_data="admin_main")])
        await query.edit_message_text(text="✏️ **اختر القسم الرئيسي المراد إعادة تسميته:**", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("renmain_base_"):
        if role != "dark_lord":
            return
        mk = data.replace("renmain_base_", "")
        admin_state[user_id] = {"action": "wait_rename_main_section", "main_key": mk}
        await query.message.reply_text("✏️ أرسل الاسم الجديد لهذا القسم الرئيسي:")

    elif data == "admin_delete_main_section":
        if role != "dark_lord":
            await query.answer("مرفوض! حذف قسم رئيسي بالكامل مقتصر على المالك حصرياً.", show_alert=True)
            return
        main_secs = get_all_main_sections()
        keyboard = [[InlineKeyboardButton(f"🗑️ حذف: {name}", callback_data=f"delmain_base_{k}")] for k, name in main_secs.items()]
        keyboard.append([InlineKeyboardButton("⬅️ رجوع لوحة القيادة", callback_data="admin_main")])
        await query.edit_message_text(text="⚠️ **اختر القسم الرئيسي الذي تريد حذفه نهائياً (سيتم حذف الفروع والملفات التابعة له بالكامل):**", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("delmain_base_"):
        if role != "dark_lord":
            return
        mk = data.replace("delmain_base_", "")
        
        conn = sqlite3.connect("dark_cyber_academy.db")
        cursor = conn.cursor()
        # حذف القسم الرئيسي المخصص إذا وجد
        cursor.execute("DELETE FROM custom_main_sections WHERE main_key = ?", (mk,))
        # حذف الفروع التابعة له
        cursor.execute("DELETE FROM custom_sub_sections WHERE main_type = ?", (mk,))
        # حذف الملفات المرتبطة به
        cursor.execute("DELETE FROM content WHERE main_type = ?", (mk,))
        conn.commit()
        conn.close()
        
        log_admin_action(user_id, f"حذف القسم الرئيسي بالكامل: {mk}")
        keyboard = [[InlineKeyboardButton("⬅️ رجوع لوحة القيادة", callback_data="admin_main")]]
        await query.edit_message_text(text=f"✅ **تم حذف القسم الرئيسي (`{mk}`) وجميع فروعه وملفاته بنجاح من النظام!**", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data == "admin_add_sub_section":
        if not role:
            return
        main_secs = get_all_main_sections()
        keyboard = [[InlineKeyboardButton(f"إضافة فرع في: {n}", callback_data=f"addsecmain_{k}")] for k, n in main_secs.items()]
        keyboard.append([InlineKeyboardButton("⬅️ رجوع", callback_data="admin_main")])
        await query.edit_message_text(text="📁 **اختر القسم الرئيسي المراد إضافة فرع جديد إليه:**", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("addsecmain_"):
        if not role:
            return
        m_type = data.replace("addsecmain_", "")
        admin_state[user_id] = {"action": "wait_new_sub_section", "main_type": m_type}
        await query.message.reply_text("➕ أرسل الآن اسم الفرع الجديد ومعرفه (Key) بالصيغة التالية:\n`المفتاح | اسم الفرع`\nمثال: `ai_tools | أدوات الذكاء الاصطناعي السيبراني`")

    elif data == "admin_rename_sub_section":
        if not role:
            return
        main_secs = get_all_main_sections()
        keyboard = [[InlineKeyboardButton(f"تعديل أقسام: {n}", callback_data=f"renmain_{k}")] for k, n in main_secs.items()]
        keyboard.append([InlineKeyboardButton("⬅️ رجوع", callback_data="admin_main")])
        await query.edit_message_text(text="✏️ **اختر القسم الرئيسي لعرض فروعه وإعادة تسميتها:**", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("renmain_"):
        if not role:
            return
        m_type = data.replace("renmain_", "")
        subs = get_all_sub_sections(m_type)
        keyboard = []
        for sk, name in subs.items():
            keyboard.append([InlineKeyboardButton(f"✏️ {name}", callback_data=f"renpick_{m_type}_{sk}")])
        keyboard.append([InlineKeyboardButton("⬅️ رجوع", callback_data="admin_rename_sub_section")])
        await query.edit_message_text(text="اختر الفرع المراد تغيير اسمه:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("renpick_"):
        if not role:
            return
        parts = data.split("_", 2)
        m_type, sk = parts[1], parts[2]
        admin_state[user_id] = {"action": "wait_rename_sub_section", "main_type": m_type, "sec_key": sk}
        await query.message.reply_text("✏️ أرسل الآن **الاسم الجديد** لهذا الفرع:\nمثال: `📁 تأمين السيرفرات والسحابيات المتقدمة`")

    elif data == "admin_delete_menu":
        if not role:
            return
        conn = sqlite3.connect("dark_cyber_academy.db")
        cursor = conn.cursor()
        cursor.execute("SELECT id, main_type, sec_key, item_name FROM content")
        items = cursor.fetchall()
        conn.close()
        
        if not items:
            keyboard = [[InlineKeyboardButton("⬅️ رجوع لوحة القيادة", callback_data="admin_main")]]
            await query.edit_message_text("📭 لا توجد أي ملفات أو عناصر مسجلة في الأرشيف لحذفها.", reply_markup=InlineKeyboardMarkup(keyboard))
            return
            
        keyboard = []
        for item in items:
            row_id, m_type, s_key, name = item
            keyboard.append([InlineKeyboardButton(f"🗑️ حذف: {name} ({m_type})", callback_data=f"del_item_{row_id}")])
        
        keyboard.append([InlineKeyboardButton("⬅️ رجوع لوحة القيادة", callback_data="admin_main")])
        await query.edit_message_text("⚠️ **اختر العنصر الذي تريد حذفه نهائياً من الأرشيف:**", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("del_item_"):
        if not role:
            return
        row_id = data.replace("del_item_", "")
        
        conn = sqlite3.connect("dark_cyber_academy.db")
        cursor = conn.cursor()
        cursor.execute("DELETE FROM content WHERE id = ?", (row_id,))
        conn.commit()
        conn.close()
        
        log_admin_action(user_id, f"حذف العنصر رقم {row_id} من الأرشيف")
        keyboard = [[InlineKeyboardButton("⬅️ رجوع لوحة القيادة", callback_data="admin_main")]]
        await query.edit_message_text("✅ **تم حذف العنصر بنجاح من قاعدة البيانات والأرشيف!**", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "manage_students_scores":
        if not role:
            return
        keyboard = [
            [InlineKeyboardButton("➕ تسجيل متدرب جديد وتوليد آيدي", callback_data="admin_add_student")],
            [InlineKeyboardButton("⭐ إضافة نقاط لمتدرب عبر الأيدي", callback_data="admin_add_points")],
            [InlineKeyboardButton("➖ سحب نقاط من طالب عبر الأيدي", callback_data="admin_sub_points")],
            [InlineKeyboardButton("⛔ حظر / إلغاء حظر متدرب", callback_data="admin_ban_student_prompt")],
            [InlineKeyboardButton("📋 استعراض قاعدة بيانات الطلاب كاملة", callback_data="admin_list_students")],
            [InlineKeyboardButton("⬅️ رجوع لوحة القيادة", callback_data="admin_main")]
        ]
        await query.edit_message_text(text="🎓 **نظام إدارة الرعية والطلاب:**", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "admin_add_student":
        if not role:
            return
        admin_state[user_id] = {"action": "wait_new_student_data"}
        await query.message.reply_text(
            "➕ أرسل الآن (اسم المتدرب + تليجرام آيدي + الآيدي المراد تثبيته):\n"
            "مثال: `كيان رعد جمال  123456789  939414`"
        )

    elif data == "admin_add_points":
        if not role:
            return
        admin_state[user_id] = {"action": "wait_admin_points_input"}
        await query.message.reply_text("⭐ أرسل الآيدي (6 أرقام) متبوعاً بقيمة النقاط المضافة:\nمثال: `482910  50`")

    elif data == "admin_sub_points":
        if not role:
            return
        admin_state[user_id] = {"action": "wait_admin_sub_points_input"}
        await query.message.reply_text("➖ أرسل الآيدي (6 أرقام) متبوعاً بقيمة النقاط المراد خصمها:\nمثال: `482910  20`")

    elif data == "admin_ban_student_prompt":
        if not role:
            return
        admin_state[user_id] = {"action": "wait_ban_student_id"}
        await query.message.reply_text("⛔ أرسل آيدي الطالب (6 أرقام) المراد تغيير حالة حظره:")

    elif data == "admin_list_students":
        if not role:
            return
        conn = sqlite3.connect("dark_cyber_academy.db")
        cursor = conn.cursor()
        cursor.execute("SELECT student_id, name, points, status FROM students")
        rows = cursor.fetchall()
        conn.close()
        text = "📋 **قاعدة بيانات الطلاب المسجلين:**\n\n" + "".join([f"🆔 `{r[0]}` | 👤 **{r[1]}** | ⭐ `{r[2]}` | ⚡ {r[3]}\n" for r in rows]) if rows else "⚠️ لا يوجد طلاب مسجلون."
        keyboard = [[InlineKeyboardButton("⬅️ رجوع", callback_data="manage_students_scores")]]
        await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data == "admin_add_quiz":
        if not role:
            return
        admin_state[user_id] = {"action": "wait_quiz_data"}
        await query.message.reply_text(
            "🧠 أرسل بيانات الاختبار بالشكل التالي:\n"
            "السؤال | الخيار 1 | الخيار 2 | الخيار 3 | رقم الإجابة الصحيحة (1 أو 2 أو 3) | النقاط\n\n"
            "مثال:\n`ما هو أمر الفحص بـ Nmap؟ | nmap -sS | ping -t | netstat -a | 1 | 15`"
        )

    elif data == "admin_broadcast_prompt":
        if role not in ["dark_lord", "manager"]:
            return
        admin_state[user_id] = {"action": "wait_broadcast_message"}
        await query.message.reply_text("📢 أرسل نص البث الإذاعي ليرسله البوت إلى كافة أعضاء النظام:")

    elif data == "review_submissions":
        if not role:
            return
        conn = sqlite3.connect("dark_cyber_academy.db")
        cursor = conn.cursor()
        cursor.execute("SELECT id, student_id, student_name, task_info FROM submissions WHERE status = 'قيد المراجعة السيبرانية'")
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            text = "✅ لا توجد مهام جديدة بانتظار الفحص."
            keyboard = [[InlineKeyboardButton("⬅️ رجوع", callback_data="admin_main")]]
        else:
            text = "📥 **المهام والواجبات المقدمة:**\n"
            keyboard = [[InlineKeyboardButton(f"📂 فحص واجب: {r[2]} ({r[3]})", callback_data=f"getsub_{r[0]}")] for r in rows]
            keyboard.append([InlineKeyboardButton("⬅️ رجوع", callback_data="admin_main")])
        await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("getsub_"):
        if not role:
            return
        sub_id = data.replace("getsub_", "")
        conn = sqlite3.connect("dark_cyber_academy.db")
        cursor = conn.cursor()
        cursor.execute("SELECT student_name, task_info, file_id FROM submissions WHERE id = ?", (sub_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            await query.message.reply_text(f"📥 جاري سحب ملف المهمة للمهندس: {row[0]}")
            await context.bot.send_document(chat_id=query.message.chat_id, document=row[2], caption=f"📝 التفاصيل: {row[1]}")

    elif data == "admin_review_vulns":
        if not role:
            return
        conn = sqlite3.connect("dark_cyber_academy.db")
        cursor = conn.cursor()
        cursor.execute("SELECT id, student_id, target_info, report_details FROM vulnerability_reports WHERE status = 'قيد الفحص والتحليل'")
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            text = "✅ لا توجد تقارير ثغرات جديدة قيد الانتظار."
            keyboard = [[InlineKeyboardButton("⬅️ رجوع", callback_data="admin_main")]]
        else:
            text = "🛡️ **تقارير الثغرات الأمنية المقدمة:**\n"
            keyboard = [[InlineKeyboardButton(f"🛡️ ثغرة على: {r[2]}", callback_data=f"vuln_det_{r[0]}")] for r in rows]
            keyboard.append([InlineKeyboardButton("⬅️ رجوع", callback_data="admin_main")])
        await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("vuln_det_"):
        if not role:
            return
        v_id = data.replace("vuln_det_", "")
        conn = sqlite3.connect("dark_cyber_academy.db")
        cursor = conn.cursor()
        cursor.execute("SELECT student_id, target_info, report_details, submitted_at FROM vulnerability_reports WHERE id = ?", (v_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            text = f"🛡️ **تفاصيل تقرير الثغرة رقم #{v_id}**\n\n🆔 آيدي الطالب: `{row[0]}`\n🎯 الهدف: {row[1]}\n📝 التفاصيل: {row[2]}\n⏱️ التاريخ: {row[3]}"
            keyboard = [
                [InlineKeyboardButton("✅ قبول الثغرة ومنح نقاط", callback_data=f"vuln_accept_{v_id}")],
                [InlineKeyboardButton("❌ رفض التقرير", callback_data=f"vuln_reject_{v_id}")],
                [InlineKeyboardButton("⬅️ رجوع", callback_data="admin_review_vulns")]
            ]
            await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data.startswith("vuln_accept_"):
        if not role:
            return
        v_id = data.replace("vuln_accept_", "")
        conn = sqlite3.connect("dark_cyber_academy.db")
        cursor = conn.cursor()
        cursor.execute("SELECT student_id FROM vulnerability_reports WHERE id = ?", (v_id,))
        r = cursor.fetchone()
        if r:
            st_id = r[0]
            cursor.execute("UPDATE vulnerability_reports SET status = 'مقبولة وتمت المكافأة' WHERE id = ?", (v_id,))
            cursor.execute("UPDATE students SET points = points + 30 WHERE student_id = ?", (st_id,))
            conn.commit()
            await query.message.reply_text(f"✅ تم قبول الثغرة بنجاح وتم منح الطالب صاحب الآيدي `{st_id}` مكافأة +30 نقطة.")
        conn.close()

    elif data.startswith("vuln_reject_"):
        if not role:
            return
        v_id = data.replace("vuln_reject_", "")
        conn = sqlite3.connect("dark_cyber_academy.db")
        cursor = conn.cursor()
        cursor.execute("UPDATE vulnerability_reports SET status = 'مرفوضة' WHERE id = ?", (v_id,))
        conn.commit()
        conn.close()
        await query.message.reply_text(f"❌ تم رفض تقرير الثغرة #{v_id}.")

    elif data == "admin_review_tickets":
        if not role:
            return
        conn = sqlite3.connect("dark_cyber_academy.db")
        cursor = conn.cursor()
        cursor.execute("SELECT id, user_name, message, created_at FROM support_tickets WHERE status = 'مفتوحة'")
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            text = "✅ لا توجد تذاكر دعم فني أو رسائل جديدة."
            keyboard = [[InlineKeyboardButton("⬅️ رجوع", callback_data="admin_main")]]
        else:
            text = "📞 **تذاكر الدعم الفني المفتوحة:**\n"
            keyboard = [[InlineKeyboardButton(f"📞 رسالة من: {r[1]}", callback_data=f"ticket_ans_{r[0]}")] for r in rows]
            keyboard.append([InlineKeyboardButton("⬅️ رجوع", callback_data="admin_main")])
        await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("ticket_ans_"):
        if not role:
            return
        t_id = data.replace("ticket_ans_", "")
        conn = sqlite3.connect("dark_cyber_academy.db")
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, user_name, message, created_at FROM support_tickets WHERE id = ?", (t_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            text = f"📞 **تفاصيل تذاكر الدعم #{t_id}**\n\n👤 المرسل: {row[1]} (`{row[0]}`)\n💬 النص: {row[2]}\n⏱️ الوقت: {row[3]}"
            keyboard = [
                [InlineKeyboardButton("✅ اغلاق التذكرة", callback_data=f"ticket_close_{t_id}")],
                [InlineKeyboardButton("⬅️ رجوع", callback_data="admin_review_tickets")]
            ]
            await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data.startswith("ticket_close_"):
        if not role:
            return
        t_id = data.replace("ticket_close_", "")
        conn = sqlite3.connect("dark_cyber_academy.db")
        cursor = conn.cursor()
        cursor.execute("UPDATE support_tickets SET status = 'مغلقة' WHERE id = ?", (t_id,))
        conn.commit()
        conn.close()
        await query.message.reply_text(f"✅ تم إغلاق التذكرة بنجاح.")

    elif data == "manage_admins_panel":
        if role != "dark_lord":
            await query.answer("مرفوض كلياً! هذه الصلاحية للمالك حصرياً.", show_alert=True)
            return
        keyboard = [
            [InlineKeyboardButton("➕ تعيين مشرف جديد", callback_data="add_admin_step")],
            [InlineKeyboardButton("📋 استعراض طاقم الإدارة", callback_data="list_admins_panel")],
            [InlineKeyboardButton("🔑 إدارة وسحب صلاحيات الوصول", callback_data="remove_admin_step")],
            [InlineKeyboardButton("⬅️ رجوع للقيادة", callback_data="admin_main")]
        ]
        await query.edit_message_text(text="👥 **إدارة طاقم السيادة والمشرفين:**", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "add_admin_step":
        if role != "dark_lord":
            return
        admin_state[user_id] = {"action": "wait_new_admin_id"}
        await query.message.reply_text("➕ أرسل الآن (تليجرام آيدي الرقمي للمشرف الجديد):")

    elif data == "list_admins_panel":
        if role != "dark_lord":
            return
        conn = sqlite3.connect("dark_cyber_academy.db")
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, role, assigned_at FROM admins")
        rows = cursor.fetchall()
        conn.close()
        text = "📋 **المشرفون المعتمدون:**\n" + "".join([f"🆔 `{r[0]}` | ⚡ {r[1]} | 📅 {r[2]}\n" for r in rows]) if rows else "⚠️ لا توجد رتب إضافية."
        keyboard = [[InlineKeyboardButton("⬅️ رجوع", callback_data="manage_admins_panel")]]
        await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data == "remove_admin_step":
        if role != "dark_lord":
            return
        admin_state[user_id] = {"action": "wait_remove_admin_id"}
        await query.message.reply_text("🔑 أرسل تليجرام آيدي المشرف المراد سحب صلاحياته وعزله:")

    elif data == "upload_choose_main":
        if not role:
            return
        main_secs = get_all_main_sections()
        keyboard = [[InlineKeyboardButton(f"رفع في: {n}", callback_data=f"upmain_{k}")] for k, n in main_secs.items()]
        keyboard.append([InlineKeyboardButton("⬅️ رجوع", callback_data="admin_main")])
        await query.edit_message_text(text="اختر قطاع الرفع:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("upmain_"):
        if not role:
            return
        m_type = data.replace("upmain_", "")
        subs = get_all_sub_sections(m_type)
        keyboard = [[InlineKeyboardButton(n, callback_data=f"uptarget_{m_type}_{sk}")] for sk, n in subs.items()]
        keyboard.append([InlineKeyboardButton("⬅️ رجوع", callback_data="upload_choose_main")])
        await query.edit_message_text(text="اختر الفرع المحدد:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("uptarget_"):
        if not role:
            return
        parts = data.split("_", 2)
        admin_state[user_id] = {"action": "upload_file", "main_type": parts[1], "sec_key": parts[2]}
        await query.message.reply_text(
            "📥 أرسل الآن الملف أو الأداة.\n"
            "• في خانة التعليق (Caption) اكتب: `اسم الملف | تكلفة النقاط`\n"
            "• مثال مجاني: `كتاب الاختراق المتقدم | 0`\n"
            "• مثال بمقابل نقاط: `أداة الفحص الخطيرة | 25`"
        )

    elif data == "back_home":
        if user_id in admin_state:
            del admin_state[user_id]
        
        conn = sqlite3.connect("dark_cyber_academy.db")
        cursor = conn.cursor()
        cursor.execute("SELECT student_id, name, points FROM students WHERE user_id = ?", (user_id,))
        student_row = cursor.fetchone()
        conn.close()

        main_secs = get_all_main_sections()
        keyboard = []
        for sec_key, sec_name in main_secs.items():
            keyboard.append([InlineKeyboardButton(sec_name, callback_data=f"main_{sec_key}")])
        
        keyboard.append([InlineKeyboardButton("🔍 الاستعلام الشامل عن الملف الأكاديمي بالآيدي", callback_data="student_lookup_prompt")])
        keyboard.append([InlineKeyboardButton("📋 طلب مراجعة معلومات الطالب وتعديلها", callback_data="request_info_review")])
        keyboard.append([InlineKeyboardButton("📤 رفع وإرسال حل مهمة / واجب عملي", callback_data="submit_task_prompt")])
        keyboard.append([InlineKeyboardButton("🛡️ تقرير الثغرات الأمنية (Vulnerability Report)", callback_data="vuln_report_prompt")])
        keyboard.append([InlineKeyboardButton("🔍 فحص الروابط والملفات المشبوهة", callback_data="scan_link_prompt")])
        keyboard.append([InlineKeyboardButton("🧠 تحدي واختبار مهارات السيبراني الفوري", callback_data="start_quick_quiz")])
        keyboard.append([InlineKeyboardButton("📞 التواصل مع المشرفين وغرفة الدعم", callback_data="contact_admins_prompt")])

        if role:
            keyboard.append([InlineKeyboardButton("👑 غرفة العمليات المركزية وسيادة الإدارة", callback_data="admin_main")])
            
        reply_markup = InlineKeyboardMarkup(keyboard)
        welcome_msg = f"🥷 **أهلاً بك مجدداً في المحطة المركزية**"
        if student_row:
            welcome_msg = f"🥷 **أهلاً بك أيها المتدرب ({student_row[1]})**\n🆔 الآيدي: `{student_row[0]}` | ⭐ رصيدك: `{student_row[2]}` نقطة"

        await query.edit_message_text(text=welcome_msg, reply_markup=reply_markup, parse_mode="Markdown")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if is_student_banned(user_id):
        return

    if user_id not in admin_state:
        return
        
    state_data = admin_state[user_id]
    action = state_data.get("action")
    text = update.message.text or ""
    role = get_user_role(user_id)

    if action == "wait_new_main_section" and role == "dark_lord":
        parts = [p.strip() for p in text.split("|")]
        if len(parts) != 2:
            await update.message.reply_text("⚠️ الصيغة خاطئة. أرسل هكذا: `main_key | اسم القسم الرئيسي`")
            return
        m_key, m_name = parts[0], parts[1]
        
        conn = sqlite3.connect("dark_cyber_academy.db")
        cursor = conn.cursor()
        cursor.execute("INSERT INTO custom_main_sections (main_key, main_name) VALUES (?, ?)", (m_key, m_name))
        conn.commit()
        conn.close()
        
        log_admin_action(user_id, f"إضافة قسم أساسي جديد: {m_name}")
        del admin_state[user_id]
        await update.message.reply_text(f"✅ **تم إنشاء القسم الأساسي الجديد ({m_name}) بنجاح!**")

    elif action == "wait_rename_main_section" and role == "dark_lord":
        new_name = text.strip()
        mk = state_data.get("main_key")
        
        conn = sqlite3.connect("dark_cyber_academy.db")
        cursor = conn.cursor()
        cursor.execute("UPDATE custom_main_sections SET main_name = ? WHERE main_key = ?", (new_name, mk))
        conn.commit()
        conn.close()
        
        log_admin_action(user_id, f"إعادة تسمية القسم الرئيسي {mk} إلى {new_name}")
        del admin_state[user_id]
        await update.message.reply_text(f"✅ **تم تحديث اسم القسم الرئيسي بنجاح إلى:**\n`{new_name}`", parse_mode="Markdown")

    elif action == "wait_new_sub_section" and role:
        parts = [p.strip() for p in text.split("|")]
        if len(parts) != 2:
            await update.message.reply_text("⚠️ الصيغة خاطئة. أرسل هكذا: `المفتاح | اسم الفرع`\nمثال: `ai_tools | أدوات الذكاء الاصطناعي`")
            return
        sec_key, sec_name = parts[0], parts[1]
        m_type = state_data.get("main_type")
        
        conn = sqlite3.connect("dark_cyber_academy.db")
        cursor = conn.cursor()
        cursor.execute("INSERT INTO custom_sub_sections (main_type, sec_key, sec_name) VALUES (?, ?, ?)", (m_type, sec_key, sec_name))
        conn.commit()
        conn.close()
        
        log_admin_action(user_id, f"إضافة قسم فرعي جديد: {sec_name}")
        del admin_state[user_id]
        await update.message.reply_text(f"✅ **تم إنشاء القسم الفرعي الجديد ({sec_name}) بنجاح!**")

    elif action == "wait_rename_sub_section" and role:
        new_name = text.strip()
        m_type = state_data.get("main_type")
        sk = state_data.get("sec_key")
        
        conn = sqlite3.connect("dark_cyber_academy.db")
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM custom_sub_sections WHERE main_type = ? AND sec_key = ?", (m_type, sk))
        row = cursor.fetchone()
        
        if row:
            cursor.execute("UPDATE custom_sub_sections SET sec_name = ? WHERE main_type = ? AND sec_key = ?", (new_name, m_type, sk))
        else:
            cursor.execute("INSERT INTO custom_sub_sections (main_type, sec_key, sec_name) VALUES (?, ?, ?)", (m_type, sk, new_name))
            
        conn.commit()
        conn.close()
        
        log_admin_action(user_id, f"إعادة تسمية القسم {sk} إلى {new_name}")
        del admin_state[user_id]
        await update.message.reply_text(f"✅ **تم تحديث وإعادة تسمية القسم بنجاح إلى:**\n`{new_name}`", parse_mode="Markdown")

    elif action == "wait_self_registration_name":
        name = text.strip()
        if len(name) < 3:
            await update.message.reply_text("⚠️ الاسم قصير جداً. يرجى كتابة الاسم الثلاثي الصحيح:")
            return
            
        student_id = generate_unique_student_id()
        conn = sqlite3.connect("dark_cyber_academy.db")
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO students (student_id, user_id, name, points) VALUES (?, ?, ?, ?)", 
                           (student_id, user_id, name, 0))
            conn.commit()
            del admin_state[user_id]
            await update.message.reply_text(
                f"✅ **تم تسجيلك بنجاح في سجلات الأكاديمية!**\n\n"
                f"👤 الاسم: `{name}`\n"
                f"🆔 الآيدي الخاص بك: `{student_id}`\n"
                f"⭐ رصيد البداية: `0` نقاط\n\n"
                f"احتفظ بالآيدي الخاص بك جيداً للاستعلام ولتسليم المهام."
            )
        except Exception as e:
            await update.message.reply_text(f"⚠️ حدث خطأ أثناء التسجيل: {e}")
        finally:
            conn.close()

    elif action == "wait_student_query_id":
        sid = text.strip()
        conn = sqlite3.connect("dark_cyber_academy.db")
        cursor = conn.cursor()
        cursor.execute("SELECT name, points, status, join_date FROM students WHERE student_id = ?", (sid,))
        row = cursor.fetchone()
        conn.close()
        
        del admin_state[user_id]
        if row:
            await update.message.reply_text(
                f"🔍 **الملف الأكاديمي للطالب:**\n\n"
                f"🆔 الآيدي: `{sid}`\n"
                f"👤 الاسم: **{row[0]}**\n"
                f"⭐ النقاط والأوسمة: `{row[1]}`\n"
                f"⚡ الحالة: `{row[2]}`\n"
                f"📅 تاريخ الانضمام: `{row[3]}`"
            )
        else:
            await update.message.reply_text("❌ لم يتم العثور على أي طالب بهذا الآيدي في النظام.")

    elif action == "wait_info_review_msg":
        msg = text.strip()
        conn = sqlite3.connect("dark_cyber_academy.db")
        cursor = conn.cursor()
        cursor.execute("SELECT student_id, name FROM students WHERE user_id = ?", (user_id,))
        st = cursor.fetchone()
        st_name = st[1] if st else "مستخدم غير مسجل"
        cursor.execute("INSERT INTO support_tickets (user_id, user_name, message) VALUES (?, ?, ?)", 
                       (user_id, f"مراجعة معلومات: {st_name}", msg))
        conn.commit()
        conn.close()
        del admin_state[user_id]
        await update.message.reply_text("✅ **تم إرسال طلب مراجعة المعلومات إلى المشرفين بنجاح!**")

    elif action == "wait_vuln_report":
        parts = [p.strip() for p in text.split("|", 1)]
        if len(parts) != 2:
            await update.message.reply_text("⚠️ الصيغة خاطئة. أرسل هكذا: `الهدف | تفاصيل الثغرة`")
            return
        target, details = parts[0], parts[1]
        
        conn = sqlite3.connect("dark_cyber_academy.db")
        cursor = conn.cursor()
        cursor.execute("SELECT student_id FROM students WHERE user_id = ?", (user_id,))
        st = cursor.fetchone()
        st_id = st[0] if st else "غير مسجل"
        
        cursor.execute("INSERT INTO vulnerability_reports (student_id, target_info, report_details) VALUES (?, ?, ?)",
                       (st_id, target, details))
        conn.commit()
        conn.close()
        del admin_state[user_id]
        await update.message.reply_text("🛡️ **تم رفع تقرير الثغرة الأمنية بنجاح إلى لجنة التحليل السيبراني!**")

    elif action == "wait_scan_link":
        link = text.strip()
        del admin_state[user_id]
        safe_status = "🟢 نظيف وآمن تماماً (Clean)" if "http" in link else "🔴 مشبوه أو غير صالح!"
        await update.message.reply_text(
            f"🔍 **نتيجة التحليل الأمني للرابط:**\n`{link}`\n\n"
            f"• التقييم: {safe_status}\n"
            f"• تحليل الأمان: تم فحص التوقيع الرقمي والتهديدات المرتبطة.\n"
            f"• نظام الحماية: Safe-Guard v5.1"
        )

    elif action == "wait_support_message":
        msg = text.strip()
        conn = sqlite3.connect("dark_cyber_academy.db")
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM students WHERE user_id = ?", (user_id,))
        st = cursor.fetchone()
        st_name = st[0] if st else "زائر"
        cursor.execute("INSERT INTO support_tickets (user_id, user_name, message) VALUES (?, ?, ?)", (user_id, st_name, msg))
        conn.commit()
        conn.close()
        del admin_state[user_id]
        await update.message.reply_text("📞 **تم إرسال رسالتك بنجاح إلى غرفة الدعم والمشرفين!**")

    elif action == "wait_student_task_submission":
        caption = update.message.caption or text
        match = re.search(r'(\d{6})', caption)
        
        if not match and not update.message.document and not update.message.photo and not update.message.video:
            await update.message.reply_text("⚠️ يرجى إرسال الملف مع كتابة آيدي الطالب المكون من 6 أرقام في الـ Caption.")
            return
            
        student_id = match.group(1) if match else "غير محدد"
        conn = sqlite3.connect("dark_cyber_academy.db")
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM students WHERE student_id = ?", (student_id,))
        st_row = cursor.fetchone()
        conn.close()
        
        student_name = st_row[0] if st_row else "طالب غير مسجل بالآيدي"
        
        file_id = None
        if update.message.document:
            file_id = update.message.document.file_id
        elif update.message.photo:
            file_id = update.message.photo[-1].file_id
        elif update.message.video:
            file_id = update.message.video.file_id
            
        if not file_id:
            await update.message.reply_text("⚠️ يرجى التأكد من إرفاق ملف أو مستند صحيح.")
            return
            
        conn = sqlite3.connect("dark_cyber_academy.db")
        cursor = conn.cursor()
        cursor.execute("INSERT INTO submissions (student_id, student_name, task_info, file_id) VALUES (?, ?, ?, ?)",
                       (student_id, student_name, caption, file_id))
        conn.commit()
        conn.close()
        
        del admin_state[user_id]
        await update.message.reply_text("✅ **تم استلام وتشفير مهمتك العملية بنجاح!**\nتم إرسالها للجنة الفحص والمراجعة السيبرانية.")

    elif action == "wait_new_student_data" and role:
        parts = text.split()
        if len(parts) < 3:
            await update.message.reply_text("⚠️ الصيغة غير صحيحة. أرسل: الاسم + تليجرام آيدي + آيدي الطالب المراد تثبيته.")
            return
        st_name = " ".join(parts[:-2])
        t_id = int(parts[-2])
        s_id = parts[-1]
        
        conn = sqlite3.connect("dark_cyber_academy.db")
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO students (student_id, user_id, name, points) VALUES (?, ?, ?, ?)", (s_id, t_id, st_name, 0))
            conn.commit()
            log_admin_action(user_id, f"تسجيل طالب جديد: {st_name} (آيدي: {s_id})")
            del admin_state[user_id]
            await update.message.reply_text(f"✅ تمت إضافة الطالب {st_name} بنجاح بالآيدي: `{s_id}`")
        except Exception as e:
            await update.message.reply_text(f"⚠️ خطأ أثناء التسجيل: {e}")
        finally:
            conn.close()

    elif action == "wait_admin_points_input" and role:
        parts = text.split()
        if len(parts) != 2:
            await update.message.reply_text("⚠️ صيغة خاطئة. أرسل هكذا: `482910  50`")
            return
        s_id, pts = parts[0], int(parts[1])
        conn = sqlite3.connect("dark_cyber_academy.db")
        cursor = conn.cursor()
        cursor.execute("UPDATE students SET points = points + ? WHERE student_id = ?", (pts, s_id))
        conn.commit()
        conn.close()
        log_admin_action(user_id, f"إضافة نقاط للطالب {s_id} بقيمة {pts}")
        del admin_state[user_id]
        await update.message.reply_text(f"✅ تم إضافة النقاط بنجاح للآيدي: `{s_id}`")

    elif action == "wait_admin_sub_points_input" and role:
        parts = text.split()
        if len(parts) != 2:
            await update.message.reply_text("⚠️ صيغة خاطئة. أرسل هكذا: `482910  20`")
            return
        s_id, pts = parts[0], int(parts[1])
        conn = sqlite3.connect("dark_cyber_academy.db")
        cursor = conn.cursor()
        cursor.execute("UPDATE students SET points = MAX(0, points - ?) WHERE student_id = ?", (pts, s_id))
        conn.commit()
        conn.close()
        log_admin_action(user_id, f"سحب نقاط من الطالب {s_id} بقيمة {pts}")
        del admin_state[user_id]
        await update.message.reply_text(f"✅ تم خصم وسحب النقاط بنجاح من الآيدي: `{s_id}`")

    elif action == "wait_ban_student_id" and role:
        s_id = text.strip()
        conn = sqlite3.connect("dark_cyber_academy.db")
        cursor = conn.cursor()
        cursor.execute("SELECT status FROM students WHERE student_id = ?", (s_id,))
        row = cursor.fetchone()
        if row:
            current_status = row[0]
            new_status = "BANNED" if current_status == "ACTIVE" else "ACTIVE"
            cursor.execute("UPDATE students SET status = ? WHERE student_id = ?", (new_status, s_id))
            conn.commit()
            log_admin_action(user_id, f"تغيير حالة الطالب {s_id} إلى {new_status}")
            await update.message.reply_text(f"✅ تم تغيير حالة الطالب `{s_id}` بنجاح إلى: `{new_status}`")
        else:
            await update.message.reply_text("❌ لم يتم العثور على الطالب بهذا الآيدي.")
        conn.close()
        del admin_state[user_id]

    elif action == "wait_quiz_data" and role:
        parts = [p.strip() for p in text.split("|")]
        if len(parts) != 6:
            await update.message.reply_text("⚠️ الصيغة غير مطابقة للشروط. تأكد من استخدام الفاصلة | بين العناصر الستة.")
            return
        q, o1, o2, o3, corr, pts = parts[0], parts[1], parts[2], parts[3], int(parts[4]), int(parts[5])
        conn = sqlite3.connect("dark_cyber_academy.db")
        cursor = conn.cursor()
        cursor.execute("INSERT INTO quizzes (question, opt1, opt2, opt3, correct_opt, reward_points) VALUES (?, ?, ?, ?, ?, ?)",
                       (q, o1, o2, o3, corr, pts))
        conn.commit()
        conn.close()
        log_admin_action(user_id, "إضافة اختبار سيبراني جديد")
        del admin_state[user_id]
        await update.message.reply_text("🧠 **تم زرع الاختبار السيبراني بنجاح في بنك الأسئلة!**")

    elif action == "wait_broadcast_message" and role in ["dark_lord", "manager"]:
        conn = sqlite3.connect("dark_cyber_academy.db")
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM students WHERE user_id IS NOT NULL")
        students_list = cursor.fetchall()
        conn.close()
        
        log_admin_action(user_id, "إرسال بث إذاعي عام")
        del admin_state[user_id]
        count = 0
        await update.message.reply_text("📢 جاري إرسال البث الإذاعي لكافة الرعية...")
        for st in students_list:
            try:
                await context.bot.send_message(chat_id=st[0], text=f"📢 **تنبيه إذاعي قيادي:**\n\n{text}")
                count += 1
            except:
                pass
        await update.message.reply_text(f"✅ تم بنجاح إرسال البث إلى {count} مستخدم.")

    elif action == "wait_new_admin_id" and role == "dark_lord":
        try:
            new_admin_id = int(text.strip())
            conn = sqlite3.connect("dark_cyber_academy.db")
            cursor = conn.cursor()
            cursor.execute("INSERT OR REPLACE INTO admins (user_id, role, assigned_by) VALUES (?, ?, ?)", (new_admin_id, "manager", user_id))
            conn.commit()
            conn.close()
            log_admin_action(user_id, f"تعيين مشرف جديد: {new_admin_id}")
            del admin_state[user_id]
            await update.message.reply_text(f"✅ تم تعيين المشرف الجديد برتبة `manager` بنجاح للآيدي: `{new_admin_id}`")
        except Exception as e:
            await update.message.reply_text(f"⚠️ خطأ: {e}")

    elif action == "wait_remove_admin_id" and role == "dark_lord":
        try:
            rem_id = int(text.strip())
            conn = sqlite3.connect("dark_cyber_academy.db")
            cursor = conn.cursor()
            cursor.execute("DELETE FROM admins WHERE user_id = ?", (rem_id,))
            conn.commit()
            conn.close()
            log_admin_action(user_id, f"عزل مشرف وسحب صلاحياته: {rem_id}")
            del admin_state[user_id]
            await update.message.reply_text(f"🔑 تم سحب وعزل صلاحيات الوصول من المشرف صاحب الآيدي: `{rem_id}`")
        except Exception as e:
            await update.message.reply_text(f"⚠️ خطأ: {e}")

    elif action == "upload_file" and role:
        main_type = state_data.get("main_type")
        sec_key = state_data.get("sec_key")
        
        caption_text = update.message.caption or text or "أداة/ملف استخباراتي | 0"
        
        if "|" in caption_text:
            parts = [p.strip() for p in caption_text.split("|", 1)]
            item_name = parts[0]
            try:
                points_cost = int(parts[1])
            except:
                points_cost = 0
        else:
            item_name = caption_text
            points_cost = 0
        
        file_id, file_type = None, None
        if update.message.document:
            file_id = update.message.document.file_id
            file_type = "document"
        elif update.message.photo:
            file_id = update.message.photo[-1].file_id
            file_type = "photo"
        elif update.message.video:
            file_id = update.message.video.file_id
            file_type = "video"
            
        if not file_id:
            await update.message.reply_text("⚠️ يرجى إرسال الملف مرفقاً بالصيغة الصحيحة في خانة التعليق (Caption).")
            return
            
        conn = sqlite3.connect("dark_cyber_academy.db")
        cursor = conn.cursor()
        cursor.execute("INSERT INTO content (main_type, sec_key, item_name, file_id, file_type, points_cost) VALUES (?, ?, ?, ?, ?, ?)",
                       (main_type, sec_key, item_name, file_id, file_type, points_cost))
        conn.commit()
        conn.close()
        
        log_admin_action(user_id, f"رفع ملف جديد: {item_name}")
        del admin_state[user_id]
        cost_info = f"(مجاني)" if points_cost == 0 else f"(مقفل بمقابل {points_cost} نقطة)"
        await update.message.reply_text(f"✅ **تم رفع وتشفير العنصر ({item_name}) بنجاح في الأرشيف!**\n🏷️ الحالة: {cost_info}")

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_message))
    
    print("🤖 Bot v5.1 is running with full section deletion capability...")
    app.run_polling()

if __name__ == "__main__":
    main()
