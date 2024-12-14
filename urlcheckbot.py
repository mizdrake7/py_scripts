import requests
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pyrogram import Client, filters, enums
from urllib.parse import urlparse
import re

# API credentials
api_id = "YOUR_API_ID_HERE"
api_hash = "YOUR_API_HASH_HERE"
bot_token = 'YOUR_BOT_TOKEN_HERE'
session_name = f"websitecheckbot_{bot_token.split(':')[0]}"

app = Client(
    session_name,
    api_id=api_id,
    api_hash=api_hash,
    bot_token=bot_token
)

pending_users = {}

def is_valid_url(url):
    parsed = urlparse(url)
    return bool(parsed.netloc) and bool(parsed.scheme)

def country_name_to_emoji(country_name):
    country_flags = {
        "United States of America": "🇺🇸",
        "Netherlands": "🇳🇱",
        "China": "🇨🇳",
        "Italy": "🇮🇹",
        "Germany": "🇩🇪",
        "India": "🇮🇳",
        "United Kingdom": "🇬🇧",
        "France": "🇫🇷",
        "Canada": "🇨🇦",
        "Australia": "🇦🇺",
        "Brazil": "🇧🇷",
        "Russia": "🇷🇺",
        "Japan": "🇯🇵",
        "South Korea": "🇰🇷",
        "Mexico": "🇲🇽",
        "Argentina": "🇦🇷",
        "South Africa": "🇿🇦",
        "Egypt": "🇪🇬",
        "Turkey": "🇹🇷",
        "Spain": "🇪🇸",
        "Poland": "🇵🇱",
        "Sweden": "🇸🇪",
        "Norway": "🇳🇴",
        "Denmark": "🇩🇰",
        "Finland": "🇫🇮",
        "Belgium": "🇧🇪",
        "Switzerland": "🇨🇭",
        "Austria": "🇦🇹",
        "Luxembourg": "🇱🇺",
        "Czech Republic": "🇨🇿",
        "Slovakia": "🇸🇰",
        "Portugal": "🇵🇹",
        "Greece": "🇬🇷",
        "Ireland": "🇮🇪",
        "Israel": "🇮🇱",
        "Saudi Arabia": "🇸🇦",
        "United Arab Emirates": "🇦🇪",
        "Qatar": "🇶🇦",
        "Kuwait": "🇰🇼",
        "Bahrain": "🇧🇭",
        "Oman": "🇴🇲",
        "Jordan": "🇯🇴",
        "Lebanon": "🇱🇧",
        "Vietnam": "🇻🇳",
        "Thailand": "🇹🇭",
        "Malaysia": "🇲🇾",
        "Singapore": "🇸🇬",
        "Indonesia": "🇮🇩",
        "Philippines": "🇵🇭",
        "Myanmar": "🇲🇲",
        "Laos": "🇱🇸",
        "Cambodia": "🇰🇭",
        "Nepal": "🇳🇵",
        "Sri Lanka": "🇱🇰",
        "Bangladesh": "🇧🇩",
        "Pakistan": "🇵🇰",
        "Afghanistan": "🇦🇫",
        "Bangladesh": "🇧🇩",
        "Mongolia": "🇲🇳",
        "Kazakhstan": "🇰🇿",
        "Uzbekistan": "🇺🇿",
        "Turkmenistan": "🇹🇲",
        "Kyrgyzstan": "🇰🇬",
        "Tajikistan": "🇹🇯",
        "Armenia": "🇦🇲",
        "Georgia": "🇬🇪",
        "Algeria": "🇩🇿",
        "Morocco": "🇲🇦",
        "Tunisia": "🇹🇳",
        "Libya": "🇱🇾",
        "Mauritius": "🇲🇺",
        "Malawi": "🇲🇼",
        "Zambia": "🇿🇲",
        "Zimbabwe": "🇿🇼",
        "Botswana": "🇧🇼",
        "Namibia": "🇳🇦",
        "Lesotho": "🇱🇸",
        "Eswatini": "🇸🇿",
        "Seychelles": "🇸🇨",
        "Madagascar": "🇲🇬",
        "Comoros": "🇰🇲",
        "Djibouti": "🇩🇯",
        "Ethiopia": "🇪🇹",
        "Kenya": "🇰🇪",
        "Uganda": "🇺🇬",
        "Tanzania": "🇹🇿",
        "Rwanda": "🇷🇼",
        "Burundi": "🇧🇮",
        "Somalia": "🇸🇴",
    }
    return country_flags.get(country_name, "N/A")

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

    isp_name = ip_info_first_answer.get("asname", "N/A")

    # Location details
    location_city = ip_info_first_answer.get("city", "N/A")
    location_region = ip_info_first_answer.get("regionName", "N/A")
    location_country = ip_info_first_answer.get("country", "N/A")

    if location_city == "N/A" and location_region == "N/A" and location_country == "N/A":
        location_output = "N/A"
    else:
        location_output = f"{location_city}, {location_region}, {location_country} {country_name_to_emoji(location_country)}"

    platform_keywords = ['lit', 'gin', 'react', 'angular', 'django', 'flask', 'vue', 'node']
    try:
        platforms = [keyword for keyword in platform_keywords if keyword in page_text.lower()]
        platform_info = ', '.join(platforms) if platforms else 'N/A'
    except Exception as e:
        platform_info = 'N/A'
        print(f"Error detecting platforms for {url}: {e}")

    # Output results
    output = f"""
<b>🌐 Website Information 🌐</b>
🔗 Site URL: <code>{url}</code>
🔎 HTTP Status: <code>{http_status} {'OK' if http_status == 200 else 'Error'}</code>
💳 Payment Gateway: <code>{', '.join(payment_gateways) if payment_gateways else 'None'}</code>
🔒 Captcha: <code>{'Captcha Detected ❌' if captcha_detected else 'No Captcha Detected ✅'}</code>
☁️ Cloudflare: <code>{'Yes ❌' if cloudflare_detected else 'No ✅'}</code>
🔍 GraphQL: <code>{'Yes' if 'graphql' in page_text.lower() else 'No'}</code>
🔧 Platform: <code>{platform_info}</code>
🌍 Location: <code>{location_output}</code>
🖧 IP Address: <code>{ip_info_first_answer.get("query", "N/A")}</code>
📡 ISP: <code>{isp_name}</code>
"""
    return output.strip()

@app.on_message(filters.command("url"))
async def handle_url(client, message):
    user_id = message.from_user.id
    if len(message.command) == 1:  # User called "/url" with no URLs
        pending_users[user_id] = True
        await message.reply_text("\ud83d\udd0d ⚠️ Please provide atleast one URL.", reply_to_message_id=message.id)
    else:
        urls = [url.strip() for url in re.split(r'[\s,]+', message.text.split(' ', 1)[1]) if url.strip()]

        valid_urls = []
        invalid_urls = []

        for url in urls:
            if not is_valid_url(url):
                url = f"https://{url}"
            if is_valid_url(url):
                valid_urls.append(url)
            else:
                invalid_urls.append(url)

        if invalid_urls:
            await message.reply_text(f"\u26a0\ufe0f The following URLs are invalid: {', '.join(invalid_urls)}", parse_mode=enums.ParseMode.HTML)

        if not valid_urls:
            await message.reply_text("\u26a0\ufe0f No valid URLs provided.", parse_mode=enums.ParseMode.HTML)
            return

        processing_message = await message.reply_text("\ud83d\udd0d Processing URLs...", reply_to_message_id=message.id)

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(check_website_info, url): url for url in valid_urls}
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

@app.on_message(filters.text)
async def handle_user_input(client, message):
    user_id = message.from_user.id
    if user_id in pending_users:
        pending_users.pop(user_id)  # Remove user from pending list after they reply with URLs
        urls = [url.strip() for url in re.split(r'[\s,]+', message.text) if url.strip()]
        
        valid_urls = []
        invalid_urls = []

        for url in urls:
            if not is_valid_url(url):
                url = f"https://{url}"
            if is_valid_url(url):
                valid_urls.append(url)
            else:
                invalid_urls.append(url)

        if invalid_urls:
            await message.reply_text(f"\u26a0\ufe0f The following URLs are invalid: {', '.join(invalid_urls)}", parse_mode=enums.ParseMode.HTML)

        if not valid_urls:
            await message.reply_text("\u26a0\ufe0f No valid URLs provided.", parse_mode=enums.ParseMode.HTML)
            return

        processing_message = await message.reply_text("\ud83d\udd0d Processing URLs...", reply_to_message_id=message.id)

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(check_website_info, url): url for url in valid_urls}
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

# Start the bot
print("Bot is running...")
app.run()
