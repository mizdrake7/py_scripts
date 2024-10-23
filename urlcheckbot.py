import requests
import time
from concurrent.futures import ThreadPoolExecutor
from pyrogram import Client, filters, enums

# Telegram bot setup
api_id = "YOUR_API_ID_HERE"
api_hash = "YOUR_API_HASH_HERE"
bot_token = 'YOUR_BOT_TOKEN_HERE'
app = Client("websitecheckbot", api_id=api_id, api_hash=api_hash, bot_token=bot_token)

def country_code_to_emoji(country_code):
    if len(country_code) != 2:
        return country_code
    return chr(0x1F1E6 + (ord(country_code.upper()[0]) - ord('A'))) + chr(0x1F1E6 + (ord(country_code.upper()[1]) - ord('A')))

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

    # Captcha detection
    captcha_detected = "Captcha" in response.text

    # Check for Cloudflare
    cloudflare_detected = "Cloudflare" in response.text

    # IP Address and ISP retrieval using nslookup.io
    api_method = "https://www.nslookup.io/api/v1/records"
    payload = {
        'dnsServer': 'cloudflare',
        'domain': url.replace('https://', '').replace('http://', '')
    }
    try:
        ip_response = requests.post(api_method, json=payload)
        ip_info = ip_response.json()

        # Check if 'a' record is present and if 'answer' exists
        if "a" in ip_info.get("records", {}) and "response" in ip_info["records"]["a"]:
            ip_info_first_answer = ip_info["records"]["a"]["response"]["answer"][0].get("ipInfo", {})
        else:
            return f"Error: No 'a' record or response in IP info for {url}"

    except Exception as e:
        return f"Error fetching IP info: {e}"

    country_code = ip_info_first_answer.get("countryCode", "Unknown")
    country_emoji = country_code_to_emoji(country_code)

    # Define a comprehensive list of keywords for platform detection
    platform_keywords = ['lit', 'gin', 'react', 'angular', 'django', 'flask', 'vue', 'node']
    platforms = [keyword for keyword in platform_keywords if keyword in response.text.lower()]
    platform_info = ', '.join(platforms) if platforms else 'Unknown'

    # Output results
    output = f"""
🌐 Website Information 🌐
📍 Site URL: {url}
🔎 HTTP Status: {http_status} {'OK' if http_status == 200 else 'Error'}
💳 Payment Gateway: {', '.join(payment_gateways) if payment_gateways else 'None'}
🔒 Captcha: {'Captcha Detected ❌' if captcha_detected else 'No Captcha Detected ✅'}
☁️ Cloudflare: {'Yes ❌' if cloudflare_detected else 'No ✅'}
🔍 GraphQL: {'Yes' if 'graphql' in response.text.lower() else 'No'}
🔧 Platform: {platform_info}
🌍 Country: {ip_info_first_answer.get("country", "Unknown")} {country_emoji}
🌐 IP Address: {ip_info_first_answer.get("query", "Unknown")}
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
