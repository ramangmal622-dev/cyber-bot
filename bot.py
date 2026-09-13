import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# ضع توكن البوت الخاص بك هنا
TOKEN = 'YOUR_BOT_TOKEN'
bot = telebot.TeleBot(TOKEN)

# 1. القائمة الرئيسية (الأزرار الأربعة للمستويات)
@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("🔒 مستوى أول (أساسيات الأمن السيبراني)", callback_data="level_1"),
        InlineKeyboardButton("🛡️ مستوى ثاني (حماية الأفراد والمبتدئين)", callback_data="level_2"),
        InlineKeyboardButton("⚙️ مستوى ثالث (الأمن المتقدم للشركات)", callback_data="level_3"),
        InlineKeyboardButton("🚀 مستوى رابع (الخبير / إدارة العمليات)", callback_data="level_4")
    )
    bot.send_message(
        message.chat.id, 
        "👑 **غرفة القيادة العليا (مستوى السيادة)**\n\nاختر مستوى الأمن السيبراني المطلوب:", 
        parse_mode="Markdown", 
        reply_markup=markup
    )


# معالج الضغط على أزرار المستويات والقوائم الفرعية
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    chat_id = call.message.chat.id
    message_id = call.message.message_id

    # --- المستوى الأول ---
    if call.data == "level_1":
        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(
            InlineKeyboardButton("➕ إضافة فرع/قسم جديد داخل الأقسام", callback_data="add_sub_sec"),
            InlineKeyboardButton("✏️ تعديل وإعادة تسمية الأقسام والفروع", callback_data="rename_all"),
            InlineKeyboardButton("📢 البث الإذاعي الشامل لجميع الرعية", callback_data="broadcast_all"),
            InlineKeyboardButton("🧠 زر تحدي واختبار سيبراني (Quiz)", callback_data="quiz"),
            InlineKeyboardButton("📥 رفع أداة أو ملف استخباراتي جديد", callback_data="upload_intel"),
            InlineKeyboardButton("🗑️ حذف ملف أو عنصر من الأرشيف", callback_data="delete_item"),
            InlineKeyboardButton("🎓 إدارة الطلاب والتقييمات والدرجات", callback_data="manage_students"),
            InlineKeyboardButton("📥 فحص ومراجعة الواجبات المقدمة", callback_data="review_assignments"),
            InlineKeyboardButton("👥 لوحة التحكم بالمشرفين والصلاحيات", callback_data="manage_admins"),
            InlineKeyboardButton("📜 سجل تدقيق نشاطات المشرفين (Logs)", callback_data="view_logs"),
            InlineKeyboardButton("🔙 رجوع للرئيسية", callback_data="back_to_home")
        )
        bot.edit_message_text("🔒 **مستوى أول: أساسيات الأمن السيبراني**\nاختر الإجراء المطلوب:", chat_id, message_id, parse_mode="Markdown", reply_markup=markup)

    # --- المستوى الثاني ---
    elif call.data == "level_2":
        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(
            InlineKeyboardButton("➕ إضافة فرع/قسم جديد داخل الأقسام", callback_data="add_sub_sec"),
            InlineKeyboardButton("✏️ تعديل وإعادة تسمية الأقسام والفروع", callback_data="rename_all"),
            InlineKeyboardButton("📢 البث الإذاعي الشامل لجميع الرعية", callback_data="broadcast_all"),
            InlineKeyboardButton("🧠 زر تحدي واختبار سيبراني (Quiz)", callback_data="quiz"),
            InlineKeyboardButton("📥 رفع أداة أو ملف استخباراتي جديد", callback_data="upload_intel"),
            InlineKeyboardButton("🗑️ حذف ملف أو عنصر من الأرشيف", callback_data="delete_item"),
            InlineKeyboardButton("🎓 إدارة الطلاب والتقييمات والدرجات", callback_data="manage_students"),
            InlineKeyboardButton("📥 فحص ومراجعة الواجبات المقدمة", callback_data="review_assignments"),
            InlineKeyboardButton("👥 لوحة التحكم بالمشرفين والصلاحيات", callback_data="manage_admins"),
            InlineKeyboardButton("📜 سجل تدقيق نشاطات المشرفين (Logs)", callback_data="view_logs"),
            InlineKeyboardButton("🔙 رجوع للرئيسية", callback_data="back_to_home")
        )
        bot.edit_message_text("🛡️ **مستوى ثاني: حماية الأفراد والمبتدئين**\nاختر الإجراء المطلوب:", chat_id, message_id, parse_mode="Markdown", reply_markup=markup)

    # --- المستوى الثالث ---
    elif call.data == "level_3":
        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(
            InlineKeyboardButton("➕ إضافة فرع/قسم جديد داخل الأقسام", callback_data="add_sub_sec"),
            InlineKeyboardButton("✏️ تعديل وإعادة تسمية الأقسام والفروع", callback_data="rename_all"),
            InlineKeyboardButton("📢 البث الإذاعي الشامل لجميع الرعية", callback_data="broadcast_all"),
            InlineKeyboardButton("🧠 زر تحدي واختبار سيبراني (Quiz)", callback_data="quiz"),
            InlineKeyboardButton("📥 رفع أداة أو ملف استخباراتي جديد", callback_data="upload_intel"),
            InlineKeyboardButton("🗑️ حذف ملف أو عنصر من الأرشيف", callback_data="delete_item"),
            InlineKeyboardButton("🎓 إدارة الطلاب والتقييمات والدرجات", callback_data="manage_students"),
            InlineKeyboardButton("📥 فحص ومراجعة الواجبات المقدمة", callback_data="review_assignments"),
            InlineKeyboardButton("👥 لوحة التحكم بالمشرفين والصلاحيات", callback_data="manage_admins"),
            InlineKeyboardButton("📜 سجل تدقيق نشاطات المشرفين (Logs)", callback_data="view_logs"),
            InlineKeyboardButton("🔙 رجوع للرئيسية", callback_data="back_to_home")
        )
        bot.edit_message_text("⚙️ **مستوى ثالث: الأمن المتقدم للشركات**\nاختر الإجراء المطلوب:", chat_id, message_id, parse_mode="Markdown", reply_markup=markup)

    # --- المستوى الرابع ---
    elif call.data == "level_4":
        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(
            InlineKeyboardButton("➕ إضافة فرع/قسم جديد داخل الأقسام", callback_data="add_sub_sec"),
            InlineKeyboardButton("✏️ تعديل وإعادة تسمية الأقسام والفروع", callback_data="rename_all"),
            InlineKeyboardButton("📢 البث الإذاعي الشامل لجميع الرعية", callback_data="broadcast_all"),
            InlineKeyboardButton("🧠 زر تحدي واختبار سيبراني (Quiz)", callback_data="quiz"),
            InlineKeyboardButton("📥 رفع أداة أو ملف استخباراتي جديد", callback_data="upload_intel"),
            InlineKeyboardButton("🗑️ حذف ملف أو عنصر من الأرشيف", callback_data="delete_item"),
            InlineKeyboardButton("🎓 إدارة الطلاب والتقييمات والدرجات", callback_data="manage_students"),
            InlineKeyboardButton("📥 فحص ومراجعة الواجبات المقدمة", callback_data="review_assignments"),
            InlineKeyboardButton("👥 لوحة التحكم بالمشرفين والصلاحيات", callback_data="manage_admins"),
            InlineKeyboardButton("📜 سجل تدقيق نشاطات المشرفين (Logs)", callback_data="view_logs"),
            InlineKeyboardButton("🔙 رجوع للرئيسية", callback_data="back_to_home")
        )
        bot.edit_message_text("🚀 **مستوى رابع: الخبير / إدارة العمليات**\nاختر الإجراء المطلوب:", chat_id, message_id, parse_mode="Markdown", reply_markup=markup)

    # --- معالجة الضغط على المهام الإدارية الجديدة ---
    elif call.data == "add_sub_sec":
        bot.answer_callback_query(call.id, text="[+] جاري فتح معالج إضافة فرع/قسم جديد...", show_alert=True)
    elif call.data == "rename_all":
        bot.answer_callback_query(call.id, text="[✎] جاري تفعيل وضع تعديل وإعادة تسمية الأقسام...", show_alert=True)
    elif call.data == "broadcast_all":
        bot.answer_callback_query(call.id, text="[📢] جاري تهيئة البث الإذاعي الشامل...", show_alert=True)
    elif call.data == "quiz":
        bot.answer_callback_query(call.id, text="[🧠] جاري تحميل التحدي والاختبار السيبراني...", show_alert=True)
    elif call.data == "upload_intel":
        bot.answer_callback_query(call.id, text="[📥] يرجى إرسال الملف أو الأداة الاستخباراتية...", show_alert=True)
    elif call.data == "delete_item":
        bot.answer_callback_query(call.id, text="[🗑️] حدد العنصر المراد حذفه من الأرشيف...", show_alert=True)
    elif call.data == "manage_students":
        bot.answer_callback_query(call.id, text="[🎓] فتح لوحة إدارة الطلاب والدرجات...", show_alert=True)
    elif call.data == "review_assignments":
        bot.answer_callback_query(call.id, text="[📥] جاري جلب الواجبات المقدمة للفحص...", show_alert=True)
    elif call.data == "manage_admins":
        bot.answer_callback_query(call.id, text="[👥] فتح لوحة التحكم بالمشرفين والصلاحيات...", show_alert=True)
    elif call.data == "view_logs":
        bot.answer_callback_query(call.id, text="[📜] جاري عرض سجل تدقيق نشاطات المشرفين (Logs)...", show_alert=True)

    # --- زر الرجوع للرئيسية ---
    elif call.data == "back_to_home":
        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(
            InlineKeyboardButton("🔒 مستوى أول (أساسيات الأمن السيبراني)", callback_data="level_1"),
            InlineKeyboardButton("🛡️ مستوى ثاني (حماية الأفراد والمبتدئين)", callback_data="level_2"),
            InlineKeyboardButton("⚙️ مستوى ثالث (الأمن المتقدم للشركات)", callback_data="level_3"),
            InlineKeyboardButton("🚀 مستوى رابع (الخبير / إدارة العمليات)", callback_data="level_4")
        )
        bot.edit_message_text(
            "👑 **غرفة القيادة العليا (مستوى السيادة)**\n\nاختر مستوى الأمن السيبراني المطلوب:", 
            chat_id, 
            message_id, 
            parse_mode="Markdown", 
            reply_markup=markup
        )

    # رد افتراضي لأي زر آخر
    else:
        bot.answer_callback_query(call.id, text="تم استلام طلبك وجاري تنفيذه...", show_alert=False)

# تشغيل البوت
if __name__ == '__main__':
    print("Bot is running...")
    bot.infinity_polling()
