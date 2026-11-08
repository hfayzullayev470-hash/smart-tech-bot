
import os
import threading
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
import asyncio
from pypdf import PdfReader
from openai import OpenAI
from flask import Flask

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
GROQ_KEY = os.getenv("GROQ_KEY", "")

bot = Bot(token=BOT_TOKEN.strip())
dp = Dispatcher()
client = OpenAI(api_key=GROQ_KEY.strip(), base_url="https://api.groq.com/openai/v1")

app = Flask(__name__)

@app.route("/")
def home():
    return "Smart Tech bot ishlayapti! 🤖"

def run_flask():
    port = int(os.getenv("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

user_contracts = {}

def ask_ai(prompt):
    res = client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )
    return res.choices[0].message.content

@dp.message(CommandStart())
async def start(message: types.Message):
    await message.answer(
        "Salom! Men Smart Tech man 🤖\n\n"
        "Menga shartnoma yubor (PDF).\n"
        "Men uni o'qib:\n"
        "1. Bu qanday shartnoma ekanini\n"
        "2. Maqsadi nima ekanini\n"
        "3. Asillik belgilari bormi-yo'qmi\n"
        "4. Xavfli joylari qayerda ekanini aytib beraman.\n\n"
        "Keyin shartnoma bo'yicha savol bersang, shu shartnomadan javob beraman."
    )

@dp.message(F.document)
async def handle_doc(message: types.Message):
    await message.answer("Shartnomani o'qiyapman, biroz kut... ⏳")
    try:
        file = await bot.get_file(message.document.file_id)
        file_path = f"temp_{message.from_user.id}.pdf"
        await bot.download_file(file.file_path, file_path)
        reader = PdfReader(file_path)
        text = ""
        for page in reader.pages:
            t = page.extract_text()
            if t:
                text += t + "\n"
        if not text.strip():
            await message.answer("Bu PDF da matn topmadim, rasmli PDF bo'lishi mumkin. Hozircha faqat matnli PDF ni o'qiy olaman.")
            return
        user_contracts[message.from_user.id] = text
        prompt = f"""
        Sen O'zbekistonda yurist yordamchisisan, isming Smart Tech.
        Quyidagi shartnomani oddiy o'zbek tilida tahlil qil:
        1. Bu qanday shartnoma? Oldi-sotdi mi, davlat shartnomasi mi?
        2. Maqsadi nima? Nima uchun tuzilayapti?
        3. Tomonlar kim? Sotuvchi kim, xaridor kim?
        4. Summa, muddat, majburiyatlar nima?
        5. Asillik belgilari: STIR, manzil, imzo joyi, muhr joyi bormi? Nima yetishmayapti?
        6. Xavfli bandlar bormi?
        Shartnoma matni:
        {text[:8000]}
        """
        answer = ask_ai(prompt)
        await message.answer(answer[:4000])
    except Exception as e:
        await message.answer(f"Xato bo'ldi: {e}")

@dp.message(F.text)
async def qa(message: types.Message):
    contract = user_contracts.get(message.from_user.id)
    if not contract:
        await message.answer("Avval menga shartnoma yubor (PDF), keyin savol ber.")
        return
    prompt = f"""
    Faqat quyidagi shartnoma asosida javob ber, o'zingcha to'qima.
    Agar javob shartnomada yo'q bo'lsa, "Shartnomada bu haqida yozilmagan" de.
    Oddiy o'zbek tilida javob ber.
    Shartnoma: {contract[:8000]}
    Savol: {message.text}
    """
    answer = ask_ai(prompt)
    await message.answer(answer[:4000])

async def main():
    print("Smart Tech ishga tushdi!")
    threading.Thread(target=run_flask, daemon=True).start()
    await dp.start_polling(bot)

asyncio.run(main())
