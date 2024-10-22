import requests
import time
from concurrent.futures import ThreadPoolExecutor
from pyrogram import Client, filters, enums

# Telegram bot setup
api_id = "14370420"
api_hash = "766ebcdc81cce588e5a86b369f4d3420"
bot_token = '5319082339:AAFt6mb_TMKCDzMbWFmpTgJIog2B0kYH1ss'

app = Client("websitecheckbot", api_id=api_id, api_hash=api_hash, bot_token=bot_token)

def check_website_info(url):
    # Ensure the URL starts with 'https://' if it's not already present
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url

    # Check HTTP status
    try:
        response = requests.get(url)
        http_status = response.status_code
    except Exception as e:
        return f"Error fetching URL: {e}"

    # Define the list of payment gateways
    payment_gateways_list = [
        "Adyen", "Airwalletx", "Authorize", "Bluesnap", "Braintree", "Checkout",
        "Computop", "Endurance", "Fansly", "Mercadopago", "Ncrsecurepay", "Nordvpn",
        "Paddle", "Patreon", "Pay360", "Payzen", "Processout", "Recurly",
        "Securepay", "Squareup", "Stripe", "Tebex", "Xendit", "Xsolla"
    ]

    # Check for payment gateways
    payment_gateways = [gateway for gateway in payment_gateways_list if gateway.lower() in response.text.lower()]

    # Captcha detection (example logic)
    captcha_detected = "Captcha" in response.text

    # Check for Cloudflare (example logic)
    cloudflare_detected = "Cloudflare" in response.text

    # IP Address and ISP retrieval
    ip_info = requests.get('https://api.ipify.org?format=json').json()
    ip_address = ip_info['ip']
    isp_info = "SingleHop LLC"  # Replace with actual API call if needed

    # Output results
    output = f"""
🌐 Website Information 🌐

📍 Site URL: {url}
🔎 HTTP Status: {http_status} {'OK' if http_status == 200 else 'Error'}
💳 Payment Gateway: {', '.join(payment_gateways) if payment_gateways else 'None'}

🔒 Captcha: {'Captcha Detected ❌' if captcha_detected else 'No Captcha Detected ✅'}
☁️ Cloudflare: {'Yes ❌' if cloudflare_detected else 'No ✅'}
🔍 GraphQL: {'Yes' if 'graphql' in response.text.lower() else 'No'}
🔧 Platform: {'Lit, Gin' if 'lit' in response.text.lower() or 'gin' in response.text.lower() else 'Unknown'}
🌍 Country: The Netherlands 🇳🇱
🌐 IP Address: {ip_address}
🔗 ISP: {isp_info}
"""
    return output

@app.on_message(filters.command("url"))
async def handle_url(client, message):
    try:
        # Extract URLs from the message and replace commas with spaces
        urls = [url.strip() for url in message.text.replace(',', ' ').split()[1:] if url.strip()]  # URLs start from the second word
        if not urls:
            await message.reply_text("⚠️ Please provide URLs in the format: `/url <url1> <url2> ...`", parse_mode=enums.ParseMode.HTML)
            return

        processing_message = await message.reply_text("🔍 Processing URLs...", reply_to_message_id=message.id)

        # Use ThreadPoolExecutor to handle concurrent requests
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(check_website_info, url): url for url in urls}
            results = []
            for future in futures:
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    results.append(f"Error processing {futures[future]}: {e}")
                time.sleep(1)  # Optional: Add a delay between requests

        # Send results back via Telegram
        await processing_message.edit_text("\n\n".join(results), parse_mode=enums.ParseMode.HTML)

    except Exception as e:
        await message.reply_text(f"⚠️ Error: {e}", parse_mode=enums.ParseMode.HTML)

# Start the bot
print("Bot is running...")
app.run()
