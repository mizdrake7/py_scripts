from pyrogram import Client, filters, enums
import subprocess
import re
import requests
from bs4 import BeautifulSoup

# API credentials
api_id = "YOUR_API_ID_HERE"
api_hash = "YOUR_API_HASH_HERE"
bot_token = 'YOUR_BOT_TOKEN_HERE'

app = Client("ipcheckbot", api_id=api_id, api_hash=api_hash, bot_token=bot_token)

# Dictionary to keep track of pending users
pending_users = {}

def escape_html(text: str) -> str:
    escape_chars = {"&": "&amp;", "<": "&lt;", ">": "&gt;"}
    for char, replacement in escape_chars.items():
        text = text.replace(char, replacement)
    return text

async def fetch_ip_details(ip: str) -> str:
    ipurl = f"https://scamalytics.com/ip/{ip}"
    response = requests.get(ipurl)

    if response.status_code != 200:
        return f"Error: Unable to fetch details for IP {ip}. Please check the IP and try again."

    soup = BeautifulSoup(response.text, 'html.parser')

    score_element = soup.find('div', class_='score')
    fraud_score = score_element.text.split(': ')[1].strip() if score_element else "n/a"

    risk_element = soup.find('div', class_='panel_title')
    risk = risk_element.text.strip() if risk_element else "n/a"

    details = {}
    for row in soup.select('table tr'):
        header = row.find('th')
        if header:
            key = header.text.strip()
            value = row.find('td').text.strip() if row.find('td') else "n/a"
            details[key] = value

    location_info = {
        "Country": details.get("Country Name", "n/a"),
        "State": details.get("State / Province", "n/a"),
        "City": details.get("City", "n/a"),
        "Postal Code": details.get("Postal Code", "n/a"),
        "Latitude": details.get("Latitude", "n/a"),
        "Longitude": details.get("Longitude", "n/a"),
    }

    proxies = {
        "Anonymizing VPN": details.get("Anonymizing VPN", "n/a"),
        "Tor Exit": details.get("Tor Exit Node", "n/a"),
        "Public Proxy": details.get("Public Proxy", "n/a"),
        "Web Proxy": details.get("Web Proxy", "n/a"),
        "Search Engine Bot": details.get("Search Engine Robot", "n/a"),
    }

    message = f"""
<b>📊 IP Fraud Risk Report for {escape_html(ip)}</b>

<b>Score</b>: <code>{escape_html(fraud_score)}</code> | <b>Risk</b>: <code>{escape_html(risk)}</code>

<b>Operator Details:</b>
Hostname: <code>{escape_html(details.get('Hostname', 'n/a'))}</code>
ASN: <code>{escape_html(details.get('ASN', 'n/a'))}</code>
ISP: <code>{escape_html(details.get('ISP Name', 'n/a'))}</code>
Organization: <code>{escape_html(details.get('Organization Name', 'n/a'))}</code>
Connection Type: <code>{escape_html(details.get('Connection type', 'n/a'))}</code>

<b>🌍 Location:</b>
Country: <code>{escape_html(location_info['Country'])} 🇮🇳</code>
State: <code>{escape_html(location_info['State'])}</code>
City: <code>{escape_html(location_info['City'])}</code>
Postal Code: <code>{escape_html(location_info['Postal Code'])}</code>
Coordinates: <code>{escape_html(location_info['Latitude'])}, {escape_html(location_info['Longitude'])}</code>

<b>🔐 Proxies:</b>
Anonymizing VPN: <code>{escape_html(proxies['Anonymizing VPN'])}</code>
Tor Exit: <code>{escape_html(proxies['Tor Exit'])}</code>
Public Proxy: <code>{escape_html(proxies['Public Proxy'])}</code>
Web Proxy: <code>{escape_html(proxies['Web Proxy'])}</code>
Search Engine Bot: <code>{escape_html(proxies['Search Engine Bot'])}</code>

<b>⚡ Ping Info:</b>
Ping: {await check_ping(ip)}
    """
    return message

async def check_ping(ip: str) -> str:
    try:
        response = subprocess.run(
            ["ping", "-c", "1", "-W", "5", ip],  # '-W 5' sets timeout to 5 seconds
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        match = re.search(r'time=(\d+\.\d+) ms', response.stdout)
        if match:
            return f"{match.group(1)} ms"
        else:
            return "Timeout"
    except Exception as e:
        return "Timeout"

@app.on_message(filters.command("ip"))
async def handle_ip(client, message):
    if message.from_user:
        user_id = message.from_user.id
    else:
        user_id = message.chat.id

    if len(message.command) == 1:
        pending_users[user_id] = True
        await message.reply_text("⚠️ Please provide at least one IP address.")
    else:
        ip_input = message.text.split(maxsplit=1)[1]
        ip_list = [ip.strip() for ip in ip_input.replace(',', ' ').split() if ip.strip()]

        if ip_list:
            processing_message = await message.reply_text("🔍 Processing IP details...", reply_to_message_id=message.id)
            results = ""
            for ip in ip_list:
                ip_details = await fetch_ip_details(ip)
                results += ip_details + "\n\n"
            await processing_message.edit_text(results.strip(), parse_mode=enums.ParseMode.HTML)
        else:
            await message.reply_text("⚠️ Invalid IPs provided. IPs separated by spaces or commas.")

@app.on_message(filters.text & filters.private)
async def handle_responses(client, message):
    if message.from_user:
        user_id = message.from_user.id
    else:
        user_id = message.chat.id

    if user_id in pending_users:
        del pending_users[user_id]
        ip_input = message.text
        ip_list = [ip.strip() for ip in ip_input.replace(',', ' ').split() if ip.strip()]

        if ip_list:
            processing_message = await message.reply_text("🔍 Processing IP details...", reply_to_message_id=message.id)
            results = ""
            for ip in ip_list:
                ip_details = await fetch_ip_details(ip)
                results += ip_details + "\n\n"
            await processing_message.edit_text(results.strip(), parse_mode=enums.ParseMode.HTML)
        else:
            await message.reply_text("⚠️ Invalid IPs provided. IPs separated by spaces or commas.")

print("Bot is running...")
app.run()
