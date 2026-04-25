import logging
import os
import subprocess
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, CallbackContext
from yt_dlp import YoutubeDL

# Logging
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

def escape_markdown_v2(text):
    if not text: return ""
    return "".join(f"\\{c}" if c in r"\_*[]()~`>#+-=|{}.!'" else c for c in str(text))

def is_shorts(url):
    return "youtube.com/shorts/" in url or "shorts" in url.lower()

def generate_thumbnail(video_path, thumb_path):
    try:
        subprocess.run([
            'ffmpeg', '-i', video_path, '-ss', '00:00:02', 
            '-vframes', '1', thumb_path, '-y'
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return thumb_path
    except Exception as e:
        logger.warning(f"Thumbnail generation failed: {e}")
        return None

async def start(update: Update, context: CallbackContext):
    await update.message.reply_text("Hi! Send me any YouTube link and I will download it for you.")

def get_video_info(url):
    ydl_opts = {
        "quiet": True, 
        "no_warnings": True, 
        "cookiefile": "youtube_cookies.txt", 
        "noplaylist": True, 
        "check_formats": False,
        "extractor_args": {'youtube': {'player_client': ['web', 'android']}}
    }
    with YoutubeDL(ydl_opts) as ydl:
        return ydl.extract_info(url, download=False)

async def handle_message(update: Update, context: CallbackContext):
    url = update.message.text.strip()
    chat_id = update.message.chat_id
    user_msg_id = update.message.message_id
    
    if ("youtube.com" in url or "youtu.be" in url) and "http" in url:
        status_msg = await update.message.reply_text("<code>🔍 Analyzing...</code>", parse_mode="HTML")
        try:
            info = get_video_info(url)
            title = info.get("title", "YouTube Video")
            
            context.user_data['current_url'] = url
            context.user_data['user_msg_id'] = user_msg_id

            if is_shorts(url):
                await status_msg.edit_text("⚡ <b>Shorts detected!</b>", parse_mode="HTML")
                await download_and_send(update, context, url, "bestvideo+bestaudio/best", status_msg)
            else:
                keyboard = [
                    [InlineKeyboardButton("📁 360p", callback_data="dl_360"), InlineKeyboardButton("🎬 720p", callback_data="dl_720")],
                    [InlineKeyboardButton("🌟 Best Quality", callback_data="dl_best")]
                ]
                await status_msg.edit_text(f"🎬 <b>{title}</b>\n\nSelect Quality:", 
                                         reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
        except Exception as e:
            logger.error(f"Metadata Error: {e}")
            await status_msg.edit_text("⚠️ Metadata failed. Trying direct download...")
            await download_and_send(update, context, url, "best", status_msg)

async def button_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    url = context.user_data.get('current_url')
    if not url: return await query.edit_message_text("❌ Session expired.")

    format_map = {
        "dl_360": "best[height<=360]/best", 
        "dl_720": "best[height<=720]/best", 
        "dl_best": "bestvideo+bestaudio/best"
    }
    fmt = format_map.get(query.data, "best")
    await query.edit_message_text("<code>📥 Downloading...</code>", parse_mode="HTML")
    await download_and_send(query, context, url, fmt, query.message)

async def download_and_send(update_or_query, context, url, fmt_key, status_msg):
    chat_id = status_msg.chat_id
    
    # FIXED: Correct way to get effective_user from the Update object
    user = None
    if isinstance(update_or_query, Update):
        user = update_or_query.effective_user
    else:
        # If update_or_query is actually a Message object (from button callback)
        user = context.user_data.get('user_obj') # Fallback if needed, but effective_user is best

    # Ultimate fallback for user identification
    if not user:
        user = status_msg.chat.first_name # Using chat info as last resort
        username = user
    else:
        username = user.username or user.first_name

    file_path = f"video_{chat_id}.mp4"
    thumb_path = f"thumb_{chat_id}.jpg"
    
    formats_to_try = [fmt_key, "bestvideo+bestaudio/best", "best"]

    for current_fmt in formats_to_try:
        ydl_opts = {
            "format": current_fmt, 
            "outtmpl": file_path, 
            "merge_output_format": "mp4",
            "cookiefile": "youtube_cookies.txt", 
            "quiet": True,
            "no_warnings": True,
            "extractor_args": {'youtube': {'player_client': ['web', 'android']}},
        }

        try:
            with YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
                info = ydl.extract_info(url, download=False)
                title = info.get("title", "YouTube Video")
            break 
        except Exception:
            if os.path.exists(file_path): os.remove(file_path)
            continue
    else:
        await context.bot.send_message(chat_id=chat_id, text="❌ Download failed.")
        return

    # Check 50MB Limit
    file_size = os.path.getsize(file_path)
    if file_size > 50 * 1024 * 1024:
        await context.bot.send_message(chat_id=chat_id, text=f"❌ Too large ({file_size/1024/1024:.1f}MB). Choose 360p.")
        if os.path.exists(file_path): os.remove(file_path)
        return

    try:
        thumb = generate_thumbnail(file_path, thumb_path)
        caption = (f"✨ *Your media is ready\\!* ✨\n\n"
                   f"🆔 *User:* `{escape_markdown_v2(username)}`\n"
                   f"🎬 *Title:* {escape_markdown_v2(title)}\n"
                   f"📥 *Processed with ❤️*")

        with open(file_path, "rb") as video:
            v_thumb = open(thumb, 'rb') if thumb and os.path.exists(thumb) else None
            await context.bot.send_video(
                chat_id=chat_id, video=video, caption=caption, 
                thumbnail=v_thumb, supports_streaming=True, parse_mode="MarkdownV2",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔗 Open Video", url=url)]])
            )
            
        await status_msg.delete()
        user_msg_id = context.user_data.get('user_msg_id')
        if user_msg_id:
            try:
                await context.bot.delete_message(chat_id=chat_id, message_id=user_msg_id)
            except: pass
        
    except Exception as e:
        logger.error(f"Send error: {e}")
        await context.bot.send_message(chat_id=chat_id, text="❌ Error sending to Telegram.")
    finally:
        for p in [file_path, thumb_path]:
            if os.path.exists(p): os.remove(p)

if __name__ == "__main__":
    TOKEN = "YOUR_NEW_BOT_TOKEN" 
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.run_polling()
