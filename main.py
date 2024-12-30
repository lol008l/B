import hashlib
import base58
import random
import requests
from ecdsa import SigningKey, SECP256k1
from telegram import Update
from telegram.ext import Application, CommandHandler
import time
import asyncio

API_TOKEN = '8156418368:AAHVk0ueiYrONk5FiJv-MSWLLKtk77rICCM'  # Replace with your Telegram bot token

# Step 1: Generate a random private key (from hex characters)
def generate_private_key():
    hex_chars = '0123456789abcdef'
    return ''.join(random.choice(hex_chars) for _ in range(64))

# Step 2: Convert the private key to a public key using the secp256k1 curve
def private_key_to_public_key(private_key):
    sk = SigningKey.from_string(bytes.fromhex(private_key), curve=SECP256k1)
    return sk.get_verifying_key().to_string()

# Step 3: Perform SHA256 followed by RIPEMD160 on the public key
def public_key_to_address(public_key):
    sha256_public_key = hashlib.sha256(public_key).digest()
    ripemd160_public_key = hashlib.new('ripemd160', sha256_public_key).digest()
    versioned_payload = b'\x00' + ripemd160_public_key

    sha256_first = hashlib.sha256(versioned_payload).digest()
    sha256_second = hashlib.sha256(sha256_first).digest()

    checksum = sha256_second[:4]
    final_payload = versioned_payload + checksum

    return base58.b58encode(final_payload).decode('utf-8')

# Fetch the Bitcoin balance using an API (Blockchain.com) with retries and timeout handling
def get_btc_balance(address, retries=3, delay=5):
    url = f"https://api.blockchain.info/q/getreceivedbyaddress/{address}"
    for attempt in range(retries):
        try:
            response = requests.get(url, timeout=10)  # Timeout set to 10 seconds
            if response.status_code != 200:
                print("Error: Unable to fetch data from Blockchain.com.")
                return None
            balance = response.text
            if balance.isdigit():
                return int(balance) / 1e8  # Convert satoshis to BTC
            else:
                print(f"Error: Invalid response for address {address}")
                return None
        except requests.exceptions.Timeout:
            print(f"Timeout occurred, retrying ({attempt + 1}/{retries})...")
            time.sleep(delay)
    return None

# Periodically check Bitcoin addresses
async def check_addresses(update: Update, context, message):
    count = 0
    while True:
        private_key = generate_private_key()
        public_key = private_key_to_public_key(private_key)
        bitcoin_address = public_key_to_address(public_key)
        
        balance = get_btc_balance(bitcoin_address)
        count += 1

        if count % 1000 == 0:  # Update every 1000 addresses checked
            msg = f"🔄 Checked {count} addresses\n"
            msg += f"🔑 Private Key: {private_key}\n"
            msg += f"📬 Address: {bitcoin_address}\n"
            msg += f"💰 Balance: {balance} BTC\n"
            
            # Edit the existing message
            await message.edit_text(msg)

        if balance and balance > 0.0001:
            found_message = f"🎉 Found balance!\nPrivate Key: {private_key}\n"
            found_message += f"Bitcoin Address: {bitcoin_address} | Balance: {balance} BTC\n"
            found_message += f"Checked Addresses: {count}"
            
            # Send the found balance message
            await update.message.reply_text(found_message)

        await asyncio.sleep(1)  # Add a small delay to avoid overloading requests

# Handler for the /start command
async def start(update: Update, context):
    # Send the initial message that can be edited
    message = await update.message.reply_text("Starting Bitcoin address checker...")
    
    # Start checking addresses automatically
    await check_addresses(update, context, message)

# Main function to start the bot
def main():
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(API_TOKEN).build()

    # Register the start command handler
    application.add_handler(CommandHandler("start", start))

    # Start the Bot
    application.run_polling(timeout=30)  # Timeout for polling set to 30 seconds

if __name__ == '__main__':
    main()