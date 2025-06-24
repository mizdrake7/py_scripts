from pyrogram import Client, filters, enums
import subprocess
import re
import requests
from bs4 import BeautifulSoup
import pycountry
import platform

# API credentials
api_id = ""
api_hash = ""
bot_token = ''

app = Client("ipcheckbot", api_id=api_id, api_hash=api_hash, bot_token=bot_token)

pending_users = {}

def escape_html(text: str) -> str:
    escape_chars = {"&": "&amp;", "<": "&lt;", ">": "&gt;"}
    for char, replacement in escape_chars.items():
        text = text.replace(char, replacement)
    return text

def country_to_flag(country_name: str) -> str:
    try:
        country = pycountry.countries.get(name=country_name)
        if not country:
            country = pycountry.countries.get(common_name=country_name)
        if not country:
            return "🏳"
        country_code = country.alpha_2
        return ''.join(chr(127397 + ord(c)) for c in country_code.upper())
    except Exception:
        return "🏳"

async def check_ping(ip: str) -> str:
    try:
        if platform.system().lower() == "windows":
            cmd = ["ping", "-n", "1", "-w", "5000", ip]
        else:
            cmd = ["ping", "-c", "1", "-W", "5", ip]

        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        match = re.search(r'time[=<]?\s*(\d+\.?\d*)\s*ms', result.stdout)
        return f"{match.group(1)} ms" if match else "Timeout"
    except:
        return "Timeout"

async def fetch_ip_details(ip: str) -> str:
    url = f"https://scamalytics.com/ip/{ip}"
    headers = {"User-Agent": "Mozilla/5.0"}

    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        return f"❌ Error: Could not retrieve data for IP {ip} (Status Code: {response.status_code})"

    soup = BeautifulSoup(response.text, 'html.parser')

    # Fraud score extraction
    fraud_score = "Not available"
    score_box = soup.select_one("div.score")
    if score_box:
        text = score_box.get_text(strip=True)
        match = re.search(r"Fraud Score:\s*(\d+)", text)
        if match:
            fraud_score = match.group(1)
        else:
            print(f"[⚠️ DEBUG] Found score div but couldn't extract number: {text}")
    else:
        print("[⚠️ DEBUG] No <div class='score'> found — layout may have changed.")

   
    risk = "n/a"
    risk_tag = soup.find("div", class_="panel_title")
    if risk_tag:
        risk = risk_tag.text.strip()

   
    details = {}
    for row in soup.select("table tr"):
        th = row.find("th")
        td = row.find("td")
        if th and td:
            key = th.text.strip()
            value = td.text.strip()
            details[key] = value

    location_info = {
        "Country": details.get("Country Name", "n/a"),
        "State": details.get("State / Province", "n/a"),
        "City": details.get("City", "n/a"),
        "Postal Code": details.get("Postal Code", "n/a"),
        "Latitude": details.get("Latitude", "n/a"),
        "Longitude": details.get("Longitude", "n/a"),
    }

    country_name = location_info["Country"]
    country_flag = country_to_flag(country_name)

    message = f"""
<b>📊 IP Fraud Risk Report for {escape_html(ip)}</b>

<b>Score</b>: <code>{escape_html(fraud_score)}</code> | <b>Risk</b>: <code>{escape_html(risk)}</code>

<b>🌐 Operator Details:</b>
Hostname: <code>{escape_html(details.get('Hostname', 'n/a'))}</code>
ASN: <code>{escape_html(details.get('ASN', 'n/a'))}</code>
ISP: <code>{escape_html(details.get('ISP Name', 'n/a'))}</code>
Organization: <code>{escape_html(details.get('Organization Name', 'n/a'))}</code>
Connection Type: <code>{escape_html(details.get('Connection type', 'n/a'))}</code>

<b>🌍 Location:</b>
Country: <code>{escape_html(country_name)} {country_flag}</code>
State: <code>{escape_html(location_info['State'])}</code>
City: <code>{escape_html(location_info['City'])}</code>
Postal Code: <code>{escape_html(location_info['Postal Code'])}</code>
Coordinates: <code>{escape_html(location_info['Latitude'])}, {escape_html(location_info['Longitude'])}</code>

<b>🏢 Datacenter:</b>
Datacenter: <code>{escape_html(details.get('Datacenter', 'n/a'))}</code>

<b>🛑 External Blacklists:</b>
Firehol: <code>{escape_html(details.get('Firehol', 'n/a'))}</code>
IP2ProxyLite: <code>{escape_html(details.get('IP2ProxyLite', 'n/a'))}</code>
IPsum: <code>{escape_html(details.get('IPsum', 'n/a'))}</code>
Spamhaus: <code>{escape_html(details.get('Spamhaus', 'n/a'))}</code>
X4Bnet Spambot: <code>{escape_html(details.get('X4Bnet Spambot', 'n/a'))}</code>

<b>🔐 Proxies:</b>
Anonymizing VPN: <code>{escape_html(details.get('Anonymizing VPN', 'n/a'))}</code>
Tor Exit: <code>{escape_html(details.get('Tor Exit Node', 'n/a'))}</code>
Server: <code>{escape_html(details.get('Server', 'n/a'))}</code>
Public Proxy: <code>{escape_html(details.get('Public Proxy', 'n/a'))}</code>
Web Proxy: <code>{escape_html(details.get('Web Proxy', 'n/a'))}</code>
Search Engine Bot: <code>{escape_html(details.get('Search Engine Robot', 'n/a'))}</code>

<b>⚡ Ping Info:</b>
Ping: {await check_ping(ip)}
"""
    return message

@app.on_message(filters.command("ip"))
async def handle_ip_command(client, message):
    user_id = message.from_user.id if message.from_user else message.chat.id

    if len(message.command) == 1:
        pending_users[user_id] = True
        await message.reply_text("⚠️ Please provide at least one IP address.")
        return

    ip_input = message.text.split(maxsplit=1)[1]
    ip_list = [ip.strip() for ip in ip_input.replace(",", " ").split() if ip.strip()]

    if not ip_list:
        await message.reply_text("⚠️ Invalid IPs provided. Use space or comma to separate them.")
        return

    processing = await message.reply_text("🔍 Processing IP details...", reply_to_message_id=message.id)
    result = ""
    for ip in ip_list:
        result += await fetch_ip_details(ip) + "\n\n"

    await processing.edit_text(result.strip(), parse_mode=enums.ParseMode.HTML)

@app.on_message(filters.text & filters.private)
async def handle_text_response(client, message):
    user_id = message.from_user.id if message.from_user else message.chat.id

    if user_id not in pending_users:
        return

    del pending_users[user_id]
    ip_input = message.text
    ip_list = [ip.strip() for ip in ip_input.replace(",", " ").split() if ip.strip()]

    if not ip_list:
        await message.reply_text("⚠️ Invalid IPs provided. Use space or comma to separate them.")
        return

    processing = await message.reply_text("🔍 Processing IP details...", reply_to_message_id=message.id)
    result = ""
    for ip in ip_list:
        result += await fetch_ip_details(ip) + "\n\n"

    await processing.edit_text(result.strip(), parse_mode=enums.ParseMode.HTML)

print("Bot is running...")
app.run()
