import os
import shutil
import hashlib
import json
import speedtest
import threading
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, ChatMemberHandler

# Flask app for health check
app = Flask(__name__)

@app.route('/health', methods=['GET'])
def health_check():
    return "OK", 200

def run_flask():
    app.run(host='0.0.0.0', port=8080)

# Directory to store videos
VIDEO_DIRECTORY = 'videos/'

# Ensure the video directory exists
if not os.path.exists(VIDEO_DIRECTORY):
    os.makedirs(VIDEO_DIRECTORY)

# Channel username and admin user ID
CHANNEL_USERNAME = "@leafposting"
ADMIN_USER_ID = 7211160670

# File to store video hash data
HASH_DATA_FILE = 'video_hashes.json'

# Load existing hash data from the file
def load_hash_data():
    if os.path.exists(HASH_DATA_FILE):
        with open(HASH_DATA_FILE, 'r') as file:
            return json.load(file)
    return {}

# Save hash data to the file
def save_hash_data(data):
    with open(HASH_DATA_FILE, 'w') as file:
        json.dump(data, file)

# Function to generate the SHA256 hash of a file
def generate_file_hash(file_path):
    hash_sha256 = hashlib.sha256()
    with open(file_path, 'rb') as file:
        while chunk := file.read(8192):
            hash_sha256.update(chunk)
    return hash_sha256.hexdigest()

# Force subscription check
async def check_subscription(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    try:
        # Check if the user is a member of the channel
        member = await context.bot.get_chat_member(CHANNEL_USERNAME, user_id)
        if member.status in ['member', 'administrator', 'creator']:
            return True
        else:
            inline_button = InlineKeyboardButton(
                text="Subscribe to Channel", 
                url=f"https://t.me/{CHANNEL_USERNAME[1:]}"
            )
            reply_markup = InlineKeyboardMarkup([[inline_button]])
            
            await update.message.reply_text(
                f"To interact with this bot, please subscribe to our channel: {CHANNEL_USERNAME}",
                reply_markup=reply_markup
            )
            return False
    except Exception:
        await update.message.reply_text(
            f"An error occurred. Ensure you are subscribed to {CHANNEL_USERNAME}."
        )
        return False

# Handler for video messages (Admin only)
async def handle_video(update: Update, context: CallbackContext):
    if update.message.from_user.id != ADMIN_USER_ID:
        await update.message.reply_text("Only admins can upload videos.")
        return

    if not await check_subscription(update, context):
        return

    video = update.message.video
    file_id = video.file_id
    file = await context.bot.get_file(file_id)
    
    # Download the video file
    file_path = os.path.join(VIDEO_DIRECTORY, f"{file_id}.mp4")
    await file.download_to_drive(file_path)
    
    # Generate the hash for the video
    video_hash = generate_file_hash(file_path)
    
    # Load existing data and add new hash
    video_hashes = load_hash_data()
    video_hashes[video_hash] = file_path
    
    # Save the updated data
    save_hash_data(video_hashes)
    
    # Create the inline button with the bot link
    bot_username = (await context.bot.get_me()).username
    inline_button = InlineKeyboardButton(
        text="Get Video by Hash",
        url=f"tg://resolve?domain={bot_username}&text={video_hash}"
    )
    reply_markup = InlineKeyboardMarkup([[inline_button]])

    await update.message.reply_text(f"Video uploaded successfully! Hash: {video_hash}", reply_markup=reply_markup)

# Handler for receiving the hash (for non-admins and users)
async def handle_hash(update: Update, context: CallbackContext):
    user_hash = update.message.text.strip()

    # Load the video hash data
    video_hashes = load_hash_data()

    if user_hash in video_hashes:
        video_path = video_hashes[user_hash]
        await update.message.reply_video(open(video_path, 'rb'))
    else:
        await update.message.reply_text("Hash not found or incorrect hash!")

# Command handler for /start
async def start(update: Update, context: CallbackContext):
    if not await check_subscription(update, context):
        return
    await update.message.reply_text("Welcome! Send a video (admin only) to get its hash. Use the hash to retrieve the video later.")

# Command handler for /speed to measure internet speed
async def speed_test(update: Update, context: CallbackContext):
    try:
        await update.message.reply_text("Measuring speed, please wait...")
        st = speedtest.Speedtest()
        st.get_best_server()
        
        download_speed = st.download() / 1_000_000  # Convert to Mbps
        upload_speed = st.upload() / 1_000_000  # Convert to Mbps
        
        response = (f"Internet Speed Test Results:\n"
                    f"Download Speed: {download_speed:.2f} Mbps\n"
                    f"Upload Speed: {upload_speed:.2f} Mbps")
        await update.message.reply_text(response)
    except Exception as e:
        await update.message.reply_text(f"Error measuring speed: {e}")

# Command handler for /local to check storage usage
async def check_local_storage(update: Update, context: CallbackContext):
    try:
        total, used, free = shutil.disk_usage(".")
        
        total_gb = total / (1024 ** 3)
        used_gb = used / (1024 ** 3)
        free_gb = free / (1024 ** 3)
        
        response = (f"Local Storage Usage:\n"
                    f"Total: {total_gb:.2f} GB\n"
                    f"Used: {used_gb:.2f} GB\n"
                    f"Free: {free_gb:.2f} GB")
        await update.message.reply_text(response)
    except Exception as e:
        await update.message.reply_text(f"Error checking storage: {e}")

# Main function to run the bot and Flask server
def main():
    application = Application.builder().token("7649741419:AAFiBlAl861aG1WY_74JQQfJE6YWDRAxdJI").build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("speed", speed_test))
    application.add_handler(CommandHandler("local", check_local_storage))
    application.add_handler(MessageHandler(filters.VIDEO, handle_video))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_hash))
    application.add_handler(ChatMemberHandler(check_subscription, ChatMemberHandler.MY_CHAT_MEMBER))

    # Run Flask in a separate thread
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

    # Start the bot
    application.run_polling()

if __name__ == '__main__':
    main()


