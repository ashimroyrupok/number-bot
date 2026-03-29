import os
import json
import time
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters

TOKEN = "8277742376:AAFYbNj7sLroVHcOcRgYkQf4qnFow6hvOV4"
ADMIN_IDS = [5474672519]
COOLDOWN = 10

allUsers = set()
userService = {}
userCountry = {}
userCooldown = {}

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Ensure directories exist
for service in ["telegram", "facebook", "whatsapp"]:
    os.makedirs(f"numbers/{service}", exist_ok=True)
    countries_path = f"numbers/{service}/countries.json"
    if not os.path.exists(countries_path):
        with open(countries_path, "w", encoding="utf-8") as f:
            json.dump({}, f, indent=2, ensure_ascii=False)

# ===== Helper Functions =====
def is_admin(uid): 
    return uid in ADMIN_IDS

def load_countries(service):
    path = f"numbers/{service}/countries.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_countries(service, data):
    path = f"numbers/{service}/countries.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def read_numbers(service, code):
    path = f"numbers/{service}/{code}.txt"
    if not os.path.exists(path): return []
    with open(path, "r", encoding="utf-8") as f:
        return [x.strip() for x in f.readlines() if x.strip()]

def append_numbers(service, code, numbers):
    path = f"numbers/{service}/{code}.txt"
    with open(path, "a", encoding="utf-8") as f:
        f.write("\n".join(numbers) + "\n")

def overwrite_numbers(service, code, numbers):
    path = f"numbers/{service}/{code}.txt"
    with open(path, "w", encoding="utf-8") as f:
        if numbers:
            f.write("\n".join(numbers) + "\n")

def delete_numbers(service, code):
    path = f"numbers/{service}/{code}.txt"
    if os.path.exists(path): 
        os.remove(path)

def cooldown_left(uid):
    now = time.time()
    if uid in userCooldown:
        remain = COOLDOWN - (now - userCooldown[uid])
        return int(remain) if remain > 0 else 0
    return 0

def get_country_keyboard(service, action_prefix):
    countries = load_countries(service)
    keyboard = [[InlineKeyboardButton(f"{flag} {data['name']}", callback_data=f"{action_prefix}_{flag}")] 
                for flag, data in countries.items()]
    return InlineKeyboardMarkup(keyboard)

async def safe_edit_message(query, text, reply_markup=None, parse_mode=None):
    try:
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
    except Exception as e:
        if "Message is not modified" in str(e):
            pass
        else:
            raise e

# ===== Start Command =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    allUsers.add(uid)
    keyboard = [
        [InlineKeyboardButton("📘 Facebook", callback_data="service_facebook")],
        [InlineKeyboardButton("💬 WhatsApp", callback_data="service_whatsapp")],
        [InlineKeyboardButton("✈️ Telegram", callback_data="service_telegram")]
    ]
    await update.message.reply_text("👋 Dynamo OTP Bot\n\nSelect service:", reply_markup=InlineKeyboardMarkup(keyboard))

# ===== User Callback Handler =====
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    uid = query.from_user.id

    logging.info(f"User callback: {data}")

    if data.startswith("service_"):
        service = data.split("_")[1]
        userService[uid] = service
        await safe_edit_message(query, f"🌍 Country selection for {service.capitalize()}:", 
                               reply_markup=get_country_keyboard(service, "country"))
        return

    if data.startswith("country_"):
        service = userService.get(uid)
        flag = data.split("_")[1]
        userCountry[uid] = flag
        countries = load_countries(service)
        code = countries[flag]["code"]
        numbers = read_numbers(service, code)
        send = numbers[:3]
        remain = numbers[3:]
        overwrite_numbers(service, code, remain)
        userCooldown[uid] = time.time()

        text = f"🔥 *Dynamo OTP Numbers*\n\n🌍 Country: {flag} {countries[flag]['name']}\n📊 Remaining: {len(remain)}\n\n📋 Numbers:\n"
        for n in send: text += f"`+{n}`\n"

        keyboard = [
            [InlineKeyboardButton("➡️ Next 3 Numbers", callback_data="next")],
            [InlineKeyboardButton("🌐 Join OTP Group", url="https://t.me/dynamo_otp_group")],
            [InlineKeyboardButton("🌍 Change Country", callback_data="change_country")]
        ]
        await safe_edit_message(query, text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return

    if data == "next":
        wait = cooldown_left(uid)
        if wait > 0:
            await query.answer(f"⏳ {wait} sec remaining", show_alert=True)
            return

        service = userService.get(uid)
        flag = userCountry.get(uid)
        countries = load_countries(service)
        code = countries[flag]["code"]
        numbers = read_numbers(service, code)

        if not numbers:
            await safe_edit_message(query, "❌ No numbers left.")
            return

        send = numbers[:3]
        remain = numbers[3:]
        overwrite_numbers(service, code, remain)
        userCooldown[uid] = time.time()

        text = f"🔥 *Dynamo OTP Numbers*\n\n🌍 Country: {flag} {countries[flag]['name']}\n📊 Remaining: {len(remain)}\n\n📋 Numbers:\n"
        for n in send: text += f"`+{n}`\n"

        keyboard = [
            [InlineKeyboardButton("➡️ Next 3 Numbers", callback_data="next")],
            [InlineKeyboardButton("🌐 Join OTP Group", url="https://t.me/dynamo_otp_group")],
            [InlineKeyboardButton("🌍 Change Country", callback_data="change_country")]
        ]
        await safe_edit_message(query, text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return

    if data == "change_country":
        service = userService.get(uid)
        if service:
            await safe_edit_message(query, f"🌍 Country selection for {service.capitalize()}:", 
                                   reply_markup=get_country_keyboard(service, "country"))

# ===== Admin Panel =====
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    keyboard = [
        [InlineKeyboardButton("➕ Add Country", callback_data="admin_add_country")],
        [InlineKeyboardButton("🗑 Delete Country", callback_data="admin_delete_country")],
        [InlineKeyboardButton("➕ Add Numbers", callback_data="admin_add_numbers")],
        [InlineKeyboardButton("🗑 Delete Numbers", callback_data="admin_delete_numbers")],
        [InlineKeyboardButton("📊 Country Stats", callback_data="admin_stats")],
        [InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast")]
    ]
    await update.message.reply_text("🔧 Admin Panel - Select Action:", reply_markup=InlineKeyboardMarkup(keyboard))

# ===== Admin Callback Handler (FULL) =====
async def admin_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    uid = query.from_user.id

    if not is_admin(uid): return
    logging.info(f"Admin callback: {data}")

    # ===== Country Stats =====
    if data == "admin_stats":
        keyboard = [
            [InlineKeyboardButton("Telegram", callback_data="stats_telegram")],
            [InlineKeyboardButton("Facebook", callback_data="stats_facebook")],
            [InlineKeyboardButton("Whatsapp", callback_data="stats_whatsapp")]
        ]
        await safe_edit_message(query, "Select service to view stats:", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data.startswith("stats_"):
        service = data.split("_")[1]
        countries = load_countries(service)
        if not countries:
            await safe_edit_message(query, f"❌ No countries available in {service}.")
            return

        text = f"📊 *{service.capitalize()} Country Stats*\n\n"
        for flag, info in countries.items():
            code = info["code"]
            numbers = read_numbers(service, code)
            text += f"{flag} {info['name']}: {len(numbers)} numbers remaining\n"
        await safe_edit_message(query, text, parse_mode="Markdown")
        return

    # ===== Broadcast =====
    if data == "admin_broadcast":
        context.user_data["step"] = "broadcast"
        await safe_edit_message(query, "✉️ Send the message to broadcast to all users:")
        return

    # ===== Existing Admin Actions =====
    if data in ["admin_add_country", "admin_delete_country", "admin_add_numbers", "admin_delete_numbers"]:
        context.user_data["step"] = data
        keyboard = [
            [InlineKeyboardButton("Telegram", callback_data=f"{data}_telegram")],
            [InlineKeyboardButton("Facebook", callback_data=f"{data}_facebook")],
            [InlineKeyboardButton("Whatsapp", callback_data=f"{data}_whatsapp")]
        ]
        await safe_edit_message(query, "Select service first:", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    for action in ["admin_add_country", "admin_delete_country", "admin_add_numbers", "admin_delete_numbers"]:
        if data.startswith(f"{action}_"):
            service = data.split("_")[-1]
            context.user_data["admin_service"] = service
            context.user_data["step"] = action
            countries = load_countries(service)

            if action == "admin_add_country":
                await query.edit_message_text("Send country in format:\n🇧🇩|Bangladesh|bd")
            elif action == "admin_delete_country":
                if not countries:
                    await safe_edit_message(query, "❌ No countries available.")
                    return
                keyboard = [[InlineKeyboardButton(f"{f} {info['name']}", callback_data=f"delcountry_{f}")] for f, info in countries.items()]
                await safe_edit_message(query, "Select country to delete:", reply_markup=InlineKeyboardMarkup(keyboard))
            elif action == "admin_add_numbers":
                if not countries:
                    await safe_edit_message(query, "❌ No countries available.")
                    return
                keyboard = [[InlineKeyboardButton(f"{f} {info['name']}", callback_data=f"addnum_{f}")] for f, info in countries.items()]
                await safe_edit_message(query, "Select country to add numbers:", reply_markup=InlineKeyboardMarkup(keyboard))
            elif action == "admin_delete_numbers":
                if not countries:
                    await safe_edit_message(query, "❌ No countries available.")
                    return
                keyboard = [[InlineKeyboardButton(f"{f} {info['name']}", callback_data=f"delnum_{f}")] for f, info in countries.items()]
                await safe_edit_message(query, "Select country to delete all numbers:", reply_markup=InlineKeyboardMarkup(keyboard))
            return

    if data.startswith("delcountry_"):
        service = context.user_data.get("admin_service")
        flag = data.split("_")[1]
        countries = load_countries(service)
        if flag in countries:
            code = countries[flag]["code"]
            delete_numbers(service, code)
            del countries[flag]
            save_countries(service, countries)
            await safe_edit_message(query, f"✅ Country {flag} deleted from {service}")
        context.user_data.clear()
        return

    if data.startswith("addnum_"):
        flag = data.split("_")[1]
        context.user_data["addnum_flag"] = flag
        await safe_edit_message(query, f"Send numbers line by line for {flag}")
        return

    if data.startswith("delnum_"):
        service = context.user_data.get("admin_service")
        flag = data.split("_")[1]
        countries = load_countries(service)
        if flag in countries:
            code = countries[flag]["code"]
            delete_numbers(service, code)
            await safe_edit_message(query, f"✅ All numbers for {flag} have been deleted in {service}.")
        context.user_data.clear()
        return

# ===== Admin Message Handler =====
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_admin(uid): return

    step = context.user_data.get("step")
    service = context.user_data.get("admin_service")
    text = update.message.text.strip()

    if not step:
        return

    # ===== Broadcast Message =====
    if step == "broadcast":
        sent_count = 0
        for user_id in allUsers:
            try:
                await context.bot.send_message(user_id, text)
                sent_count += 1
            except:
                continue
        await update.message.reply_text(f"✅ Broadcast sent to {sent_count} users.")
        context.user_data.clear()
        return

    if step == "admin_add_country":
        try:
            flag, name, code = [x.strip() for x in text.split("|")]
            countries = load_countries(service)
            countries[flag] = {"name": name, "code": code}
            save_countries(service, countries)
            await update.message.reply_text(f"✅ Country {flag} {name} added to {service}")
        except:
            await update.message.reply_text("❌ Format invalid! Use: 🇧🇩|Bangladesh|bd")
        context.user_data.clear()
        return

    if step == "admin_add_numbers":
        flag = context.user_data.get("addnum_flag")
        countries = load_countries(service)
        code = countries[flag]["code"]
        numbers = [x.strip() for x in text.splitlines() if x.strip()]
        append_numbers(service, code, numbers)
        await update.message.reply_text(f"✅ {len(numbers)} numbers added to {flag} in {service}")
        context.user_data.clear()
        return

# ===== Main =====
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))

    app.add_handler(CallbackQueryHandler(button_handler, 
        pattern=r'^(service_|country_|next|change_country)'))

    app.add_handler(CallbackQueryHandler(admin_buttons, 
        pattern=r'^(admin|admin_add_country|admin_delete_country|admin_add_numbers|admin_delete_numbers|delcountry_|addnum_|delnum_|admin_stats|stats_|admin_broadcast)'))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    print("✅ Dynamo OTP Bot Running... (Country Stats & Broadcast Fixed)")
    app.run_polling()

if __name__ == "__main__":
    main()
