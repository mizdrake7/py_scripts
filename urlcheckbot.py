import requests
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pyrogram import Client, filters, enums
from urllib.parse import urlparse
from ping3 import ping
import re
import pycountry
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Telegram bot credentials
api_id = "YOUR_API_ID_HERE"
api_hash = "YOUR_API_HASH_HERE"
bot_token = 'YOUR_BOT_TOKEN_HERE'
session_name = f"websitecheckbot_{bot_token.split(':')[0]}"

app = Client(session_name, api_id=api_id, api_hash=api_hash, bot_token=bot_token)
pending_users = {}

def country_name_to_emoji(country_name):
    try:
        country = pycountry.countries.lookup(country_name)
        iso = country.alpha_2.upper()
        return chr(127397 + ord(iso[0])) + chr(127397 + ord(iso[1]))
    except:
        return "🏳️"

def is_valid_url(url):
    parsed = urlparse(url)
    return bool(parsed.netloc) and bool(parsed.scheme)

def check_website_info(url):
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url

    domain = urlparse(url).netloc

    try:
        latency = ping(domain, timeout=3)
        ping_info = f"{int(latency * 1000)} ms" if latency else "Unreachable"
    except Exception:
        ping_info = "Unreachable"

    try:
        response = requests.get(url, timeout=10)
        http_status = response.status_code
        page_text = response.text
    except requests.exceptions.Timeout:
        return {"error": f"❌ <b>Timeout</b>: The site <code>{url}</code> didn't respond in time.", "url": url}
    except requests.exceptions.RequestException as e:
        return {"error": f"❌ <b>Connection Error</b>: Unable to reach <code>{url}</code>\n<code>{str(e)}</code>", "url": url}
    except Exception as e:
        return {"error": f"❌ <b>Error</b>: Couldn't read the response from <code>{url}</code>", "url": url}

    PAYMENT_GATEWAYS = {
        "paypal": "PayPal", "stripe": "Stripe", "razorpay": "Razorpay", "paytm": "Paytm",
        "ccavenue": "CCAvenue", "cashfree": "Cashfree", "instamojo": "Instamojo",
        "braintree": "Braintree", "adyen": "Adyen", "square": "Square", "xendit": "Xendit",
        "payflow": "Payflow", "authorize.net": "Authorize.net", "recurly": "Recurly",
        "payu": "PayU", "worldpay": "Worldpay", "mollie": "Mollie", "stripe-checkout": "Stripe Checkout",
        "2checkout": "2Checkout", "bluepay": "BluePay", "amazon-pay": "Amazon Pay",
        "apple-pay": "Apple Pay", "google-pay": "Google Pay", "phonepe": "PhonePe",
        "mobikwik": "Mobikwik", "billdesk": "BillDesk", "atom": "Atom", "bhim": "BHIM",
        "upi": "UPI", "neteller": "Neteller", "skrill": "Skrill", "payoneer": "Payoneer",
        "paysera": "Paysera", "sezzle": "Sezzle", "klarna": "Klarna", "afterpay": "Afterpay",
        "zuora": "Zuora", "xsolla": "Xsolla", "airwalletx": "Airwalletx", "authorize": "Authorize",
        "bluesnap": "Bluesnap", "checkout": "Checkout", "computop": "Computop", "endurance": "Endurance",
        "fansly": "Fansly", "mercadopago": "MercadoPago", "ncrsecurepay": "NCR SecurePay",
        "nordvpn": "NordVPN", "paddle": "Paddle", "patreon": "Patreon", "pay360": "Pay360",
        "payzen": "PayZen", "processout": "ProcessOut", "securepay": "SecurePay",
        "squareup": "Squareup", "tebex": "Tebex"
    }

    CMS_SYSTEMS = ["wordpress", "magento", "prestashop", "bigcommerce", "shopify"]
    CAPTCHAS = {
        "recaptcha": "reCAPTCHA", "hcaptcha": "hCAPTCHA",
        "cloudflare.com/turnstile": "Cloudflare Turnstile", "cloudflare": "Cloudflare"
    }

    payment_gateways = [name for key, name in PAYMENT_GATEWAYS.items() if key in page_text.lower()]
    captcha_found = [name for key, name in CAPTCHAS.items() if key in page_text.lower()]
    cms_found = [cms.title() for cms in CMS_SYSTEMS if cms in page_text.lower()]
    cloudflare_detected = "cloudflare" in page_text.lower()
    graphql_used = "Yes" if "graphql" in page_text.lower() else "No"
    platform_keywords = ['lit', 'gin', 'react', 'angular', 'django', 'flask', 'vue', 'node']
    platforms = [keyword for keyword in platform_keywords if keyword in page_text.lower()]

    try:
        domain_only = url.replace("https://", "").replace("http://", "")
        ip_response = requests.post("https://www.nslookup.io/api/v1/records", json={'dnsServer': 'cloudflare', 'domain': domain_only}, timeout=10)
        ip_data = ip_response.json().get("records", {}).get("a", {}).get("response", {}).get("answer", [{}])[0].get("ipInfo", {})
    except Exception as e:
        return {"error": f"❌ <b>DNS Error</b>: Could not resolve IP info for <code>{url}</code>\n<code>{e}</code>", "url": url}

    isp_name = ip_data.get("asname", "N/A")
    ip_query = ip_data.get("query", "N/A")
    city = ip_data.get("city", "N/A")
    region = ip_data.get("regionName", "N/A")
    country = ip_data.get("country", "N/A")
    flag = country_name_to_emoji(country)
    location_output = f"{city}, {region}, {country} {flag}" if country != "N/A" else "N/A"

    return {
        "info": f"""
<b>🌐 Website Information 🌐</b>
🔗 Site URL: <code>{url}</code>
🔍 HTTP Status: <code>{http_status} {'OK' if http_status == 200 else 'Error'}</code>
🧱 CMS: <code>{', '.join(cms_found) if cms_found else 'N/A'}</code>
💳 Payment Gateway: <code>{', '.join(payment_gateways) if payment_gateways else 'None'}</code>
🔐 Captcha: <code>{', '.join(captcha_found) if captcha_found else 'No Captcha Detected ✅'}</code>
☁️ Cloudflare: <code>{'Yes ❌' if cloudflare_detected else 'No ✅'}</code>
🔎 GraphQL: <code>{graphql_used}</code>
🔧 Platform: <code>{', '.join(platforms) if platforms else 'N/A'}</code>
🌍 Location: <code>{location_output}</code>
📧 IP Address: <code>{ip_query}</code>
📡 ISP: <code>{isp_name}</code>
⚡ Ping Info: <code>{ping_info}</code>
""".strip(),
        "url": url
    }

@app.on_message(filters.command("url"))
async def handle_url(client, message):
    user_id = message.from_user.id if message.from_user else message.chat.id

    if len(message.command) == 1:
        pending_users[user_id] = True
        await message.reply_text("🔍 ⚠️ Please provide at least one URL.", reply_to_message_id=message.id)
        return

    raw_input = message.text.split(' ', 1)[1]
    raw_urls = [u.strip() for u in re.split(r'[\s,]+', raw_input) if u.strip()]
    urls = []
    invalid_urls = []

    for u in raw_urls:
        test_url = u if is_valid_url(u) else f"https://{u}"
        if is_valid_url(test_url):
            urls.append(test_url)
        else:
            invalid_urls.append(u)

    if not urls:
        await message.reply_text("⚠️ No valid URLs provided.", parse_mode=enums.ParseMode.HTML)
        return

    if invalid_urls:
        await message.reply_text(f"⚠️ The following URLs are invalid: {', '.join(invalid_urls)}", parse_mode=enums.ParseMode.HTML)

    processing_message = await message.reply_text("🔍 Processing URLs...", reply_to_message_id=message.id)

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(check_website_info, url): url for url in urls}
        results = [future.result() for future in as_completed(futures)]
        time.sleep(1)

    await processing_message.delete()

    for result in results:
        if "error" in result:
            await message.reply_text(result["error"], parse_mode=enums.ParseMode.HTML)
        else:
            screenshot_url = f"https://image.thum.io/get/width/1000/{result['url']}"
            buttons = InlineKeyboardMarkup([[InlineKeyboardButton("🌐 Open Website", url=result["url"])]])
            await client.send_photo(
                chat_id=message.chat.id,
                photo=screenshot_url,
                caption=result["info"],
                parse_mode=enums.ParseMode.HTML,
                reply_markup=buttons
            )

@app.on_message(filters.text)
async def handle_user_input(client, message):
    user_id = message.from_user.id if message.from_user else message.chat.id

    if user_id in pending_users:
        pending_users.pop(user_id)
        raw_urls = [u.strip() for u in re.split(r'[\s,]+', message.text) if u.strip()]
        urls = []
        for u in raw_urls:
            test_url = u if is_valid_url(u) else f"https://{u}"
            if is_valid_url(test_url):
                urls.append(test_url)

        if urls:
            processing_message = await message.reply_text("🔍 Processing URLs...", reply_to_message_id=message.id)
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = {executor.submit(check_website_info, url): url for url in urls}
                results = [future.result() for future in as_completed(futures)]
                time.sleep(1)
            await processing_message.delete()
            for result in results:
                if "error" in result:
                    await message.reply_text(result["error"], parse_mode=enums.ParseMode.HTML)
                else:
                    screenshot_url = f"https://image.thum.io/get/width/1000/{result['url']}"
                    buttons = InlineKeyboardMarkup([[InlineKeyboardButton("Open Website", url=result["url"])]])
                    await client.send_photo(
                        chat_id=message.chat.id,
                        photo=screenshot_url,
                        caption=result["info"],
                        parse_mode=enums.ParseMode.HTML,
                        reply_markup=buttons
                    )

print("Bot is running...")
app.run()
