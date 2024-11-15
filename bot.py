import os
import hashlib
import speedtest
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext

# Directory to store videos
VIDEO_DIRECTORY = 'videos/'

# Ensure the video directory exists
if not os.path.exists(VIDEO_DIRECTORY):
    os.makedirs(VIDEO_DIRECTORY)

# Channel username and Admin User ID
CHANNEL_USERNAME = "@leafposting"
ADMIN_USER_ID = 6630039904

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
                f"To interact with this bot, you need to subscribe to our channel: {CHANNEL_USERNAME}",
                reply_markup=reply_markup
            )
            return False
    except Exception:
        await update.message.reply_text(
            f"Error checking subscription. Ensure you're subscribed to {CHANNEL_USERNAME}."
        )
        return False

# Function to calculate the total size of the video directory
def get_directory_size(directory_path):
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(directory_path):
        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            total_size += os.path.getsize(filepath)
    return total_size

# Function to check internet speed
def check_internet_speed():
    st = speedtest.Speedtest()
    st.get_best_server()
    download_speed = st.download() / 1_000_000
    upload_speed = st.upload() / 1_000_000
    ping = st.results.ping
    return download_speed, upload_speed, ping

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
    
    file_path = os.path.join(VIDEO_DIRECTORY, f"{file_id}.mp4")
    await file.download_to_drive(file_path)
    
    video_hash = generate_file_hash(file_path)
    context.chat_data['video_hash'] = video_hash
    context.chat_data['video_path'] = file_path
    
    inline_button = InlineKeyboardButton(
        text="Get Video by Hash",
        url=f"tg://resolve?domain=Leafsavebot&text={video_hash}"
    )
    reply_markup = InlineKeyboardMarkup([[inline_button]])
    await update.message.reply_text(f"Video uploaded! Hash: {video_hash}", reply_markup=reply_markup)

# Handler for receiving the hash
async def handle_hash(update: Update, context: CallbackContext):
    user_hash = update.message.text.strip()
    if user_hash == context.chat_data.get('video_hash'):
        video_path = context.chat_data.get('video_path')
        await update.message.reply_video(open(video_path, 'rb'))
    else:
        await update.message.reply_text("Hash not found!")

# Command handler for start
async def start(update: Update, context: CallbackContext):
    if not await check_subscription(update, context):
        return
    await update.message.reply_text("Send a video (admin only) to get a hash or retrieve a video by sending its hash.")

# Command handler for /local to check storage usage
async def local(update: Update, context: CallbackContext):
    if update.message.from_user.id != ADMIN_USER_ID:
        await update.message.reply_text("Only the admin can check storage.")
        return
    total_size = get_directory_size(VIDEO_DIRECTORY)
    total_size_mb = total_size / (1024 * 1024)
    await update.message.reply_text(f"Total storage used: {total_size_mb:.2f} MB")

# Command handler for /speed to check internet speed
async def speed(update: Update, context: CallbackContext):
    if update.message.from_user.id != ADMIN_USER_ID:
        await update.message.reply_text("Only the admin can check internet speed.")
        return
    download_speed, upload_speed, ping = check_internet_speed()
    await update.message.reply_text(
        f"Speed Test Results:\nDownload: {download_speed:.2f} Mbps\nUpload: {upload_speed:.2f} Mbps\nPing: {ping} ms"
    )

# Main function to run the bot with webhook
def main():
    TOKEN = "7649741419:AAFiBlAl861aG1WY_74JQQfJE6YWDRAxdJI"
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("local", local))
    application.add_handler(CommandHandler("speed", speed))
    application.add_handler(MessageHandler(filters.VIDEO, handle_video))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_hash))

    # Set up the webhook
    PORT = int(os.environ.get("PORT", 8000))
    application.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        webhook_url="https://responsible-hildagard-ashutosh0879-8efaf2e5.koyeb.app/webhook"
    )

if __name__ == '__main__':
    main()
