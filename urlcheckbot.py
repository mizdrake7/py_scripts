import requests
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
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
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url

    try:
        response = requests.get(url, timeout=10)
        http_status = response.status_code
    except requests.exceptions.Timeout:
        return f"Error: Timeout while trying to connect to {url}"
    except requests.exceptions.RequestException as e:
        return f"Error fetching URL: {e}"

    try:
        page_text = response.text
    except Exception as e:
        return f"Error reading content from {url}: {e}"

    payment_gateways_list = [
        "Adyen", "Airwalletx", "Authorize", "Bluesnap", "Braintree", "Checkout",
        "Computop", "Endurance", "Fansly", "Mercadopago", "Ncrsecurepay", "Nordvpn",
        "Paddle", "Patreon", "Pay360", "Payzen", "Processout", "Recurly",
        "Securepay", "Squareup", "Stripe", "Tebex", "Xendit", "Xsolla"
    ]

    try:
        payment_gateways = [gateway for gateway in payment_gateways_list if gateway.lower() in page_text.lower()]
    except Exception as e:
        payment_gateways = []
        print(f"Error searching for payment gateways on {url}: {e}")

    captcha_detected = "Captcha" in page_text
    cloudflare_detected = "Cloudflare" in page_text

    api_method = "https://www.nslookup.io/api/v1/records"
    payload = {
        'dnsServer': 'cloudflare',
        'domain': url.replace('https://', '').replace('http://', '')
    }
    try:
        ip_response = requests.post(api_method, json=payload, timeout=10)
        ip_info = ip_response.json()

        if "a" in ip_info.get("records", {}) and "response" in ip_info["records"]["a"]:
            ip_info_first_answer = ip_info["records"]["a"]["response"]["answer"][0].get("ipInfo", {})
        else:
            return f"Error: No 'a' record or response in IP info for {url}"

    except requests.exceptions.Timeout:
        return f"Error: Timeout while trying to retrieve IP info for {url}"
    except Exception as e:
        return f"Error fetching IP info: {e}"

    country_code = ip_info_first_answer.get("countryCode", "N/A")
    country_emoji = country_code_to_emoji(country_code)
    isp_name = ip_info_first_answer.get("asname", "N/A")

    platform_keywords = ['lit', 'gin', 'react', 'angular', 'django', 'flask', 'vue', 'node']
    try:
        platforms = [keyword for keyword in platform_keywords if keyword in page_text.lower()]
        platform_info = ', '.join(platforms) if platforms else 'N/A'
    except Exception as e:
        platform_info = 'N/A'
        print(f"Error detecting platforms for {url}: {e}")

    output = f"🌐 Website Information 🌐\n📍 Site URL: {url}\n🔎 HTTP Status: {http_status} {'OK' if http_status == 200 else 'Error'}\n💳 Payment Gateway: {', '.join(payment_gateways) if payment_gateways else 'None'}\n🔒 Captcha: {'Captcha Detected ❌' if captcha_detected else 'No Captcha Detected ✅'}\n☁️ Cloudflare: {'Yes ❌' if cloudflare_detected else 'No ✅'}\n🔍 GraphQL: {'Yes' if 'graphql' in page_text.lower() else 'No'}\n🔧 Platform: {platform_info}\n🌍 Location: {ip_info_first_answer.get('city', 'N/A')}, {ip_info_first_answer.get('regionName', 'N/A')}, {ip_info_first_answer.get('country', 'N/A')} {country_emoji}\n🌐 IP Address: {ip_info_first_answer.get('query', 'N/A')}\n🔗 ISP: {isp_name}\n"
    
    return output

@app.on_message(filters.command("url"))
async def handle_url(client, message):
    try:
        urls = [url.strip() for url in message.text.replace(',', ' ').split()[1:] if url.strip()]
        if not urls:
            await message.reply_text("⚠️ Please provide URLs in the format: `/url <url1> <url2> ...`", parse_mode=enums.ParseMode.HTML)
            return

        processing_message = await message.reply_text("🔍 Processing URLs...", reply_to_message_id=message.id)

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(check_website_info, url): url for url in urls}
            results = []
            for future in as_completed(futures):
                url = futures[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    results.append(f"Error processing {url}: {e}")
                time.sleep(1)

        await processing_message.edit_text("\n\n".join(results), parse_mode=enums.ParseMode.HTML)

    except Exception as e:
        await message.reply_text(f"⚠️ Error: {e}", parse_mode=enums.ParseMode.HTML)

# Start the bot
print("Bot is running...")
app.run()
