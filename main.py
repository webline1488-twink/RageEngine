import asyncio
import ctypes
import os
import tempfile
from pathlib import Path

from aiogram import Bot, Dispatcher, Router, types
from aiogram.filters import Command
from aiogram.types import Message, FSInputFile
from aiogram.enums import ParseMode

# ============================================================================
# КОНФИГ
# ============================================================================
TOKEN = "8965561787:AAFLh8gu66APc161B2jjhzBpbEdDVi78oPA"

# ============================================================================
# ЗАГРУЗКА libparser.so (LOCAL СИМВОЛЫ)
# ============================================================================
LIB_PATH = "/app/libparser.so"

print("📂 Files in /app:", os.listdir("/app") if os.path.exists("/app") else "No /app dir")

if not os.path.exists(LIB_PATH):
    print(f"[ERROR] libparser.so not found at {LIB_PATH}")
    exit(1)

try:
    lib = ctypes.CDLL(LIB_PATH, mode=ctypes.RTLD_GLOBAL)
    print(f"[OK] libparser.so loaded from {LIB_PATH}")
except OSError as e:
    print(f"[ERROR] Failed to load libparser.so: {e}")
    exit(1)

# ============================================================================
# ИСПОЛЬЗУЕМ LOCAL СИМВОЛЫ (без mangled)
# ============================================================================

# parse_ydr — LOCAL символ
_parse_ydr = lib.parse_ydr
_parse_ydr.argtypes = [ctypes.c_char_p]
_parse_ydr.restype = ctypes.c_char_p

# parse_ydd — LOCAL символ
_parse_ydd = lib.parse_ydd
_parse_ydd.argtypes = [ctypes.c_char_p]
_parse_ydd.restype = ctypes.c_char_p

# parse_yft — LOCAL символ
_parse_yft = lib.parse_yft
_parse_yft.argtypes = [ctypes.c_char_p]
_parse_yft.restype = ctypes.c_char_p

def parse_ydr(path: str) -> str:
    result = _parse_ydr(path.encode())
    return result.decode() if result else ""

def parse_ydd(path: str) -> str:
    result = _parse_ydd(path.encode())
    return result.decode() if result else ""

def parse_yft(path: str) -> str:
    result = _parse_yft(path.encode())
    return result.decode() if result else ""

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
            result = parse_ydr(file_path)
        elif ext == '.ydd':
            result = parse_ydd(file_path)
        elif ext == '.yft':
            result = parse_yft(file_path)
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
