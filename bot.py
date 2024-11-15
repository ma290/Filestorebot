import os
import hashlib
import speedtest
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, ChatMemberHandler

# Directory to store videos
VIDEO_DIRECTORY = 'videos/'

# Ensure the video directory exists
if not os.path.exists(VIDEO_DIRECTORY):
    os.makedirs(VIDEO_DIRECTORY)

# Channel username (replace with your actual channel's username)
CHANNEL_USERNAME = "@leafposting"  # Updated to your channel
ADMIN_USER_ID = 6630039904  # Replace with your admin user ID

# Function to generate the SHA256 hash of a file
def generate_file_hash(file_path):
    hash_sha256 = hashlib.sha256()
    with open(file_path, 'rb') as file:
        while chunk := file.read(8192):  # Read in chunks
            hash_sha256.update(chunk)
    return hash_sha256.hexdigest()

# Force subscription check
async def check_subscription(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    try:
        # Check if the user is a member of the channel
        member = await context.bot.get_chat_member(CHANNEL_USERNAME, user_id)
        if member.status in ['member', 'administrator', 'creator']:
            # If the user is a member, proceed with the bot's functionality
            return True
        else:
            # Send a message with an inline button for subscribing
            inline_button = InlineKeyboardButton(
                text="Subscribe to Channel", 
                url=f"https://t.me/{CHANNEL_USERNAME[1:]}"
            )
            reply_markup = InlineKeyboardMarkup([[inline_button]])
            
            await update.message.reply_text(
                f"To interact with this bot, you need to subscribe to our channel: {CHANNEL_USERNAME}\nPlease subscribe and try again.",
                reply_markup=reply_markup
            )
            return False
    except Exception as e:
        await update.message.reply_text(
            f"An error occurred while checking subscription. Please ensure you are subscribed to {CHANNEL_USERNAME}."
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
    
    # Get best server based on ping
    st.get_best_server()
    
    # Download speed in Mbps
    download_speed = st.download() / 1_000_000  # Convert from bits to Mbps
    
    # Upload speed in Mbps
    upload_speed = st.upload() / 1_000_000  # Convert from bits to Mbps
    
    # Ping in ms
    ping = st.results.ping
    
    return download_speed, upload_speed, ping

# Handler for video messages (Admin only)
async def handle_video(update: Update, context: CallbackContext):
    # Check if the user is the admin
    if update.message.from_user.id != ADMIN_USER_ID:
        await update.message.reply_text("Only admins can upload videos.")
        return

    # First check if the user is subscribed
    if not await check_subscription(update, context):
        return

    # Get the video file sent by the user
    video = update.message.video
    file_id = video.file_id
    
    # Access the bot instance via the context
    file = await context.bot.get_file(file_id)
    
    # Download the video file locally
    file_path = os.path.join(VIDEO_DIRECTORY, f"{file_id}.mp4")
    await file.download_to_drive(file_path)
    
    # Generate the hash for the video
    video_hash = generate_file_hash(file_path)
    
    # Store the hash and file mapping in chat data
    context.chat_data['video_hash'] = video_hash
    context.chat_data['video_path'] = file_path
    
    # Create the inline button with the tg://resolve link containing the hash
    inline_button = InlineKeyboardButton(
        text="Get Video by Hash",
        url=f"tg://resolve?domain=User8393838_bot&text={video_hash}"
    )
    reply_markup = InlineKeyboardMarkup([[inline_button]])

    # Acknowledge the video upload with the inline button
    await update.message.reply_text(f"Video uploaded successfully! Hash: {video_hash}", reply_markup=reply_markup)

# Handler for receiving the hash (for non-admins and users in general)
async def handle_hash(update: Update, context: CallbackContext):
    user_hash = update.message.text.strip()

    # Check if the hash exists in chat data
    if user_hash == context.chat_data.get('video_hash'):
        video_path = context.chat_data.get('video_path')

        # Send the video file back to the user
        await update.message.reply_video(open(video_path, 'rb'))
    else:
        await update.message.reply_text("Hash not found or incorrect hash!")

# Command handler for start
async def start(update: Update, context: CallbackContext):
    # First check if the user is subscribed
    if not await check_subscription(update, context):
        return
    await update.message.reply_text("Send me a video (admin only), and I will generate a hash for it. Later, you can send the hash to retrieve the video.")

# Command handler for local (to check storage usage)
async def local(update: Update, context: CallbackContext):
    # First check if the user is subscribed
    if not await check_subscription(update, context):
        return
    
    # Check if the user is the admin
    if update.message.from_user.id != ADMIN_USER_ID:
        await update.message.reply_text("Only the admin can check the storage usage.")
        return
    
    # Get the total size of the video directory
    total_size = get_directory_size(VIDEO_DIRECTORY)
    
    # Format the size in a readable format (MB)
    total_size_mb = total_size / (1024 * 1024)
    
    # Send the total storage usage to the admin
    await update.message.reply_text(f"Total storage used by videos: {total_size_mb:.2f} MB")

# Command handler for speed (to check internet speed)
async def speed(update: Update, context: CallbackContext):
    # First check if the user is subscribed
    if not await check_subscription(update, context):
        return
    
    # Check if the user is the admin
    if update.message.from_user.id != ADMIN_USER_ID:
        await update.message.reply_text("Only the admin can check the internet speed.")
        return
    
    # Get internet speed
    download_speed, upload_speed, ping = check_internet_speed()
    
    # Send the internet speed results to the admin
    await update.message.reply_text(
        f"Internet Speed:\n"
        f"Download Speed: {download_speed:.2f} Mbps\n"
        f"Upload Speed: {upload_speed:.2f} Mbps\n"
        f"Ping: {ping} ms"
    )

# Main function to run the bot
def main():
    # Create the Application instance with your bot token
    application = Application.builder().token("7247732685:AAHtSUv7iM1U-19qTvfaCr5NAk5HCefD1iY").build()

    # Add command and message handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("local", local))  # /local command
    application.add_handler(CommandHandler("speed", speed))  # /speed command
    application.add_handler(MessageHandler(filters.VIDEO, handle_video))  # Video filter (admin-only)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_hash))  # Hash filter

    # Add a handler to check the subscription when a user joins the chat or interacts
    application.add_handler(ChatMemberHandler(check_subscription, ChatMemberHandler.MY_CHAT_MEMBER))

    # Start the bot
    application.run_polling()

if __name__ == '__main__':
    main()
