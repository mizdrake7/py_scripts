from telegram import Update
from telegram.ext import Application, CommandHandler
import datetime
import pytz

TOKEN = ''

# Set the time zone to India Standard Time (IST)
timezone = pytz.timezone('Asia/Kolkata')

# Function to calculate the exact time left until 2026 (days, hours, minutes, seconds)
def time_left_in_2026():
    today = datetime.datetime.now(timezone)  # Get the current time in IST	
    print(f"Current Time in IST: {today}")  # Debug line to print the current time in IST	
    new_year_2026 = datetime.datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone)  # Set target datetime for IST
    
    # If today is already in 2026, return 0 for everything
    if today >= new_year_2026:
        return 0, 0, 0, 0
    
    remaining_time = new_year_2026 - today
    days = remaining_time.days
    hours = remaining_time.seconds // 3600
    minutes = (remaining_time.seconds // 60) % 60
    seconds = remaining_time.seconds % 60
    
    return days, hours, minutes, seconds

# Command handler for the /left command
async def left(update: Update, context):
    days, hours, minutes, seconds = time_left_in_2026()
    message = f"There are {days} days, {hours} hours, {minutes} minutes, and {seconds} seconds left until 2026!"
    await update.message.reply_text(message)

# Command handler for the /start command (initial message when user starts bot)
async def start(update: Update, context):
    welcome_message = "Hello! Type /left to see how many days, hours, minutes, and seconds are left until 2026."
    await update.message.reply_text(welcome_message)

# Main function to run the bot
def main():
    # Initialize the bot with the new syntax for python-telegram-bot v20+
    application = Application.builder().token(TOKEN).build()

    # Register the /left and /start command handlers
    start_handler = CommandHandler('start', start)
    left_handler = CommandHandler('left', left)
    
    application.add_handler(start_handler)
    application.add_handler(left_handler)

    # Start the bot
    application.run_polling()

if __name__ == "__main__":
    main()
