import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
from yt_dlp import YoutubeDL

# Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Escape MarkdownV2
def escape_markdown_v2(text):
    if not text:
        return ""
    escape_chars = r"\_*[]()~`>#+-=|{}.!'"
    return "".join(f"\\{c}" if c in escape_chars else c for c in text)

# Start command
async def start(update: Update, context: CallbackContext):
    await update.message.reply_text(
        "Hi! Send me any YouTube link (Shorts or video) and I will download it for you."
    )

# Download function
def download_media(url: str):
    ydl_opts = {
        "format": "bv*+ba/best",  # ✅ FIXED STABLE FORMAT
        "outtmpl": "media_%(id)s.%(ext)s",
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "retries": 3,
        "fragment_retries": 3,
        "cookiefile": "youtube_cookies.txt",  # ✅ your cookies
        "merge_output_format": "mp4",
        "postprocessors": [{
            "key": "FFmpegVideoConvertor",
            "preferedformat": "mp4",
        }],
    }

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            return filename, info
    except Exception as e:
        logger.error(f"Download error: {e}")
        return None, None

# Handler
async def handle_message(update: Update, context: CallbackContext):
    user_message = update.message.text.strip()
    chat_id = update.message.chat_id
    message_id = update.message.message_id
    username = update.message.from_user.username or update.message.from_user.first_name

    if ("youtube.com" in user_message or "youtu.be" in user_message) and "http" in user_message:
        downloading_msg = await update.message.reply_text(
            "<code>Trying to download...</code>",
            parse_mode="HTML"
        )

        file_path = None

        try:
            file_path, info = download_media(user_message)

            if not file_path or not info:
                raise Exception("Download failed")

            title = info.get("title", "YouTube Video")
            thumbnail = info.get("thumbnail")

            caption = (
                f"✨ *Your media is ready\\!* ✨\n\n"
                f"🆔 *User:* `{escape_markdown_v2(username)}`\n"
                f"🎬 *Title:* {escape_markdown_v2(title)}\n"
                f"🎥 *Link:* [Click here]({escape_markdown_v2(user_message)})\n"
                f"📥 *Processed with ❤️*"
            )

            # Button
            keyboard = [[InlineKeyboardButton("🔗 Open Video", url=user_message)]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            # Thumbnail preview
            if thumbnail:
                try:
                    await context.bot.send_photo(chat_id=chat_id, photo=thumbnail)
                except:
                    pass

            # Send video
            with open(file_path, "rb") as video:
                await context.bot.send_video(
                    chat_id=chat_id,
                    video=video,
                    caption=caption,
                    parse_mode="MarkdownV2",
                    reply_markup=reply_markup,
                    reply_to_message_id=message_id,
                )

            # Cleanup messages
            await context.bot.delete_message(chat_id=chat_id, message_id=downloading_msg.message_id)
            await context.bot.delete_message(chat_id=chat_id, message_id=message_id)

        except Exception as e:
            logger.error(f"Handler error: {e}")

            await context.bot.send_message(
                chat_id=chat_id,
                text="❌ Failed to download video.\nPossible reasons:\n- Private video\n- Age restricted\n- Region blocked\n- Cookies expired",
                reply_to_message_id=message_id,
            )

            try:
                await context.bot.delete_message(chat_id=chat_id, message_id=downloading_msg.message_id)
            except:
                pass

        finally:
            # Delete file
            try:
                if file_path and os.path.exists(file_path):
                    os.remove(file_path)
            except:
                pass

    else:
        if update.message.chat.type == "private":
            await update.message.reply_text("Please send a valid YouTube link.")

# Main
if __name__ == "__main__":
    TOKEN = "YOUR_NEW_BOT_TOKEN"  # ⚠️ REGENERATE USING BOTFATHER

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot is running...")
    app.run_polling()
