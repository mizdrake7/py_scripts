import os
import re
import yt_dlp
import spotipy
import logging
from spotipy.oauth2 import SpotifyClientCredentials
from telegram import Update, Message
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext

# 🔹 Your credentials
SPOTIFY_CLIENT_ID = ""
SPOTIFY_CLIENT_SECRET = ""
TELEGRAM_BOT_TOKEN = ""

# 🔹 Initialize Spotify API
sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=SPOTIFY_CLIENT_ID, client_secret=SPOTIFY_CLIENT_SECRET))

# 🔹 Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_song_details(spotify_url):
    """Extract song details (title & artist) from a Spotify track URL."""
    try:
        track_id = spotify_url.split("/")[-1].split("?")[0]
        track = sp.track(track_id)
        artist = track["artists"][0]["name"]
        song_name = track["name"]
        return f"{artist} - {song_name}"
    except Exception as e:
        logger.error(f"Error fetching song details: {e}")
        return None

def search_youtube(query):
    """Search for the song on YouTube and return the video URL."""
    ydl_opts = {"quiet": True, "default_search": "ytsearch", "noplaylist": True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(query, download=False)
        if "entries" in info:
            return info["entries"][0]["webpage_url"]
    return None

def download_song(youtube_url, song_title):
    """Download the YouTube video as an MP3 file."""
    safe_title = re.sub(r'[\\/*?:"<>|]', "_", song_title)  # Remove invalid characters
    output_filename = f"{safe_title}.%(ext)s"
    
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": output_filename,
        "postprocessors": [
            {"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "320"},
            {"key": "FFmpegMetadata"},
            {"key": "EmbedThumbnail"},
        ],
        "merge_output_format": "mp3",
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([youtube_url])

        mp3_file = f"{safe_title}.mp3"
        return mp3_file if os.path.exists(mp3_file) else None
    except Exception as e:
        logger.error(f"Download failed: {e}")
        return None

async def start(update: Update, context: CallbackContext):
    """Handle /start command."""
    await update.message.reply_text("🎵 Send me a **Spotify song link**, and I'll download it for you!")

async def handle_spotify_link(update: Update, context: CallbackContext):
    """Process a valid Spotify track link, search on YouTube, download, and send the MP3."""
    message = update.message.text
    spotify_pattern = r"https://open\.spotify\.com/track/\w+"

    if not re.match(spotify_pattern, message):
        return  # Ignore messages that are not Spotify links

    downloading_msg: Message = await update.message.reply_text("⬇️ Downloading the song...")

    # Extract song details
    song_details = get_song_details(message)
    if not song_details:
        await update.message.reply_text("❌ Could not fetch song details. Please check your link.")
        return

    # Search YouTube
    youtube_url = search_youtube(song_details)
    if not youtube_url:
        await update.message.reply_text("❌ Could not find the song on YouTube.")
        return

    # Download MP3
    mp3_file = download_song(youtube_url, song_details)
    if not mp3_file:
        await update.message.reply_text("❌ Download failed.")
        return

    # Delete the "⬇️ Downloading the song..." message
    await downloading_msg.delete()

    # Send MP3 file to user and delete it afterward
    try:
        with open(mp3_file, "rb") as audio:
            await update.message.reply_audio(audio=audio, title=song_details)
    except Exception as e:
        logger.error(f"Error sending file: {e}")
        await update.message.reply_text("❌ Failed to send the song.")
    finally:
        if os.path.exists(mp3_file):
            os.remove(mp3_file)
            logger.info(f"Deleted file: {mp3_file}")

def main():
    """Start the bot."""
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_spotify_link))

    app.run_polling()

if __name__ == "__main__":
    main()
