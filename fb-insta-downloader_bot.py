import logging
import os
import yt_dlp
import requests
import re
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from yt_dlp import YoutubeDL

# Logging setup
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Telegram Bot Token (Replace this with your actual bot token)
TELEGRAM_BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"

# =========================
# FACEBOOK DOWNLOADER PART
# =========================

# Function to check if URL is a valid Facebook video link
def is_facebook_video(url: str) -> bool:
    facebook_patterns = [
        r"https?://(?:www\.)?facebook\.com/.+/videos/\d+",
        r"https?://(?:www\.)?fb\.watch/[\w\-_]+/?",
        r"https?://(?:www\.)?facebook\.com/reel/\d+",
        r"https?://(?:www\.)?facebook\.com/share/v/.+",
        r"https?://(?:www\.)?facebook\.com/share/r/.+",
        r"https?://(?:www\.)?facebook\.com/watch/v/.+"
    ]
    return any(re.match(pattern, url) for pattern in facebook_patterns)

# Function to extract the direct Facebook video URL
def get_facebook_video_url(url: str, quality: str = "best") -> str:
    """Extracts the direct video URL from Facebook using yt-dlp."""
    ydl_opts = {
        "quiet": True,
        "format": f"{quality}[ext=mp4]",
        "dump_single_json": True,  # Extract JSON metadata instead of downloading
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return info["url"] if "url" in info else None
    except Exception as e:
        logger.error(f"Error extracting direct video URL: {e}")
        return None

# Function to download video using yt-dlp
def download_video(url: str, output_path: str, quality: str = "best") -> str:
    ydl_opts = {
        "outtmpl": output_path,
        "quiet": True,
        "format": f"{quality}[ext=mp4]",
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        return output_path
    except Exception as e:
        logger.error(f"Download error: {e}")
        return None

# Function to escape special characters for MarkdownV2 (FACEBOOK VERSION)
def escape_markdown_v2_fb(text: str) -> str:
    special_chars = r"[_*\[\]()~`>#+\-=|{}.!]"
    return re.sub(f"({special_chars})", r"\\\1", text)

# =========================
# INSTAGRAM DOWNLOADER PART
# =========================

# Function to escape special characters for Markdown V2 formatting (INSTAGRAM VERSION)
def escape_markdown_v2_insta(text):
    escape_chars = r"\_*[]()~`>#+-=|{}.!'"
    return "".join(f"\\{char}" if char in escape_chars else char for char in text)

# Function to download media from Instagram using yt-dlp
def download_media(insta_url: str):
    ydl_opts = {
        "format": "best",  # Download the best quality available
        "outtmpl": "media_%(id)s.%(ext)s",  # Output file name template
        "quiet": True,  # Suppress yt-dlp output
        "no_warnings": True,  # Suppress warnings
        "cookiefile": "instagram_cookies.txt",  # Path to your cookies file
    }

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(insta_url, download=True)
            filename = ydl.prepare_filename(info_dict)
            return filename, info_dict.get("ext", "mp4"), info_dict.get("id", "Unknown ID")
    except Exception as e:
        logger.error(f"Error downloading media: {e}")
        return None, None, None

# =========================
# START COMMAND HANDLERS
# =========================

async def start_facebook(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Hello! Send me a public Facebook video URL, and I'll download it for you.")

async def start_instagram(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Hi! Send me an Instagram post URL (image/video) and I will download it for you.")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Call both original messages so behavior is preserved
    await start_facebook(update, context)
    await start_instagram(update, context)

# =========================
# UNIFIED MESSAGE HANDLER
# =========================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.text:
        return

    user_message = update.message.text.strip()
    chat_id = update.message.chat_id
    message_id = update.message.message_id
    username = update.message.from_user.username or update.message.from_user.first_name

    # 1) FACEBOOK LOGIC
    if is_facebook_video(user_message):
        processing_msg = await update.message.reply_text("<code>Trying to download...</code>", parse_mode="HTML")

        output_path = f"/tmp/{update.message.chat_id}_video.mp4"

        # Extract direct video URL
        direct_url = get_facebook_video_url(user_message)

        if not direct_url:
            await processing_msg.edit_text("❌ Failed to get the direct video link.")
            return

        # Check video size before downloading
        try:
            headers = requests.head(direct_url, allow_redirects=True).headers
            file_size = int(headers.get("content-length", 0)) / (1024 * 1024)  # Convert bytes to MB
        except Exception as e:
            logger.error(f"Failed to get file size: {e}")
            file_size = 0  # Assume it's small if we can't check

        if file_size > 50:  # If larger than 50MB, send direct link
            caption_text = (
                f"✨ *Your media is ready\\!* ✨\n\n"
                f"🆔 *User:* `{escape_markdown_v2_fb(update.message.from_user.first_name)}`\n"
                f"🎥 *Direct Download Link:* [Click here]({escape_markdown_v2_fb(direct_url)})\n"
                f"⚠️ *Your video is too large to be sent on Telegram\\!* 🚀\n"
                f"📥 *Processed with ❤️*"
            )

            # Send a new message with the CDN link
            await update.message.reply_text(caption_text, parse_mode="MarkdownV2")

            # Delete the user's original message and processing message
            await context.bot.delete_message(chat_id=update.message.chat_id, message_id=processing_msg.message_id)
            await context.bot.delete_message(chat_id=update.message.chat_id, message_id=update.message.message_id)

            return

        video_path = download_video(direct_url, output_path)

        if video_path:
            try:
                caption_text = (
                    f"✨ *Your media is ready\\!* ✨\n\n"
                    f"🆔 *User:* `{escape_markdown_v2_fb(update.message.from_user.first_name)}`\n"
                    f"🎥 *Link:* [Click here]({escape_markdown_v2_fb(user_message)})\n"
                    f"📥 *Processed with ❤️*"
                )

                with open(video_path, "rb") as video:
                    await update.message.reply_video(
                        video=video,
                        caption=caption_text,
                        parse_mode="MarkdownV2",
                        reply_to_message_id=update.message.message_id
                    )

                # Delete user message and processing message after sending video
                await context.bot.delete_message(chat_id=update.message.chat_id, message_id=processing_msg.message_id)
                await context.bot.delete_message(chat_id=update.message.chat_id, message_id=update.message.message_id)

            except Exception as e:
                logger.error(f"Error sending video: {e}")
                await update.message.reply_text(
                    "⚠️ Error sending the video.",
                    reply_to_message_id=update.message.message_id
                )
            finally:
                os.remove(video_path)
        else:
            await processing_msg.edit_text(
                "❌ Failed to download the video. Make sure it's public and try again."
            )

        return

    # 2) INSTAGRAM LOGIC
    if "instagram.com" in user_message and "https://" in user_message:
        downloading_msg = await update.message.reply_text("<code>Trying to download...</code>", parse_mode="HTML")

        try:
            media_filename, media_type, media_id = download_media(user_message)

            if not media_filename:
                raise ValueError("Failed to download the media.")

            # Construct the caption
            caption_text = (
                f"✨ *Your media is ready\\!* ✨\n\n"
                f"🆔 *User:* `{escape_markdown_v2_insta(username)}`\n"
                f"🎥 *Link:* [Click here]({escape_markdown_v2_insta(user_message)})\n"
                f"📥 *Processed with ❤️*"
            )

            try:
                with open(media_filename, "rb") as media_file:
                    if media_type in ["mp4", "webm"]:  # Video formats
                        await context.bot.send_video(
                            chat_id=chat_id,
                            video=media_file,
                            caption=caption_text,
                            parse_mode="MarkdownV2",
                            reply_to_message_id=message_id,
                        )
                    else:  # Assume it's an image
                        await context.bot.send_photo(
                            chat_id=chat_id,
                            photo=media_file,
                            caption=caption_text,
                            parse_mode="MarkdownV2",
                            reply_to_message_id=message_id,
                        )

                    # Delete the "Trying to download..." message after sending media
                    await context.bot.delete_message(chat_id=chat_id, message_id=downloading_msg.message_id)
                    await context.bot.delete_message(chat_id=chat_id, message_id=message_id)

            finally:
                # Clean up the file after sending it
                if os.path.exists(media_filename):
                    os.remove(media_filename)
                    logger.info(f"Successfully deleted {media_type} file: {media_filename}")

        except Exception as e:
            logger.error(f"Error: {e}")
            await context.bot.send_message(
                chat_id=chat_id,
                text="❌ Sorry, I couldn't download this media. Please check if the URL is correct or try again later.",
                reply_to_message_id=message_id,
            )
            # Delete the "Trying to download..." message if there's an error
            await context.bot.delete_message(chat_id=chat_id, message_id=downloading_msg.message_id)

        return

    if update.message.chat.type == "private":
        await update.message.reply_text("Please send a valid Instagram post URL (image/video).")

# =========================
# MAIN ENTRY POINT
# =========================

def main():
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # /start handler (combined)
    application.add_handler(CommandHandler("start", start))

    # Single unified text handler (like original IG bot: filters.TEXT & ~filters.COMMAND)
    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_message
        )
    )

    application.run_polling()

if __name__ == "__main__":
    main()
