from pyrogram import Client, filters, enums
import requests
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

api_id = "14370420"
api_hash = "766ebcdc81cce420e5a86b3f4f4d3169"
bot_token = '5319082339:AAFTMKC_ciRcDzMbWFmpTgJIog2B0kYH169'

app = Client("ipcheckbot", api_id=api_id, api_hash=api_hash, bot_token=bot_token)

def escape_html(text: str) -> str:
    escape_chars = {"&": "&amp;", "<": "&lt;", ">": "&gt;"}
    for char, replacement in escape_chars.items():
        text = text.replace(char, replacement)
    return text

def find_between(source: str, start: str, end: str) -> str:
    try:
        return (source.split(start))[1].split(end)[0]
    except:
        return "n/a"

async def fetch_ip_details(ip: str) -> str:
    ipurl = f"https://scamalytics.com/ip/{ip}"
    response = requests.get(ipurl)

    if response.status_code != 200:
        return f"Error: Unable to fetch details for IP {ip}. Please check the IP and try again."

    # Extracting details
    score = find_between(response.text, '"score":"', '",')
    risk = find_between(response.text, '"risk":"', '"')

    # Operators
    hostname = find_between(response.text, '''<th>Hostname</th>\n                <td>''', '</td>')
    asn = find_between(response.text, '''<th>ASN</th>\n                <td>''', '</td>')
    isp = find_between(response.text, 'https://scamalytics.com/ip/isp/', '">')
    organization = find_between(response.text, '''<th>Organization Name</th>\n                <td>''', '</td>')
    connection = find_between(response.text, '''<th>Connection type</th>\n                <td>''', '</td>')

    # Location details
    country = find_between(response.text, '''<th>Country Name</th>\n                <td>''', '</td>')
    state = find_between(response.text, '''<th>State / Province</th>\n                <td>''', '</td>')
    city = find_between(response.text, '''<th>City</th>\n                <td>''', '</td>')
    postal = find_between(response.text, '''<th>Postal Code</th>\n                <td>''', '</td>')
    latitude = find_between(response.text, '''<th>Latitude</th>\n                <td>''', '</td>')
    longitude = find_between(response.text, '''<th>Longitude</th>\n                <td>''', '</td>')

    # Proxy details
    vpn = find_between(response.text, '''<th>Anonymizing VPN</th>\n                <td><div class="risk ''', '">')
    tor = find_between(response.text, '''<th>Tor Exit Node</th>\n                <td><div class="risk ''', '">')
    publicproxy = find_between(response.text, '''<th>Public Proxy</th>\n                <td><div class="risk ''', '">')
    webproxy = find_between(response.text, '''<th>Web Proxy</th>\n                <td><div class="risk ''', '">')
    searchenginebot = find_between(response.text, '''<th>Search Engine Robot</th>\n                <td><div class="risk ''', '">')
    domainname = find_between(response.text, '<td colspan="2" class="colspan">', '</td>')

    # Formatting the message, escaping special characters
    message = f"""
<b>📊 IP Fraud Risk Report for {escape_html(ip)}</b>

<b>Score</b>: <code>{escape_html(score)}</code> | <b>Risk</b>: <code>{escape_html(risk)}</code>

<b>Operator Details:</b>
Hostname: <code>{escape_html(hostname)}</code>
ASN: <code>{escape_html(asn)}</code>
ISP: <code>{escape_html(isp)}</code>
Organization: <code>{escape_html(organization)}</code>
Connection Type: <code>{escape_html(connection)}</code>

<b>🌍 Location:</b>
Country: <code>{escape_html(country)}</code>
State: <code>{escape_html(state)}</code>
City: <code>{escape_html(city)}</code>
Postal Code: <code>{escape_html(postal)}</code>
Coordinates: <code>{escape_html(latitude)}, {escape_html(longitude)}</code>

<b>🔐 Proxies:</b>
Anonymizing VPN: <code>{escape_html(vpn)}</code>
Tor Exit: <code>{escape_html(tor)}</code>
Public Proxy: <code>{escape_html(publicproxy)}</code>
Web Proxy: <code>{escape_html(webproxy)}</code>
Search Engine Bot: <code>{escape_html(searchenginebot)}</code>

<b>🌐 Domain Names:</b> <code>{escape_html(domainname)}</code>
    """
    return message

@app.on_message(filters.command("ip"))
async def handle_ip(client, message):
    try:
        # Get all the text after the command
        input_text = message.text.split(maxsplit=1)  # Split only once
        if len(input_text) < 2:
            await message.reply_text("⚠️ Please provide at least one IP in the format: `/ip <ip1>, <ip2>, ...`", parse_mode=enums.ParseMode.HTML)
            return
        
        ip_input = input_text[1]  # This contains the IPs
        # Split by comma or space and strip whitespace
        ip_list = [ip.strip() for ip in ip_input.replace(',', ' ').split() if ip.strip()]

        if not ip_list:
            await message.reply_text("⚠️ No valid IPs provided. Please ensure your input is correct.", parse_mode=enums.ParseMode.HTML)
            return

        processing_message = await message.reply_text("🔍 Processing IP details...", reply_to_message_id=message.id)

        # Initialize an empty message to accumulate results
        results = ""

        for ip in ip_list:
            ip = ip.strip()  # Clean up spaces
            # Log the current IP being processed
            print(f"Processing IP: {ip}")
            ip_details = await fetch_ip_details(ip)
            results += ip_details + "\n\n"

        if results:
            await processing_message.edit_text(results.strip(), parse_mode=enums.ParseMode.HTML)
        else:
            await processing_message.edit_text("⚠️ No valid IPs provided.", parse_mode=enums.ParseMode.HTML)

    except Exception as e:
        await message.reply_text(f"⚠️ An error occurred: {str(e)}", parse_mode=enums.ParseMode.HTML)

print("Bot is running...")
app.run()
