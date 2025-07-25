import requests, re, socket, json, whois, time
from icmplib import ping as icmp_ping
from datetime import datetime
from urllib.parse import urlparse
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from concurrent.futures import ThreadPoolExecutor, as_completed
import pycountry

api_id = "YOUR_API_ID_HERE"
api_hash = "YOUR_API_HASH_HERE"
bot_token = 'YOUR_BOT_TOKEN_HERE'
session_name = f"websitecheckbot_{bot_token.split(':')[0]}"
app = Client(session_name, api_id=api_id, api_hash=api_hash, bot_token=bot_token)
pending_users = {}

def extract_domain(url):
    parsed_url = urlparse(url)
    return parsed_url.netloc or parsed_url.path

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

def get_ip_and_location(domain):
    try:
        response = requests.get(f"http://nslookup.io/api/ip/{domain}")
        if response.status_code == 200:
            data = response.json()
            ip = data.get("ip", "N/A")
            isp = data.get("isp", "N/A")
            location_parts = [data.get("city", ""), data.get("region", ""), data.get("country", "")]
            location = ", ".join(filter(None, location_parts))
            flag = data.get("flag", "")
            return ip, isp, location, flag
    except:
        pass
    return "N/A", "N/A", "N/A", ""

def get_whois_data(domain):
    try:
        w = whois.whois(domain)
        registrar = w.registrar or "N/A"
        creation = w.creation_date
        expiry = w.expiration_date
        if isinstance(creation, list): creation = creation[0]
        if isinstance(expiry, list): expiry = expiry[0]
        created = creation.strftime('%Y-%m-%d') if isinstance(creation, datetime) else "N/A"
        expires = expiry.strftime('%Y-%m-%d') if isinstance(expiry, datetime) else "N/A"
        return registrar, created, expires
    except:
        return "N/A", "N/A", "N/A"

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

CAPTCHAS = {
    "recaptcha": "reCAPTCHA", "hcaptcha": "hCAPTCHA",
    "cloudflare.com/turnstile": "Cloudflare Turnstile", "cloudflare": "Cloudflare"
}

CMS_SYSTEMS = ["wordpress", "magento", "prestashop", "bigcommerce", "shopify"]
PLATFORMS = ['lit', 'gin', 'react', 'angular', 'django', 'flask', 'vue', 'node', 'next.js']

def check_website_info(url):
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url

    domain = extract_domain(url)

    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        html = response.text
        status_code = response.status_code
    except Exception as e:
        return {"error": f"❌ <b>Error:</b> Could not connect to <code>{url}</code>\n<code>{str(e)}</code>", "url": url}
        
    cms_found = [cms.title() for cms in CMS_SYSTEMS if cms in html.lower()]
    payment_gateways = [name for key, name in PAYMENT_GATEWAYS.items() if key in html.lower()]
    captcha_found = [name for key, name in CAPTCHAS.items() if key in html.lower()]
    graphql_used = "Yes" if "graphql" in html.lower() else "No"
    cloudflare_detected = "cloudflare" in html.lower()
    platforms = [p.title() for p in PLATFORMS if p in html.lower()]
    
    ip, isp, location, flag = get_ip_and_location(domain)
    registrar, created, expires = get_whois_data(domain)
    try:
        ping_res = icmp_ping(domain, count=2, timeout=2)
        avg_ping = f"{int(ping_res.avg_rtt)} ms"
    except:
        avg_ping = "N/A"

    return {
        "info": f"""
<b>🌐 Website Information 🔎</b>
🔗 <b>URL:</b> <code>{url}</code>
📶 <b>Status:</b> <code>{status_code} {'OK' if status_code == 200 else 'Error'}</code>
🧱 <b>CMS:</b> <code>{', '.join(cms_found) if cms_found else 'N/A'}</code>
💳 <b>Payment:</b> <code>{', '.join(payment_gateways) if payment_gateways else 'None'}</code>
🔐 <b>Captcha:</b> <code>{', '.join(captcha_found) if captcha_found else 'No Captcha Detected ✅'}</code>
☁️ <b>Cloudflare:</b> <code>{'Yes ❌' if cloudflare_detected else 'No ✅'}</code>
🔎 <b>GraphQL:</b> <code>{graphql_used}</code>
🔧 <b>Platform:</b> <code>{', '.join(platforms) if platforms else 'N/A'}</code>
🌍 <b>Location:</b> <code>{location} {flag}</code>
#️⃣ <b>IP:</b> <code>{ip}</code>
📡 <b>ISP:</b> <code>{isp}</code>
⚡ <b>Ping:</b> <code>{avg_ping}</code>
🏢 <b>Registrar:</b> <code>{registrar}</code>
📅 <b>Created:</b> <code>{created}</code>
⌛ <b>Expires:</b> <code>{expires}</code>
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
    urls = [f"https://{u}" if not is_valid_url(u) else u for u in raw_urls]

    processing_message = await message.reply_text("🔍 Processing URLs...", reply_to_message_id=message.id)

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(check_website_info, url): url for url in urls}
        results = [f.result() for f in as_completed(futures)]

    await processing_message.delete()

    for result in results:
        if "error" in result:
            await message.reply_text(result["error"], parse_mode=enums.ParseMode.HTML)
        else:
            screenshot_url = f"https://image.thum.io/get/width/1000/{result['url']}"
            await client.send_photo(
                chat_id=message.chat.id,
                photo=screenshot_url,
                caption=result["info"],
                parse_mode=enums.ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🌐 Open Website", url=result["url"])]]),
            )

@app.on_message(filters.text)
async def handle_text(client, message):
    user_id = message.from_user.id if message.from_user else message.chat.id
    if user_id not in pending_users:
        return
    pending_users.pop(user_id)
    urls = [f"https://{u.strip()}" if not u.startswith(('http://', 'https://')) else u.strip() for u in message.text.split()]
    await handle_url(client, message)

print("🚀 Bot is running...")
app.run()
