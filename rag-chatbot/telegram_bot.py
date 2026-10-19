import asyncio
import logging
import os
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from services.telegram_service import update_rating

from dotenv import load_dotenv

from telegram.constants import ChatAction
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters,
)


from rag import run_rag
from services.telegram_service import (
    ensure_active_conversation,
    add_message,
    deactivate_all_conversations,
    create_conversation,
    update_conversation_title,
    get_conversations,
    activate_conversation,
    get_conversation_by_index,
)

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

MAX_TELEGRAM_MESSAGE_LENGTH = 4096


def split_message(text: str, max_length: int = MAX_TELEGRAM_MESSAGE_LENGTH) -> list[str]:
    if len(text) <= max_length:
        return [text]

    chunks = []
    remaining = text
    while remaining:
        chunk = remaining[:max_length]
        split_at = chunk.rfind("\n")
        if split_at < max_length // 2:
            split_at = max_length

        chunks.append(remaining[:split_at].strip())
        remaining = remaining[split_at:].strip()

    return [chunk for chunk in chunks if chunk]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Halo! Kirim pertanyaan, nanti aku jawab berdasarkan dokumen RAG."
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Kirim pertanyaan sebagai pesan biasa. Gunakan /debug pertanyaan untuk cek konteks RAG."
    )

    

    try:
        index = int(context.args[0])
    except ValueError:
        await update.message.reply_text(
            "Nomor tidak valid."
        )
        return

    conversation = get_conversation_by_index(
        update.effective_user.id,
        index,
    )
    

    if conversation is None:
        await update.message.reply_text(
            "Conversation tidak ditemukan."
        )
        return

    deactivate_all_conversations(
        update.effective_user.id,
    )

    activate_conversation(
        conversation["id"],
    )

    await update.message.reply_text(
        f"✅ Conversation '{conversation['title']}' dibuka."
    )
async def open_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("OPEN CALLED")
    print(context.args)

    if not context.args:
        await update.message.reply_text("Gunakan /open <nomor>")
        return

    try:
        index = int(context.args[0])
        print("INDEX:", index)
    except ValueError:
        await update.message.reply_text("Nomor tidak valid.")
        return

    conversation = get_conversation_by_index(
        update.effective_user.id,
        index,
    )

    print("CONVERSATION:", conversation)

    if conversation is None:
        await update.message.reply_text("Conversation tidak ditemukan.")
        return

    print("Deactivate...")
    deactivate_all_conversations(update.effective_user.id)

    print("Activate...")
    activate_conversation(conversation["id"])

    await update.message.reply_text(
        f"✅ Conversation '{conversation['title']}' dibuka."
    )
async def new_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat

    deactivate_all_conversations(user.id)

    create_conversation(
        telegram_id=user.id,
        telegram_chat_id=chat.id,
        username=user.username,
        first_name=user.first_name,
    )

    await update.message.reply_text(
        "✅ Percakapan baru berhasil dibuat."
    )



async def debug_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    question = " ".join(context.args).strip()
    if not question:
        await update.message.reply_text("Pakai format: /debug pertanyaan kamu")
        return

    await update.message.chat.send_action(action=ChatAction.TYPING)

    try:
        result = await asyncio.to_thread(run_rag, question)
    except Exception:
        logger.exception("Failed to process Telegram debug message")
        await update.message.reply_text("Debug gagal. Cek log terminal untuk detail error.")
        return

    context_preview = result.get("context", "").strip()
    if len(context_preview) > 1500:
        context_preview = f"{context_preview[:1500]}..."

    debug_text = (
        f"Jumlah hasil Supabase: {result.get('result_count', 0)}\n"
        f"Panjang konteks: {len(result.get('context', ''))} karakter\n\n"
        f"Preview konteks:\n{context_preview or '(kosong)'}"
    )

    for chunk in split_message(debug_text):
        await update.message.reply_text(chunk)

async def history_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conversations = get_conversations(
        update.effective_user.id
    )

    if not conversations:
        await update.message.reply_text(
            "📭 Belum ada riwayat percakapan."
        )
        return

    text = "📚 Riwayat Percakapan\n\n"

    for i, conv in enumerate(conversations, start=1):
        text += (
            f"{i}. {conv['title']}\n"
            f"💬 {conv['message_count']} pesan\n"
            f"🕒 {conv['updated_at'][:16]}\n\n"
        )

    text += "Gunakan /open <nomor>"

    await update.message.reply_text(text)
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    question = update.message.text.strip()

    if not question:
        return

    user = update.effective_user
    chat = update.effective_chat

    await update.message.chat.send_action(action=ChatAction.TYPING)

    try:
        # Cari / buat conversation aktif
        conversation = ensure_active_conversation(
            telegram_id=user.id,
            telegram_chat_id=chat.id,
            username=user.username,
            first_name=user.first_name,
        )

        # Simpan pesan user
        add_message(
            conversation_id=conversation["id"],
            role="user",
            content=question,
        )

        # Kalau ini chat baru, ubah judul
        if conversation["title"] == "New Chat":
            title = question.strip()

            if len(title) > 50:
                title = title[:50].rstrip() + "..."

            update_conversation_title(
                conversation["id"],
                title,
            )

        # Jalankan RAG
        result = await asyncio.to_thread(run_rag, question)
        answer = result.get("answer", "Maaf, jawaban tidak tersedia.")

        # Simpan jawaban assistant
        assistant_message = add_message(
            conversation_id=conversation["id"],
            role="assistant",
            content=answer,
        )

        # Tombol feedback
        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "👍 Membantu",
                        callback_data=f"rate:{assistant_message['id']}:1",
                    ),
                    InlineKeyboardButton(
                        "👎 Tidak Membantu",
                        callback_data=f"rate:{assistant_message['id']}:0",
                    ),
                ]
            ]
        )

        # Kirim jawaban
        chunks = split_message(answer)

        for i, chunk in enumerate(chunks):
            if i == len(chunks) - 1:
                await update.message.reply_text(
                    chunk,
                    reply_markup=keyboard,
                )
            else:
                await update.message.reply_text(chunk)

    except Exception:
        logger.exception("Failed to process Telegram message")
        await update.message.reply_text(
            "Maaf, terjadi error saat memproses pertanyaan. Coba lagi sebentar ya."
        )
async def feedback_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        await query.answer()

        print("CALLBACK:", query.data)

        _, message_id, rating = query.data.split(":")

        print("MESSAGE:", message_id)
        print("RATING:", rating)

        result = update_rating(
            message_id=message_id,
            rating=int(rating),
        )

        print("UPDATE RESULT:", result)

        await query.edit_message_reply_markup(reply_markup=None)

        await query.message.reply_text(
            "❤️ Terima kasih atas feedback Anda!"
        )

    except Exception:
        import traceback
        traceback.print_exc()

def main() -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN belum diatur di file .env")

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("new", new_chat))
    app.add_handler(CommandHandler("debug", debug_command))
    app.add_handler(CommandHandler("history", history_command))
    app.add_handler(CommandHandler("open",open_command,))

    app.add_handler(CallbackQueryHandler(feedback_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    

    logger.info("Telegram bot is running")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
