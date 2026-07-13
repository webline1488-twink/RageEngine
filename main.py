import asyncio
import ctypes
import os
import tempfile
from pathlib import Path

import requests
import zipfile
import io
from aiogram import Bot, Dispatcher, Router, types
from aiogram.filters import Command
from aiogram.types import Message, FSInputFile
from aiogram.enums import ParseMode

# ============================================================================
# КОНФИГ
# ============================================================================
TOKEN = "8965561787:AAFLh8gu66APc161B2jjhzBpbEdDVi78oPA"

# ============================================================================
# АВТО-ЗАГРУЗКА libparser.so ИЗ RELEASE
# ============================================================================
LIB_PATH = os.path.join(os.path.dirname(__file__), "libparser.so")

if not os.path.exists(LIB_PATH):
    print("[INFO] libparser.so not found. Downloading from GitHub release...")
    try:
        url = "https://github.com/webline1488-twink/RageEngine/releases/download/v1.0.1/libparser.zip"
        response = requests.get(url, timeout=60)
        response.raise_for_status()

        with zipfile.ZipFile(io.BytesIO(response.content)) as z:
            with open(LIB_PATH, "wb") as f:
                f.write(z.read("libparser.so"))

        print("[SUCCESS] libparser.so downloaded and extracted!")
    except Exception as e:
        print(f"[ERROR] Failed to download/extract: {e}")
        exit(1)

# Загружаем библиотеку
try:
    lib = ctypes.CDLL(LIB_PATH)
    print(f"[OK] libparser.so loaded from {LIB_PATH}")
except OSError as e:
    print(f"[ERROR] Failed to load libparser.so: {e}")
    exit(1)

# Настройка функций
lib.parse_ydr.argtypes = [ctypes.c_char_p]
lib.parse_ydr.restype = ctypes.c_char_p

lib.parse_ydd.argtypes = [ctypes.c_char_p]
lib.parse_ydd.restype = ctypes.c_char_p

lib.parse_yft.argtypes = [ctypes.c_char_p]
lib.parse_yft.restype = ctypes.c_char_p

# ============================================================================
# БОТ
# ============================================================================
bot = Bot(token=TOKEN)
dp = Dispatcher()
router = Router()

@router.message(Command("start"))
async def start_command(message: Message):
    await message.answer(
        "👋 Привет! Я парсер GTA V файлов.\n\n"
        "📁 Отправь мне файлы .ydd, .ydr или .yft\n"
        "Я покажу всю информацию о модели.\n\n"
        "🛠 Поддерживаемые форматы:\n"
        "• .ydd — Drawable Dictionary\n"
        "• .ydr — Drawable (модель)\n"
        "• .yft — Fragment (физика)"
    )

@router.message(Command("help"))
async def help_command(message: Message):
    await message.answer(
        "📖 Помощь:\n\n"
        "1. Отправь файл с расширением .ydd, .ydr или .yft\n"
        "2. Бот распарсит и покажет:\n"
        "   • Версию\n"
        "   • Количество материалов\n"
        "   • Количество LOD\n"
        "   • Количество вершин, индексов, полигонов\n"
        "   • Наличие скелета\n"
        "   • Наличие коллизий\n"
        "   • И многое другое"
    )

@router.message(lambda msg: msg.document is not None)
async def handle_file(message: Message):
    doc = message.document
    filename = doc.file_name or "file"

    ext = Path(filename).suffix.lower()
    if ext not in ['.ydd', '.ydr', '.yft']:
        await message.answer(
            f"❌ Неподдерживаемый формат: {ext}\n"
            "Поддерживаются: .ydd, .ydr, .yft"
        )
        return

    status_msg = await message.answer(f"⏳ Парсинг {filename}...")

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            file_path = tmp.name
        
        await bot.download(doc, file_path)

        if ext == '.ydr':
            result = lib.parse_ydr(file_path.encode()).decode()
        elif ext == '.ydd':
            result = lib.parse_ydd(file_path.encode()).decode()
        elif ext == '.yft':
            result = lib.parse_yft(file_path.encode()).decode()
        else:
            result = "❌ Неизвестный формат"

        os.unlink(file_path)

        if result.startswith("Error:"):
            await status_msg.edit_text(f"❌ {result}")
        else:
            if len(result) > 4000:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as txt:
                    txt_path = txt.name
                    txt.write(result.encode())
                
                await status_msg.delete()
                await message.answer_document(
                    FSInputFile(txt_path, filename=f"{Path(filename).stem}_info.txt"),
                    caption=f"📊 Результат парсинга {filename}"
                )
                os.unlink(txt_path)
            else:
                await status_msg.edit_text(
                    f"📊 Результат парсинга {filename}:\n\n"
                    f"```\n{result}\n```",
                    parse_mode=ParseMode.MARKDOWN
                )

    except Exception as e:
        await status_msg.edit_text(f"❌ Ошибка: {str(e)}")

@router.message()
async def unknown_message(message: Message):
    await message.answer(
        "❌ Отправь мне файл .ydd, .ydr или .yft\n"
        "Или напиши /help для справки"
    )

# ============================================================================
# ЗАПУСК
# ============================================================================
async def main():
    dp.include_router(router)
    print("🤖 Бот запущен!")
    print(f"📁 libparser.so: {LIB_PATH}")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
