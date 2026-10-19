import os
import asyncio
import logging

from dotenv import load_dotenv
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
from telegram.request import HTTPXRequest

from rag_qdrantpt2 import run_rag


from services.telegram_service import (
    ensure_active_conversation,
    add_message,
    deactivate_all_conversations,
    create_conversation,
    update_conversation_title,
    get_conversations,
    activate_conversation,
    get_conversation_by_index,
    update_rating,
)


# ============================================================
# CONFIG
# ============================================================

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not TOKEN:
    raise RuntimeError(
        "TELEGRAM_BOT_TOKEN tidak ditemukan di file .env"
    )


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", # <--- Jadikan satu baris ini
    level=logging.INFO,
)

logger = logging.getLogger(__name__)


# ============================================================
# TELEGRAM HTTP REQUEST
# ============================================================

request = HTTPXRequest(
    connect_timeout=30,
    read_timeout=30,
    write_timeout=30,
    pool_timeout=30,
)


# ============================================================
# MESSAGE SPLITTER
# Telegram maksimal sekitar 4096 karakter per pesan
# ============================================================

def split_message(text, max_length=4000):
    """
    Membagi pesan panjang menjadi beberapa bagian
    agar aman dikirim ke Telegram.
    """

    if not text:
        return [""]

    if len(text) <= max_length:
        return [text]

    chunks = []

    while len(text) > max_length:

        split_at = text.rfind("\n", 0, max_length)

        if split_at == -1:
            split_at = text.rfind(" ", 0, max_length)

        if split_at == -1:
            split_at = max_length

        chunks.append(text[:split_at])
        text = text[split_at:].lstrip()

    if text:
        chunks.append(text)

    return chunks


# ============================================================
# /START
# ============================================================

async def start_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    user = update.effective_user

    if not user:
        return

    telegram_id = user.id

    try:
        conversation = await asyncio.to_thread(
    ensure_active_conversation,
    telegram_id,
    update.effective_chat.id,
    user.username,
    user.first_name,
)

        if not conversation:
            await asyncio.to_thread(
                create_conversation,
                telegram_id,
            )

    except Exception:
        logger.exception("Error saat membuat conversation")

    text = (
        "👋 Halo! Saya **Kurubot**.\n\n"
        "Saya adalah chatbot informasi akademik berbasis "
        "RAG yang dapat membantu menjawab pertanyaan "
        "seputar informasi akademik.\n\n"
        "Silakan langsung kirim pertanyaan kamu. 😊\n\n"
        "Contoh:\n"
        "• Bagaimana cara mahasiswa mendaftar akun?\n"
        "• Apa syarat pendaftaran wisuda?\n"
        "• Bagaimana proses pendaftaran sidang?\n\n"
        "Gunakan /help untuk melihat daftar perintah."
    )

    await update.message.reply_text(
        text,
        parse_mode="Markdown",
    )


# ============================================================
# /HELP
# ============================================================

async def help_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    text = (
        "📚 **Bantuan Kurubot**\n\n"
        "Kamu bisa langsung mengirim pertanyaan "
        "tentang informasi akademik.\n\n"
        "**Perintah yang tersedia:**\n\n"
        "/start — Memulai bot\n"
        "/help — Menampilkan bantuan\n"
        "/new — Membuat percakapan baru\n"
        "/history — Melihat riwayat percakapan\n"
        "/open <nomor> — Membuka percakapan dari riwayat\n"
        "/debug — Melihat informasi retrieval RAG\n\n"
        "Contoh pertanyaan:\n"
        "• Bagaimana cara mahasiswa mendaftar akun?\n"
        "• Apa syarat untuk pendaftaran wisuda?\n"
        "• Bagaimana cara mengajukan surat pengantar?"
    )

    await update.message.reply_text(
        text,
        parse_mode="Markdown",
    )


# ============================================================
# /NEW
# ============================================================

async def new_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    telegram_id = update.effective_user.id

    try:

        await asyncio.to_thread(
            deactivate_all_conversations,
            telegram_id,
        )

        await asyncio.to_thread(
            create_conversation,
            telegram_id,
        )

        await update.message.reply_text(
            "🆕 Percakapan baru berhasil dibuat.\n\n"
            "Silakan kirim pertanyaan kamu."
        )

    except Exception as e:

        logger.exception("Error /new")

        await update.message.reply_text(
            f"❌ Gagal membuat percakapan baru.\n"
            f"Error: {e}"
        )


# ============================================================
# /HISTORY
# ============================================================

async def history_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    telegram_id = update.effective_user.id

    try:

        conversations = await asyncio.to_thread(
            get_conversations,
            telegram_id,
        )

        if not conversations:
            await update.message.reply_text(
                "📭 Belum ada riwayat percakapan."
            )
            return

        lines = ["📚 **Riwayat Percakapan**\n"]

        for index, conversation in enumerate(
            conversations,
            start=1,
        ):

            title = (
                conversation.get("title")
                or "New Chat"
            )

            lines.append(
                f"{index}. {title}"
            )

        lines.append(
            "\nGunakan `/open <nomor>` untuk membuka percakapan."
        )

        await update.message.reply_text(
            "\n".join(lines),
            parse_mode="Markdown",
        )

    except Exception as e:

        logger.exception("Error /history")

        await update.message.reply_text(
            f"❌ Gagal mengambil riwayat.\n"
            f"Error: {e}"
        )


# ============================================================
# /OPEN
# ============================================================

async def open_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    telegram_id = update.effective_user.id

    if not context.args:

        await update.message.reply_text(
            "Gunakan format:\n"
            "`/open 1`",
            parse_mode="Markdown",
        )

        return

    try:

        index = int(context.args[0])

    except ValueError:

        await update.message.reply_text(
            "❌ Nomor percakapan harus berupa angka."
        )

        return

    try:

        conversation = await asyncio.to_thread(
            get_conversation_by_index,
            telegram_id,
            index,
        )

        if not conversation:

            await update.message.reply_text(
                "❌ Percakapan tidak ditemukan."
            )

            return

        conversation_id = conversation.get("id")

        await asyncio.to_thread(
            activate_conversation,
            telegram_id,
            conversation_id,
        )

        title = (
            conversation.get("title")
            or "New Chat"
        )

        await update.message.reply_text(
            f"✅ Percakapan **{title}** berhasil dibuka.",
            parse_mode="Markdown",
        )

    except Exception as e:

        logger.exception("Error /open")

        await update.message.reply_text(
            f"❌ Gagal membuka percakapan.\n"
            f"Error: {e}"
        )


# ============================================================
# /DEBUG
# ============================================================

async def debug_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if not context.args:

        await update.message.reply_text(
            "Gunakan format:\n"
            "`/debug pertanyaan kamu`",
            parse_mode="Markdown",
        )

        return

    question = " ".join(context.args)

    await update.message.reply_text(
        "🔎 Menjalankan Qdrant RAG..."
    )

    try:

        result = await asyncio.to_thread(
            run_rag,
            question,
        )

        rewritten_query = result.get(
            "rewritten_query",
            "-"
        )

        result_count = result.get(
            "result_count",
            0
        )

        matches = result.get(
            "matches",
            []
        )

        lines = [
            "🔎 **Qdrant RAG Debug**",
            "",
            f"**Pertanyaan:**\n{question}",
            "",
            f"**Rewritten Query:**\n{rewritten_query}",
            "",
            f"**Jumlah hasil:** {result_count}",
            "",
            "**Top Retrieval:**",
        ]

        for i, match in enumerate(
            matches[:5],
            start=1,
        ):

            score = match.get("score", 0)

            chunk_id = match.get(
                "chunk_id",
                "-"
            )

            section = match.get(
                "section",
                "-"
            )

            page_start = match.get(
                "page_start",
                "-"
            )

            page_end = match.get(
                "page_end",
                "-"
            )

            lines.append(
                f"\n{i}. "
                f"Score: `{score:.4f}`\n"
                f"Chunk: `{chunk_id}`\n"
                f"Section: {section}\n"
                f"Page: {page_start}-{page_end}"
            )

        await update.message.reply_text(
            "\n".join(lines),
            parse_mode="Markdown",
        )

    except Exception as e:

        logger.exception("Error /debug")

        await update.message.reply_text(
            f"❌ Debug RAG gagal.\n\n"
            f"Error: {e}"
        )


# ============================================================
# FEEDBACK CALLBACK
# ============================================================

async def feedback_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    query = update.callback_query

    await query.answer()

    try:

        data = query.data

        # Format:
        # rating:1:message_id
        # rating:0:message_id

        parts = data.split(":")

        if len(parts) < 3:
            return

        rating = int(parts[1])
        message_id = parts[2]

        await asyncio.to_thread(
            update_rating,
            message_id,
            rating,
        )

        await query.edit_message_reply_markup(
            reply_markup=None
        )

    except Exception:

        logger.exception(
            "Error saat memberikan feedback"
        )


# ============================================================
# HANDLE USER MESSAGE
# ============================================================

async def handle_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if not update.message or not update.message.text:
        return

    user = update.effective_user
    if not user:
        return

    telegram_id = user.id
    question = update.message.text.strip()

    if not question:
        return

    logger.info("Question from %s: %s", telegram_id, question)

    try:
        # ----------------------------------------------------
        # Pastikan conversation aktif
        # ----------------------------------------------------
        conversation = await asyncio.to_thread(
            ensure_active_conversation,
            telegram_id,
            update.effective_chat.id,
            user.username,
            user.first_name,
        )

        if not conversation:
            conversation = await asyncio.to_thread(
                create_conversation,
                telegram_id,
            )

        conversation_id = conversation.get("id")

        # ----------------------------------------------------
        # Simpan pesan user
        # ----------------------------------------------------
        await asyncio.to_thread(
            add_message,
            conversation_id,
            "user",
            question,
        )

        # ----------------------------------------------------
        # Auto title
        # ----------------------------------------------------
        current_title = conversation.get("title") or ""
        if not current_title or current_title.lower() == "new chat":
            title = question[:60]
            await asyncio.to_thread(
                update_conversation_title,
                conversation_id,
                title,
            )

        # ----------------------------------------------------
        # Loading message
        # ----------------------------------------------------
        loading_message = await update.message.reply_text(
            "🔎 Sedang mencari informasi..."
        )

        # ----------------------------------------------------
        # RAG
        # ----------------------------------------------------
        result = await asyncio.to_thread(
            run_rag,
            question,
        )

        answer = result.get(
            "answer",
            "Maaf, saya belum dapat menemukan jawaban."
        )

        # ----------------------------------------------------
        # Ambil Referensi Dokumen & Logging Debug
        # ----------------------------------------------------
        referenced_docs = result.get("referenced_docs", [])
        
        # LOGGING UNTUK MEMANTAU ISI DOKUMEN REFERENSI DI TERMINAL
        logger.info(">>> DEBUG REFERENCED DOCS (%d): %s", len(referenced_docs), referenced_docs)

        if referenced_docs:
            answer += "\n\n📚 *Sumber Referensi:*"
            for idx, doc in enumerate(referenced_docs, 1):
                title = doc.get("title", "Dokumen Akademik")
                url = doc.get("download_url", "")
                
                if url:
                    answer += f"\n{idx}. [{title}]({url})"
                else:
                    answer += f"\n{idx}. {title}"

        # ----------------------------------------------------
        # Simpan jawaban assistant
        # ----------------------------------------------------
        assistant_message = await asyncio.to_thread(
            add_message,
            conversation_id,
            "assistant",
            answer,
        )

        # ----------------------------------------------------
        # Hapus loading message
        # ----------------------------------------------------
        try:
            await loading_message.delete()
        except Exception:
            pass

        # ----------------------------------------------------
        # Feedback button
        # ----------------------------------------------------
        message_id = None
        if isinstance(assistant_message, dict):
            message_id = (
                assistant_message.get("id")
                or assistant_message.get("message_id")
            )

        if message_id is None:
            message_id = str(update.message.message_id)

        keyboard = [
            [
                InlineKeyboardButton(
                    "👍",
                    callback_data=f"rating:1:{message_id}",
                ),
                InlineKeyboardButton(
                    "👎",
                    callback_data=f"rating:0:{message_id}",
                ),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # ----------------------------------------------------
        # Kirim jawaban ke Telegram
        # ----------------------------------------------------
        answer_chunks = split_message(answer)

        for index, chunk in enumerate(answer_chunks):
            if index == len(answer_chunks) - 1:
                await update.message.reply_text(
                    chunk,
                    reply_markup=reply_markup,
                    parse_mode="Markdown",            # Mengaktifkan format Markdown link
                    disable_web_page_preview=True     # Mencegah preview web otomatis
                )
            else:
                await update.message.reply_text(
                    chunk,
                    parse_mode="Markdown",            # Mengaktifkan format Markdown link
                    disable_web_page_preview=True
                )

        logger.info("RAG response sent successfully")

    except Exception as e:
        logger.exception("Error handle_message")
        await update.message.reply_text(
            "❌ Terjadi kesalahan saat memproses pertanyaan.\n\n"
            f"Detail: {e}"
        )

# ============================================================
# ERROR HANDLER
# ============================================================

async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE,
):

    logger.error(
        "Telegram error: %s",
        context.error,
        exc_info=context.error,
    )


# ============================================================
# MAIN
# ============================================================

def main():

    logger.info(
        "Telegram Qdrant RAG bot is starting..."
    )

    app = (
        Application.builder()
        .token(TOKEN)
        .request(request)
        .build()
    )

    # --------------------------------------------------------
    # Commands
    # --------------------------------------------------------

    app.add_handler(
        CommandHandler(
            "start",
            start_command,
        )
    )

    app.add_handler(
        CommandHandler(
            "help",
            help_command,
        )
    )

    app.add_handler(
        CommandHandler(
            "new",
            new_command,
        )
    )

    app.add_handler(
        CommandHandler(
            "history",
            history_command,
        )
    )

    app.add_handler(
        CommandHandler(
            "open",
            open_command,
        )
    )

    app.add_handler(
        CommandHandler(
            "debug",
            debug_command,
        )
    )

    # --------------------------------------------------------
    # Feedback
    # --------------------------------------------------------

    app.add_handler(
        CallbackQueryHandler(
            feedback_callback,
            pattern=r"^rating:",
        )
    )

    # --------------------------------------------------------
    # Normal messages
    # --------------------------------------------------------

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_message,
        )
    )

    # --------------------------------------------------------
    # Error handler
    # --------------------------------------------------------

    app.add_error_handler(
        error_handler
    )

    logger.info(
        "Telegram Qdrant RAG bot is running"
    )

    # --------------------------------------------------------
    # Polling
    # --------------------------------------------------------

    app.run_polling(
        allowed_updates=Update.ALL_TYPES
    )


if __name__ == "__main__":
    main()