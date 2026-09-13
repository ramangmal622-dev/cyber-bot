import os
import sqlite3
import logging
import random
import re  # تم إضافة مكتبة التعبيرات المنتظمة لاستخراج الآيدي
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)

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
        CREATE TABLE IF NOT EXISTS content (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            main_type TEXT NOT NULL,
            sec_key TEXT NOT NULL,
            item_name TEXT NOT NULL,
            file_id TEXT NOT NULL,
            file_type TEXT NOT NULL,
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

def get_user_role(user_id):
    if user_id == OWNER_ID:
        return "dark_lord"
    conn = sqlite3.connect("dark_cyber_academy.db")
    cursor = conn.cursor()
    cursor.execute("SELECT role FROM admins WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None

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

main_sections = {
    "pdf": "📄 مكتبة أبحاث وكتب السيبراني المتقدمة",
    "tools": "🛠️ ترسانة أدوات وسكربتات الاختراق",
    "labs": "💻 مختبرات وتحديات CTF السيبرانية",
    "videos": "🎬 كورسات مرئية ودورات النخبة",
    "malware": "🛡️ هندسة التحليل العكسي للماوير"
}

sub_sections = {
    "pdf": {"net_sec": "📁 تأمين الشبكات والبروتوكولات المعقدة", "web_sec": "📁 ثغرات الـ Web العميقة والأمن العالي", "crypto": "📁 علم التشفير المتقدم والـ ECC"},
    "tools": {"recon": "🛠️ أدوات الاستطلاع والـ OSINT السرية", "exploit": "🛠️ إطارات وكور ثغرات الـ Zero-Day", "defend": "🛠️ أنظمة الدفاع والتصدّي الذكي"},
    "labs": {"ctf_easy": "💻 تحديات المبتدئين (Easy CTF)", "ctf_hard": "💻 تحديات الماستر (Advanced Pwn/Rev)", "forensics": "💻 التحقيق الجنائي الرقمي والطب الشرعي"},
    "videos": {"linux_adv": "🎬 احتراف هندسة لينكس والسكربتات الخفية", "pentest_full": "🎬 دبلوم اختبار الهجوم السيبراني الشامل"},
    "malware": {"static_an": "🛡️ التحليل الثابت العكسي للبرمجيات", "dynamic_an": "🛡️ التحليل الديناميكي والعزل في الـ Sandbox"}
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in admin_state:
        del admin_state[user_id]
        
    role = get_user_role(user_id)
    
    conn = sqlite3.connect("dark_cyber_academy.db")
    cursor = conn.cursor()
    cursor.execute("SELECT student_id, name FROM students WHERE user_id = ?", (user_id,))
    student_row = cursor.fetchone()
    conn.close()

    if not student_row and not role:
        admin_state[user_id] = {"action": "wait_self_registration_name"}
        await update.message.reply_text(
            "🥷 **مرحباً بك في أكاديمية الأمن السيبراني (Cyber-Ops Empire v4.3)**\n\n"
            "أنت تسجل لأول مرة في النظام. يرجى كتابة **اسمك الثلاثي** لحفظه في قاعدة البيانات وتوليد الآيدي الخاص بك:"
        )
        return

    keyboard = []
    for sec_key, sec_name in main_sections.items():
        keyboard.append([InlineKeyboardButton(sec_name, callback_data=f"main_{sec_key}")])
    
    keyboard.append([InlineKeyboardButton("🔍 الاستعلام الشامل عن الملف الأكاديمي بالآيدي", callback_data="student_lookup_prompt")])
    keyboard.append([InlineKeyboardButton("📤 رفع وإرسال حل مهمة / واجب عملي", callback_data="submit_task_prompt")])
    keyboard.append([InlineKeyboardButton("🧠 تحدي واختبار مهارات السيبراني الفوري", callback_data="start_quick_quiz")])

    if role:
        keyboard.append([InlineKeyboardButton("👑 غرفة العمليات المركزية وسيادة الإدارة", callback_data="admin_main")])
        
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_msg = f"🥷 **أهلاً بك مجدداً في المحطة المركزية**"
    if student_row:
        welcome_msg = f"🥷 **أهلاً بك أيها المتدرب ({student_row[1]})**\n🆔 الآيدي الخاص بك: `{student_row[0]}`"

    await update.message.reply_text(welcome_msg, reply_markup=reply_markup, parse_mode="Markdown")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data
    role = get_user_role(user_id)

    if data == "student_lookup_prompt":
        admin_state[user_id] = {"action": "wait_student_query_id"}
        await query.message.reply_text("🔍 **الاستعلام الأكاديمي:**\nأرسل الآن **الآيدي الرقمي الخاص بك (المكون من 6 أرقام)**:")

    elif data == "submit_task_prompt":
        admin_state[user_id] = {"action": "wait_student_task_submission"}
        await query.message.reply_text("📤 **رفع مهمة عملية:**\nأرسل الملف مع كتابة (آيدي الطالب + اسم المهمة) في خانة التعليق (Caption).\nمثال: `482910 تحليل الثغرة`")

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
        sections_dict = sub_sections.get(main_type, {})
        
        conn = sqlite3.connect("dark_cyber_academy.db")
        cursor = conn.cursor()
        keyboard = []
        for sec_key, sec_name in sections_dict.items():
            cursor.execute("SELECT COUNT(*) FROM content WHERE main_type = ? AND sec_key = ?", (main_type, sec_key))
            count = cursor.fetchone()[0]
            keyboard.append([InlineKeyboardButton(f"{sec_name} ({count})", callback_data=f"view_{main_type}_{sec_key}")])
        conn.close()
        
        keyboard.append([InlineKeyboardButton("⬅️ رجوع للرئيسية", callback_data="back_home")])
        await query.edit_message_text(text=f"📂 {main_sections.get(main_type, 'القسم')}:\nاختر الفرع المستهدف:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("view_"):
        parts = data.split("_", 2)
        main_type, sec_key = parts[1], parts[2]
        
        conn = sqlite3.connect("dark_cyber_academy.db")
        cursor = conn.cursor()
        cursor.execute("SELECT item_name FROM content WHERE main_type = ? AND sec_key = ?", (main_type, sec_key))
        items = cursor.fetchall()
        conn.close()
        
        keyboard = []
        if not items:
            keyboard.append([InlineKeyboardButton("⚠️ القطاع فارغ حالياً", callback_data="none")])
        else:
            for item in items:
                keyboard.append([InlineKeyboardButton(f"📥 {item[0]}", callback_data=f"get_{main_type}_{sec_key}_{item[0]}")])
        keyboard.append([InlineKeyboardButton("⬅️ رجوع للأقسام", callback_data=f"main_{main_type}")])
        await query.edit_message_text(text="اختر العنصر لتحميله بآمان تام:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("get_"):
        parts = data.split("_", 3)
        conn = sqlite3.connect("dark_cyber_academy.db")
        cursor = conn.cursor()
        cursor.execute("SELECT file_id, file_type FROM content WHERE main_type = ? AND sec_key = ? AND item_name = ?", (parts[1], parts[2], parts[3]))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            f_id, f_type = row
            await query.message.reply_text(f"🔄 جاري تحميل وتشفير الملف المطلوبة ({parts[3]})...")
            if f_type == "document":
                await context.bot.send_document(chat_id=query.message.chat_id, document=f_id)
            elif f_type == "photo":
                await context.bot.send_photo(chat_id=query.message.chat_id, photo=f_id)
            elif f_type == "video":
                await context.bot.send_video(chat_id=query.message.chat_id, video=f_id)

    elif data == "admin_main":
        if not role:
            await query.answer("مرفوض! هذه المنطقة خاصة بالسيد والمشرفين فقط.", show_alert=True)
            return
        keyboard = [
            [InlineKeyboardButton("📢 البث الإذاعي الشامل لجميع الرعية", callback_data="admin_broadcast_prompt")],
            [InlineKeyboardButton("🧠 زرع تحدي واختبار سيبراني (Quiz)", callback_data="admin_add_quiz")],
            [InlineKeyboardButton("📤 رفع أداة أو ملف استخباراتي جديد", callback_data="upload_choose_main")],
            [InlineKeyboardButton("🎓 إدارة الطلاب والتقييمات والدرجات", callback_data="manage_students_scores")],
            [InlineKeyboardButton("📥 فحص ومراجعة الواجبات المقدمة", callback_data="review_submissions")],
            [InlineKeyboardButton("👥 لوحة التحكم بالمشرفين والصلاحيات", callback_data="manage_admins_panel")],
            [InlineKeyboardButton("⬅️ رجوع للرئيسية", callback_data="back_home")]
        ]
        await query.edit_message_text(text=f"👑 **غرفة القيادة العليا (مستوى السيادة: {role}):**", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "manage_students_scores":
        if not role:
            return
        keyboard = [
            [InlineKeyboardButton("➕ تسجيل متدرب جديد وتوليد آيدي", callback_data="admin_add_student")],
            [InlineKeyboardButton("⭐ تعديل نقاط ودرجات متدرب", callback_data="admin_add_points")],
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
            "مثال: `كيان رعد جمال  123456789  939414`\n\n"
            "*(ملاحظة: يمكنك كتابة الاسم والآيدي المرغوب مباشرة وسيتولى البوت التقاطه)*"
        )

    elif data == "admin_add_points":
        if not role:
            return
        admin_state[user_id] = {"action": "wait_admin_points_input"}
        await query.message.reply_text("⭐ أرسل الآيدي (6 أرقام) متبوعاً بقيمة النقاط المضافة:\nمثال: `482910  50`")

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

    elif data == "manage_admins_panel":
        if role != "dark_lord":
            await query.answer("مرفوض كلياً! هذه الصلاحية للمالك حصرياً.", show_alert=True)
            return
        keyboard = [
            [InlineKeyboardButton("➕ تعيين مشرف جديد", callback_data="add_admin_step")],
            [InlineKeyboardButton("📋 استعراض طاقم الإدارة", callback_data="list_admins_panel")],
            [InlineKeyboardButton("🗑️ عزل وسحب صلاحيات مشرف", callback_data="remove_admin_step")],
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
        await query.message.reply_text("🗑️ أرسل تليجرام آيدي المشرف المراد عزله:")

    elif data == "upload_choose_main":
        if not role:
            return
        keyboard = [[InlineKeyboardButton(f"رفع في: {n}", callback_data=f"upmain_{k}")] for k, n in main_sections.items()]
        keyboard.append([InlineKeyboardButton("⬅️ رجوع", callback_data="admin_main")])
        await query.edit_message_text(text="اختر قطاع الرفع:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("upmain_"):
        if not role:
            return
        m_type = data.replace("upmain_", "")
        keyboard = [[InlineKeyboardButton(n, callback_data=f"uptarget_{m_type}_{sk}")] for sk, n in sub_sections.get(m_type, {}).items()]
        keyboard.append([InlineKeyboardButton("⬅️ رجوع", callback_data="upload_choose_main")])
        await query.edit_message_text(text="اختر الفرع المحدد:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("uptarget_"):
        if not role:
            return
        parts = data.split("_", 2)
        admin_state[user_id] = {"action": "upload_file", "main_type": parts[1], "sec_key": parts[2]}
        await query.message.reply_text("📥 أرسل الآن الملف أو الأداة (مع كتابة اسم العنصر في الـ Caption):")
