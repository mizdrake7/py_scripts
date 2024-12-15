from pyrogram import Client, filters, enums
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from pyrogram.types import Message

# API credentials
api_id = "YOUR_API_ID_HERE"
api_hash = "YOUR_API_HASH_HERE"
bot_token = 'YOUR_BOT_TOKEN_HERE'

app = Client("proxycheckerbot", api_id=api_id, api_hash=api_hash, bot_token=bot_token)

# Function to check proxy status
def check_proxy(proxy):
    try:
        # Validate the proxy format: ip:port:username:password
        parts = proxy.strip().split(':')
        if len(parts) != 4:
            return f"**[🔴 DEAD] `{proxy.strip()}`**"  # Invalid proxy format
        
        ip, port, username, password = parts

        proxy_dict = {
            'http': f'http://{username}:{password}@{ip}:{port}',
            'https': f'http://{username}:{password}@{ip}:{port}'
        }

        test_urls = [
            'http://www.google.com',
            'http://www.example.com'
        ]

        # Try multiple test URLs to check the proxy
        for url in test_urls:
            try:
                response = requests.get(url, proxies=proxy_dict, timeout=10)
                if response.status_code == 200:
                    return f"**[🟢 LIVE] `{proxy.strip()}`**"
            except requests.RequestException:
                continue  # Try the next URL or consider it as dead

    except Exception:
        return f"**[🔴 DEAD] `{proxy.strip()}`**"
    
    return f"**[🔴 DEAD] `{proxy.strip()}`**"

# Handle the /prxy command and accept proxy inputs directly
@app.on_message(filters.command("prxy"))
async def handle_prxy(client, message: Message):
    if len(message.command) > 1:
        # Check if proxies are provided directly after the command
        proxies_input = message.text.split(maxsplit=1)[1]  # Take everything after the command
        proxies = [proxy.strip() for proxy in proxies_input.splitlines() if proxy.strip()]  # Handle each proxy on a new line

        if proxies:
            processing_message = await message.reply_text("🔍 Processing proxies...", reply_to_message_id=message.id)
            
            results = []
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = {executor.submit(check_proxy, proxy): proxy for proxy in proxies}
                for future in as_completed(futures):
                    result = future.result()
                    results.append(result)

            live_proxies = [result for result in results if result.startswith("**[🟢 LIVE]")]
            dead_proxies = [result for result in results if result.startswith("**[🔴 DEAD]")]

            output = f"**Proxy Check Complete**\n\n"
            output += f"**Total Proxies:** {len(proxies)}\n"
            output += f"**Live Proxies:** {len(live_proxies)}\n"
            output += f"**Dead Proxies:** {len(dead_proxies)}\n\n"

            if live_proxies:
                output += "**Live Proxies:**\n" + "\n".join(live_proxies) + "\n"
            if dead_proxies:
                output += "**Dead Proxies:**\n" + "\n".join(dead_proxies)

            await processing_message.edit_text(output, parse_mode=enums.ParseMode.MARKDOWN)
        else:
            await message.reply_text(
                "⚠️ Please provide proxies in the format `ip:port:username:password`. You can also send a proxy list text file.",
                reply_to_message_id=message.id,
                parse_mode=enums.ParseMode.MARKDOWN
            )
    else:
        # If no proxies are provided after the command, prompt the user to provide them directly
        await message.reply_text(
            "⚠️ Please provide proxies in the format `ip:port:username:password`. You can also send a proxy list text file.",
            reply_to_message_id=message.id,
            parse_mode=enums.ParseMode.MARKDOWN
        )

# Handle file input for proxies
@app.on_message(filters.document & filters.private)
async def handle_file_input(client, message: Message):
    if message.document.mime_type == "text/plain":
        # Download the file using client.download_media
        file_path = await client.download_media(message.document)
        
        with open(file_path, 'r') as file:
            proxies_input = file.read().strip()

        proxies = [proxy.strip() for proxy in proxies_input.splitlines() if proxy.strip()]

        if proxies:
            processing_message = await message.reply_text("🔍 Processing proxies...", reply_to_message_id=message.id)

            results = []
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = {executor.submit(check_proxy, proxy): proxy for proxy in proxies}
                for future in as_completed(futures):
                    result = future.result()
                    results.append(result)

            live_proxies = [result for result in results if result.startswith("**[🟢 LIVE]")]
            dead_proxies = [result for result in results if result.startswith("**[🔴 DEAD]")]

            output = f"**Proxy Check Complete**\n\n"
            output += f"**Total Proxies:** {len(proxies)}\n"
            output += f"**Live Proxies:** {len(live_proxies)}\n"
            output += f"**Dead Proxies:** {len(dead_proxies)}\n\n"

            if live_proxies:
                output += "**Live Proxies:**\n" + "\n".join(live_proxies) + "\n"
            if dead_proxies:
                output += "**Dead Proxies:**\n" + "\n".join(dead_proxies)

            await processing_message.edit_text(output, parse_mode=enums.ParseMode.MARKDOWN)
        else:
            await message.reply_text("⚠️ No valid proxies found in the file. Please check your file format.")

# Handle text input as well
@app.on_message(filters.private)
async def handle_text_input(client, message: Message):
    if message.text and not message.document:
        proxies_input = message.text.strip()

        if proxies_input:
            proxies = [proxy.strip() for proxy in proxies_input.splitlines() if proxy.strip()]

            if proxies:
                processing_message = await message.reply_text("🔍 Processing proxies...", reply_to_message_id=message.id)

                results = []
                with ThreadPoolExecutor(max_workers=10) as executor:
                    futures = {executor.submit(check_proxy, proxy): proxy for proxy in proxies}
                    for future in as_completed(futures):
                        result = future.result()
                        results.append(result)

                live_proxies = [result for result in results if result.startswith("**[🟢 LIVE]")]
                dead_proxies = [result for result in results if result.startswith("**[🔴 DEAD]")]

                output = f"**Proxy Check Complete**\n\n"
                output += f"**Total Proxies:** {len(proxies)}\n"
                output += f"**Live Proxies:** {len(live_proxies)}\n"
                output += f"**Dead Proxies:** {len(dead_proxies)}\n\n"

                if live_proxies:
                    output += "**Live Proxies:**\n" + "\n".join(live_proxies) + "\n"
                if dead_proxies:
                    output += "**Dead Proxies:**\n" + "\n".join(dead_proxies)

                await processing_message.edit_text(output, parse_mode=enums.ParseMode.MARKDOWN)
            else:
                await message.reply_text(
                    "⚠️ Please provide proxies in the format `ip:port:username:password`. You can also send a proxy list text file.",
                    reply_to_message_id=message.id,
                    parse_mode=enums.ParseMode.MARKDOWN
                )
        else:
            await message.reply_text(
                "⚠️ Please provide proxies in the format `ip:port:username:password`. You can also send a proxy list text file.",
                reply_to_message_id=message.id,
                parse_mode=enums.ParseMode.MARKDOWN
            )

print("Bot is running...")
app.run()
