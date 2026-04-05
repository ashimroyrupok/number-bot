import os
import json
import time
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters

TOKEN = "8637771357:AAEKuRfsiG--3bjEsgUKcTDLE-zVVuwseFA"
ADMIN_IDS = [5474672519,8278688915,6058876211]
COOLDOWN = 10

GROUP_LINK = "https://t.me/dynamo_otp_group"

allUsers = set()
userService = {}
userCountry = {}
userCooldown = {}

logging.basicConfig(level=logging.INFO)

for service in ["telegram","facebook","whatsapp"]:
    os.makedirs(f"numbers/{service}",exist_ok=True)
    path=f"numbers/{service}/countries.json"
    if not os.path.exists(path):
        with open(path,"w") as f:
            json.dump({},f)

def is_admin(uid):
    return uid in ADMIN_IDS

def load_countries(service):
    with open(f"numbers/{service}/countries.json") as f:
        return json.load(f)

def save_countries(service,data):
    with open(f"numbers/{service}/countries.json","w") as f:
        json.dump(data,f,indent=2)

def read_numbers(service,code):
    path=f"numbers/{service}/{code}.txt"
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return [x.strip() for x in f.readlines() if x.strip()]

def overwrite_numbers(service,code,numbers):
    path=f"numbers/{service}/{code}.txt"
    with open(path,"w") as f:
        f.write("\n".join(numbers))

def append_numbers(service,code,new_numbers):
    old=set(read_numbers(service,code))
    new=set(new_numbers)
    merged=list(old|new)
    overwrite_numbers(service,code,merged)

def delete_numbers(service,code):
    path=f"numbers/{service}/{code}.txt"
    if os.path.exists(path):
        os.remove(path)

def get_country_keyboard(service,prefix):
    countries=load_countries(service)
    keyboard=[[InlineKeyboardButton(f"{f} {d['name']}",callback_data=f"{prefix}_{f}")] for f,d in countries.items()]
    return InlineKeyboardMarkup(keyboard)

async def start(update:Update,context:ContextTypes.DEFAULT_TYPE):
    uid=update.effective_user.id
    allUsers.add(uid)

    keyboard=[
        [InlineKeyboardButton("📘 Facebook",callback_data="service_facebook")],
        [InlineKeyboardButton("💬 WhatsApp",callback_data="service_whatsapp")],
        [InlineKeyboardButton("✈️ Telegram",callback_data="service_telegram")]
    ]

    await update.message.reply_text(
        "👋 Dynamo OTP Bot\n\nSelect service:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def button_handler(update:Update,context:ContextTypes.DEFAULT_TYPE):

    query=update.callback_query
    await query.answer()
    data=query.data
    uid=query.from_user.id

    if data.startswith("service_"):

        service=data.split("_")[1]
        userService[uid]=service

        await query.edit_message_text(
            "🌍 Select country",
            reply_markup=get_country_keyboard(service,"country")
        )

    elif data.startswith("country_"):

        service=userService[uid]
        flag=data.split("_")[1]

        countries=load_countries(service)
        code=countries[flag]["code"]

        numbers=read_numbers(service,code)

        send=numbers[:3]
        remain=numbers[3:]

        overwrite_numbers(service,code,remain)

        remaining=len(remain)

        userCooldown[uid]=time.time()
        userCountry[uid]=flag

        text="🔥 *Dynamo OTP Numbers*\n\n"
        text+=f"📦 Remaining Numbers: {remaining}\n\n"

        for n in send:
            text+=f"`+{n}`\n\n"

        keyboard=[
            [InlineKeyboardButton("➡️ Next 3 Numbers",callback_data="next")],
            [InlineKeyboardButton("🌍 Change Country",callback_data="change_country")],
            [InlineKeyboardButton("🔗 OTP BOT Group",url=GROUP_LINK)]
        ]

        await query.edit_message_text(
            text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif data=="next":

        service=userService[uid]
        flag=userCountry[uid]

        countries=load_countries(service)
        code=countries[flag]["code"]

        numbers=read_numbers(service,code)

        send=numbers[:3]
        remain=numbers[3:]

        overwrite_numbers(service,code,remain)

        remaining=len(remain)

        text="🔥 *Next Numbers*\n\n"
        text+=f"📦 Remaining Numbers: {remaining}\n\n"

        for n in send:
            text+=f"`+{n}`\n\n"

        keyboard=[
            [InlineKeyboardButton("➡️ Next 3 Numbers",callback_data="next")],
            [InlineKeyboardButton("🌍 Change Country",callback_data="change_country")],
            [InlineKeyboardButton("🔗 OTP BOT Group",url=GROUP_LINK)]
        ]

        await query.edit_message_text(
            text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif data=="change_country":

        service=userService[uid]

        await query.edit_message_text(
            "🌍 Select country",
            reply_markup=get_country_keyboard(service,"country")
        )

async def admin(update:Update,context:ContextTypes.DEFAULT_TYPE):

    if not is_admin(update.effective_user.id):
        return

    keyboard=[
        [InlineKeyboardButton("➕ Add Country",callback_data="admin_add_country")],
        [InlineKeyboardButton("🗑 Delete Country",callback_data="admin_delete_country")],
        [InlineKeyboardButton("➕ Add Numbers",callback_data="admin_add_numbers")],
        [InlineKeyboardButton("🗑 Delete Numbers",callback_data="admin_delete_numbers")],
        [InlineKeyboardButton("📊 Country Stats",callback_data="admin_stats")],
        [InlineKeyboardButton("📢 Broadcast",callback_data="admin_broadcast")]
    ]

    await update.message.reply_text(
        "🔧 Admin Panel",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def admin_buttons(update:Update,context:ContextTypes.DEFAULT_TYPE):

    query=update.callback_query
    await query.answer()

    data=query.data
    uid=query.from_user.id

    if not is_admin(uid):
        return

    if data=="admin_stats":

        text="📊 Country Stats\n\n"

        for service in ["telegram","facebook","whatsapp"]:

            countries=load_countries(service)

            for f,d in countries.items():
                count=len(read_numbers(service,d["code"]))
                text+=f"{service} {f} {d['name']} : {count}\n"

        await query.edit_message_text(text)

    elif data=="admin_broadcast":

        context.user_data["step"]="broadcast"
        await query.edit_message_text("Send broadcast message")

    elif data in ["admin_add_country","admin_delete_country","admin_add_numbers","admin_delete_numbers"]:

        context.user_data["step"]=data

        keyboard=[
            [InlineKeyboardButton("Telegram",callback_data=f"{data}_telegram")],
            [InlineKeyboardButton("Facebook",callback_data=f"{data}_facebook")],
            [InlineKeyboardButton("Whatsapp",callback_data=f"{data}_whatsapp")]
        ]

        await query.edit_message_text(
            "Select service",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif "_telegram" in data or "_facebook" in data or "_whatsapp" in data:

        action,service=data.rsplit("_",1)

        context.user_data["admin_service"]=service
        context.user_data["step"]=action

        countries=load_countries(service)

        if action=="admin_add_country":
            await query.edit_message_text("Send: 🇧🇩|Bangladesh|bd")

        elif action=="admin_delete_country":

            keyboard=[
                [InlineKeyboardButton(f"{f} {d['name']}",callback_data=f"delcountry_{f}")]
                for f,d in countries.items()
            ]

            await query.edit_message_text(
                "Select country",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

        elif action=="admin_add_numbers":

            keyboard=[
                [InlineKeyboardButton(f"{f} {d['name']}",callback_data=f"addnum_{f}")]
                for f,d in countries.items()
            ]

            await query.edit_message_text(
                "Upload TXT file",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

        elif action=="admin_delete_numbers":

            keyboard=[
                [InlineKeyboardButton(f"{f} {d['name']}",callback_data=f"delnum_{f}")]
                for f,d in countries.items()
            ]

            await query.edit_message_text(
                "Select country",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

    elif data.startswith("addnum_"):

        flag=data.split("_")[1]
        context.user_data["addnum_flag"]=flag
        context.user_data["step"]="upload_numbers"

        await query.edit_message_text("📄 Upload numbers TXT file")

    elif data.startswith("delnum_"):

        flag=data.split("_")[1]
        service=context.user_data["admin_service"]

        countries=load_countries(service)
        code=countries[flag]["code"]

        delete_numbers(service,code)

        await query.edit_message_text("✅ Numbers deleted")

    elif data.startswith("delcountry_"):

        flag=data.split("_")[1]
        service=context.user_data["admin_service"]

        countries=load_countries(service)

        if flag in countries:
            code=countries[flag]["code"]

            del countries[flag]
            save_countries(service,countries)

            delete_numbers(service,code)

            await query.edit_message_text("✅ Country deleted")

async def message_handler(update:Update,context:ContextTypes.DEFAULT_TYPE):

    uid=update.effective_user.id

    if not is_admin(uid):
        return

    step=context.user_data.get("step")
    service=context.user_data.get("admin_service")

    if step=="broadcast":

        text=update.message.text

        for u in allUsers:
            try:
                await context.bot.send_message(u,text)
            except:
                pass

        await update.message.reply_text("Broadcast done")
        context.user_data.clear()

    elif step=="admin_add_country":

        try:
            flag,name,code=update.message.text.split("|")

            countries=load_countries(service)

            countries[flag]={
                "name":name,
                "code":code
            }

            save_countries(service,countries)

            await update.message.reply_text("✅ Country added")

        except:
            await update.message.reply_text("❌ Format:\n🇧🇩|Bangladesh|bd")

        context.user_data.clear()

async def file_handler(update:Update,context:ContextTypes.DEFAULT_TYPE):

    uid=update.effective_user.id

    if not is_admin(uid):
        return

    if context.user_data.get("step")!="upload_numbers":
        return

    file=await update.message.document.get_file()

    path="upload.txt"

    await file.download_to_drive(path)

    with open(path) as f:
        numbers=[x.strip() for x in f.readlines() if x.strip()]

    flag=context.user_data["addnum_flag"]
    service=context.user_data["admin_service"]

    countries=load_countries(service)
    code=countries[flag]["code"]

    append_numbers(service,code,numbers)

    country_name=countries[flag]["name"]

    await update.message.reply_text(
f"""✅ Numbers Added Successfully

🌍 Country: {country_name}
🔰 Service: {service}

📦 Added Numbers: {len(numbers)}
"""
)

    context.user_data.clear()

def main():

    app=Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start",start))
    app.add_handler(CommandHandler("admin",admin))

    app.add_handler(CallbackQueryHandler(button_handler,pattern="^(service_|country_|next|change_country)"))

    app.add_handler(CallbackQueryHandler(admin_buttons))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND,message_handler))
    app.add_handler(MessageHandler(filters.Document.ALL,file_handler))

    print("✅ Dynamo OTP Bot Running")

    app.run_polling(drop_pending_updates=True)

if __name__=="__main__":
    main()
