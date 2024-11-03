from pyrogram import Client, filters, enums
import requests
from bs4 import BeautifulSoup
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

api_id = "YOUR_API_ID_HERE"
api_hash = "YOUR_API_HASH_HERE"
bot_token = 'YOUR_BOT_TOKEN_HERE'

app = Client("ipcheckbot", api_id=api_id, api_hash=api_hash, bot_token=bot_token)

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
Country: <code>{escape_html(location_info['Country'])}</code>
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
    """
    return message

@app.on_message(filters.command("ip"))
async def handle_ip(client, message):
    input_text = message.text.split(maxsplit=1)
    if len(input_text) < 2:
        await message.reply_text("⚠️ Please provide at least one IP in the format: `/ip <ip1>, <ip2>, ...`", parse_mode=enums.ParseMode.HTML)
        return
    
    ip_input = input_text[1]
    ip_list = [ip.strip() for ip in ip_input.replace(',', ' ').split() if ip.strip()]

    if not ip_list:
        await message.reply_text("⚠️ No valid IPs provided.", parse_mode=enums.ParseMode.HTML)
        return

    processing_message = await message.reply_text("🔍 Processing IP details...", reply_to_message_id=message.id)
    results = ""

    for ip in ip_list:
        ip_details = await fetch_ip_details(ip)
        results += ip_details + "\n\n"

    await processing_message.edit_text(results.strip(), parse_mode=enums.ParseMode.HTML)

print("Bot is running...")
app.run()
