
import os, threading, asyncio
from io import BytesIO
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, BotCommand
import fitz
from openai import OpenAI
from flask import Flask
from PIL import Image
import cv2, numpy as np
try:
    import docx
except:
    docx = None

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
GROQ_KEY = os.getenv("GROQ_KEY", "")
bot = Bot(token=BOT_TOKEN.strip())
dp = Dispatcher()
client = OpenAI(api_key=GROQ_KEY.strip(), base_url="https://api.groq.com/openai/v1")

app = Flask(__name__)
@app.route("/")
def home():
    return "Smart Tech 3.0 ishlayapti! 🤖✨"
def run_flask():
    port = int(os.getenv("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

user_lang = {}
user_contracts = {}
user_archives = {}  # user_id -> list of {title, text, date}

LANGS = {
    "uz": {"flag":"🇺🇿", "name":"O'zbek", "hello":"Salom! Men Smart Tech 3.0 man! 🤖✨", "choose":"Tilni tanla / Choose language:", "send":"📄 Faylni yubor — PDF / Word / TXT / Rasm", "reading":"📥 O'qiyapman... ⏳✨", "archive_title":"🗂️ Arxivingiz", "no_archive":"🗂️ Arxiv bo'sh! Hali fayl yubormagansan!", "help":"ℹ️ Yordam\n\n1️⃣ Fayl yubor — PDF / Word / TXT / Rasm\n2️⃣ Men tahlil qilib beraman ✨\n3️⃣ Keyin savol ber!"},
    "ru": {"flag":"🇷🇺", "name":"Русский", "hello":"Привет! Я Smart Tech 3.0! 🤖✨", "choose":"Выбери язык / Choose language:", "send":"📄 Отправь файл — PDF / Word / TXT / Фото", "reading":"📥 Читаю... ⏳✨", "archive_title":"🗂️ Твой архив", "no_archive":"🗂️ Архив пуст!", "help":"ℹ️ Помощь\n\n1️⃣ Отправь файл\n2️⃣ Я проанализирую ✨\n3️⃣ Задавай вопросы!"},
    "en": {"flag":"🇬🇧", "name":"English", "hello":"Hello! I'm Smart Tech 3.0! 🤖✨", "choose":"Choose language:", "send":"📄 Send file — PDF / Word / TXT / Image", "reading":"📥 Reading... ⏳✨", "archive_title":"🗂️ Your Archive", "no_archive":"🗂️ Archive is empty!", "help":"ℹ️ Help\n\n1️⃣ Send file\n2️⃣ I'll analyze ✨\n3️⃣ Ask questions!"},
    "tr": {"flag":"🇹🇷", "name":"Türkçe", "hello":"Merhaba! Ben Smart Tech 3.0! 🤖✨", "choose":"Dil seç:", "send":"📄 Dosya gönder — PDF / Word / TXT / Resim", "reading":"📥 Okuyorum... ⏳✨", "archive_title":"🗂️ Arşivin", "no_archive":"🗂️ Arşiv boş!", "help":"ℹ️ Yardım\n\n1️⃣ Dosya gönder\n2️⃣ Analiz edeceğim ✨\n3️⃣ Soru sor!"},
    "ar": {"flag":"🇸🇦", "name":"العربية", "hello":"مرحباً! أنا Smart Tech 3.0! 🤖✨", "choose":"اختر اللغة:", "send":"📄 أرسل ملف — PDF / Word / TXT / صورة", "reading":"📥 أقرأ... ⏳✨", "archive_title":"🗂️ أرشيفك", "no_archive":"🗂️ الأرشيف فارغ!", "help":"ℹ️ مساعدة\n\n1️⃣ أرسل ملف\n2️⃣ سأحلله ✨\n3️⃣ اسأل!"},
    "zh": {"flag":"🇨🇳", "name":"中文", "hello":"你好！我是 Smart Tech 3.0！🤖✨", "choose":"选择语言:", "send":"📄 发送文件 — PDF / Word / TXT / 图片", "reading":"📥 正在阅读... ⏳✨", "archive_title":"🗂️ 你的存档", "no_archive":"🗂️ 存档为空！", "help":"ℹ️ 帮助\n\n1️⃣ 发送文件\n2️⃣ 我会分析 ✨\n3️⃣ 提问！"},
}

def lang_of(uid):
    return user_lang.get(uid, "uz")
def T(uid, key):
    return LANGS[lang_of(uid)][key]

def lang_kb():
    btns = []
    row = []
    for code, info in LANGS.items():
        row.append(InlineKeyboardButton(text=f"{info['flag']} {info['name']}", callback_data=f"lang_{code}"))
        if len(row) == 2:
            btns.append(row); row=[]
    if row: btns.append(row)
    return InlineKeyboardMarkup(inline_keyboard=btns)

def main_kb(uid):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📄 Yangi fayl", callback_data="new")],
        [InlineKeyboardButton(text="🗂️ Arxiv", callback_data="archive")],
        [InlineKeyboardButton(text="🌐 Til / Language", callback_data="lang_menu")],
        [InlineKeyboardButton(text="ℹ️ Yordam", callback_data="help")],
    ])

def ask_ai(prompt):
    res = client.chat.completions.create(model="openai/gpt-oss-20b", messages=[{"role":"user","content":prompt}], temperature=0.3)
    return res.choices[0].message.content

def read_qr(data: bytes):
    try:
        arr = np.frombuffer(data, np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        det = cv2.QRCodeDetector()
        text, _, _ = det.detectAndDecode(img)
        return text.strip() if text else None
    except: return None

def read_docx_bytes(data: bytes):
    d = docx.Document(BytesIO(data))
    return "\n".join([p.text for p in d.paragraphs])

@dp.message(CommandStart())
async def start(message: types.Message):
    await message.answer(
        "🌐 <b>Tilni tanla / Choose language / Til seç / اختر اللغة / 选择语言 / Выбери язык</b> 👇",
        parse_mode="HTML", reply_markup=lang_kb()
    )

@dp.callback_query(F.data.startswith("lang_"))
async def set_lang(cb: types.CallbackQuery):
    code = cb.data.split("_")[1]
    user_lang[cb.from_user.id] = code
    info = LANGS[code]
    await cb.message.answer(
        f"{info['flag']} <b>{info['hello']}</b>\n\n"
        f"📂 {info['send']}\n"
        f"📄 PDF • 📝 Word • 📃 TXT • 🖼️ Rasm\n"
        f"🔳 QR-code ni ham o'qiy olaman!\n"
        f"🗂️ Arxivda eski fayllaring saqlanadi!",
        parse_mode="HTML", reply_markup=main_kb(cb.from_user.id)
    )
    await cb.answer()

@dp.message(Command("language"))
async def cmd_lang(message: types.Message):
    await message.answer("🌐 Tilni tanla:", reply_markup=lang_kb())

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.answer(T(message.from_user.id, "help"), reply_markup=main_kb(message.from_user.id))

@dp.message(Command("new"))
async def cmd_new(message: types.Message):
    await message.answer(T(message.from_user.id, "send"))

@dp.message(Command("archive"))
async def cmd_archive(message: types.Message):
    uid = message.from_user.id
    lst = user_archives.get(uid, [])
    if not lst:
        await message.answer(T(uid, "no_archive"))
        return
    txt = f"🗂️ <b>{T(uid,'archive_title')}</b>\n\n"
    kb_rows = []
    for i, it in enumerate(lst):
        txt += f"{i+1}. 📄 {it['title']} — {it['date']}\n"
        kb_rows.append([InlineKeyboardButton(text=f"📄 {it['title'][:30]}", callback_data=f"open_{i}")])
    await message.answer(txt, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_rows))

@dp.message(Command("settings"))
async def cmd_settings(message: types.Message):
    await message.answer("⚙️ <b>Sozlamalar</b>\n\n🌐 Tilni o'zgartirish uchun: /language\n🗂️ Arxivni ko'rish uchun: /archive\n📄 Yangi fayl uchun: /new", parse_mode="HTML")

@dp.callback_query(F.data == "lang_menu")
async def cb_lang_menu(cb: types.CallbackQuery):
    await cb.message.answer("🌐 Tilni tanla:", reply_markup=lang_kb())
    await cb.answer()
@dp.callback_query(F.data == "help")
async def cb_help(cb: types.CallbackQuery):
    await cb.message.answer(T(cb.from_user.id, "help"), reply_markup=main_kb(cb.from_user.id))
    await cb.answer()
@dp.callback_query(F.data == "new")
async def cb_new(cb: types.CallbackQuery):
    await cb.message.answer(T(cb.from_user.id, "send"))
    await cb.answer()
@dp.callback_query(F.data == "archive")
async def cb_archive(cb: types.CallbackQuery):
    uid = cb.from_user.id
    lst = user_archives.get(uid, [])
    if not lst:
        await cb.message.answer(T(uid, "no_archive"))
    else:
        txt = f"🗂️ <b>{T(uid,'archive_title')}</b>\n\n"
        kb_rows = []
        for i, it in enumerate(lst):
            txt += f"{i+1}. 📄 {it['title']} — {it['date']}\n"
            kb_rows.append([InlineKeyboardButton(text=f"📄 {it['title'][:30]}", callback_data=f"open_{i}")])
        await cb.message.answer(txt, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_rows))
    await cb.answer()

@dp.callback_query(F.data.startswith("open_"))
async def cb_open(cb: types.CallbackQuery):
    idx = int(cb.data.split("_")[1])
    uid = cb.from_user.id
    lst = user_archives.get(uid, [])
    if idx < len(lst):
        it = lst[idx]
        user_contracts[uid] = it['text']
        await cb.message.answer(f"📂 <b>{it['title']}</b> ochildi! Endi savol ber! ❓", parse_mode="HTML")
    await cb.answer()

@dp.message(F.document)
async def handle_doc(message: types.Message):
    uid = message.from_user.id
    lang = lang_of(uid)
    await message.answer(T(uid, "reading"))
    try:
        file = await bot.get_file(message.document.file_id)
        bio = BytesIO(); await bot.download_file(file.file_path, bio); data = bio.getvalue()
        fname = (message.document.file_name or "").lower()
        text = ""; kind = ""
        if fname.endswith(".pdf"):
            kind="📄 PDF"; doc = fitz.open(stream=data, filetype="pdf")
            for p in doc: text += p.get_text()
            doc.close()
        elif fname.endswith(".docx"):
            kind="📝 Word"; text = read_docx_bytes(data)
        elif fname.endswith(".txt"):
            kind="📃 TXT"; text = data.decode("utf-8", errors="ignore")
        elif fname.endswith((".jpg",".jpeg",".png",".webp")):
            qr = read_qr(data)
            if qr:
                await message.answer(f"🔳 <b>QR-code topildi!</b> ✨\n\n📦 <b>Ichida:</b>\n<code>{qr}</code>", parse_mode="HTML")
                return
            await message.answer("🖼️ Rasmda QR topmadim! PDF / Word qilib yubor!")
            return
        else:
            await message.answer("😅 Bu faylni o'qiy olmayman! PDF / Word / TXT / Rasm yubor!")
            return
        if not text.strip():
            await message.answer("📄 Faylda matn topmadim!")
            return
        user_contracts[uid] = text
        title = message.document.file_name or "Fayl"
        user_archives.setdefault(uid, []).append({"title": title, "text": text, "date": datetime.now().strftime("%d.%m %H:%M")})
        lang_name = LANGS[lang]["name"]
        prompt = f"Sen yurist yordamchisisan, isming Smart Tech. Javobni {lang_name} tilida ber, emojilar bilan, chiroyli formatda: 📄 1. Qanday shartnoma? 🎯 2. Maqsad? 👥 3. Tomonlar? 💰 4. Summa, muddat? ✅ 5. Asillik belgilari? ⚠️ 6. Xavfli bandlar? 💡 7. Xulosa. Shartnoma: {text[:8000]}"
        answer = ask_ai(prompt)
        await message.answer(f"✨ <b>Tahlil tayyor!</b> {kind}\n\n{answer[:3800]}", parse_mode="HTML", reply_markup=main_kb(uid))
    except Exception as e:
        await message.answer(f"❌ Xato: {e}")

@dp.message(F.photo)
async def handle_photo(message: types.Message):
    await message.answer("🖼️ Rasmni tekshirayapman... 🔍")
    try:
        photo = message.photo[-1]
        file = await bot.get_file(photo.file_id)
        bio = BytesIO(); await bot.download_file(file.file_path, bio); data = bio.getvalue()
        qr = read_qr(data)
        if qr:
            await message.answer(f"🔳 <b>QR-code topildi!</b> ✨\n\n📦 <b>Ichida:</b>\n<code>{qr}</code>", parse_mode="HTML")
        else:
            await message.answer("🖼️ Rasmda QR topmadim! PDF qilib yubor!")
    except Exception as e:
        await message.answer(f"❌ Xato: {e}")

@dp.message(F.text)
async def qa(message: types.Message):
    if message.text.startswith("/"): return
    uid = message.from_user.id
    contract = user_contracts.get(uid)
    if not contract:
        await message.answer(T(uid, "send"))
        return
    lang_name = LANGS[lang_of(uid)]["name"]
    prompt = f"Faqat shartnoma asosida javob ber, {lang_name} tilida, emojilar bilan. Agar yo'q bo'lsa '📌 Shartnomada yozilmagan' de. Shartnoma: {contract[:8000]} Savol: {message.text}"
    answer = ask_ai(prompt)
    await message.answer(f"💬 <b>Javob:</b>\n\n{answer[:3800]}", parse_mode="HTML")

async def main():
    await bot.set_my_commands([
        BotCommand(command="start", description="🏠 Bosh sahifa / Til tanlash"),
        BotCommand(command="new", description="📄 Yangi shartnoma yuborish"),
        BotCommand(command="archive", description="🗂️ Arxiv - eski shartnomalar"),
        BotCommand(command="language", description="🌐 Tilni o'zgartirish"),
        BotCommand(command="help", description="ℹ️ Yordam"),
        BotCommand(command="settings", description="⚙️ Sozlamalar"),
    ])
    print("Smart Tech 3.0 ishga tushdi!")
    threading.Thread(target=run_flask, daemon=True).start()
    await dp.start_polling(bot)

asyncio.run(main())
