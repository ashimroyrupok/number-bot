import os
import json
import logging
import re

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters

TOKEN="8637771357:AAHzG6J-L9GcsR-Rk5lHLrTiU5GEysXa-Eo"

ADMIN_IDS=[5474672519,8278688915,6058876211]

GROUP_LINK="https://t.me/dynamo_otp_group"

allUsers=set()
userService={}
userCountry={}
numberOwner={}

logging.basicConfig(level=logging.INFO)

OTP_REGEX=r"\b\d{4,8}\b"

NUMBER_PATTERNS=[
r"\+\d{9,15}",
r"\d{9,15}",
r"\+\d{2,6}\*{2,8}\d{2,6}",
r"\d{2,6}\*{2,8}\d{2,6}"
]

# ফোল্ডার তৈরি করার সময় আপনার স্ট্রাকচার অনুযায়ী 'numbers/service' পাথ ব্যবহার করা হয়েছে
for service in ["telegram","facebook","whatsapp"]:
    os.makedirs(f"numbers/{service}",exist_ok=True)
    path=f"numbers/{service}/countries.json"
    if not os.path.exists(path):
        with open(path,"w") as f:
            json.dump({},f)

def is_admin(uid):
    return uid in ADMIN_IDS

def load_countries(service):
    path = f"numbers/{service}/countries.json"
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {}

def save_countries(service,data):
    path = f"numbers/{service}/countries.json"
    with open(path,"w") as f:
        json.dump(data,f,indent=2)

def read_numbers(service,code):
    # আপনার স্ট্রাকচার অনুযায়ী numbers/{service}/{code}.txt
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

# নির্দিষ্ট সার্ভিসের নির্দিষ্ট দেশের ফাইল ডিলিট করার ফাংশন
def delete_numbers_file(service,code):
    path=f"numbers/{service}/{code}.txt"
    if os.path.exists(path):
        os.remove(path)

def get_country_keyboard(service,prefix):
    countries=load_countries(service)
    keyboard=[
        [InlineKeyboardButton(f"{f} {d['name']}",callback_data=f"{prefix}_{f}")]
        for f,d in countries.items()
    ]
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
        
        if not numbers:
            await query.edit_message_text("❌ No numbers available for this country.")
            return

        send=numbers[:3]
        remain=numbers[3:]
        overwrite_numbers(service,code,remain)
        
        text="🔥 *Dynamo OTP Numbers*\n\n"
        for k,v in list(numberOwner.items()):
            if v==uid:
                del numberOwner[k]
        
        for n in send:
            text+=f"`+{n}`\n\n"
            clean=n.replace("+","").replace("*","")
            last4=clean[-4:]
            numberOwner[last4]=uid
            
        keyboard=[
            [InlineKeyboardButton("➡️ Next 3 Numbers",callback_data="next")],
            [InlineKeyboardButton("🌍 Change Country",callback_data="change_country")],
            [InlineKeyboardButton("🔗 OTP BOT Group",url=GROUP_LINK)]
        ]
        userCountry[uid]=flag
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data=="next":
        service=userService[uid]
        flag=userCountry[uid]
        countries=load_countries(service)
        code=countries[flag]["code"]
        numbers=read_numbers(service,code)
        
        if not numbers:
            await query.edit_message_text("❌ No more numbers available.")
            return

        send=numbers[:3]
        remain=numbers[3:]
        overwrite_numbers(service,code,remain)
        
        text="🔥 *Next Numbers*\n\n"
        for k,v in list(numberOwner.items()):
            if v==uid:
                del numberOwner[k]
        for n in send:
            text+=f"`+{n}`\n\n"
            clean=n.replace("+","").replace("*","")
            last4=clean[-4:]
            numberOwner[last4]=uid
            
        keyboard=[
            [InlineKeyboardButton("➡️ Next 3 Numbers",callback_data="next")],
            [InlineKeyboardButton("🌍 Change Country",callback_data="change_country")],
            [InlineKeyboardButton("🔗 OTP BOT Group",url=GROUP_LINK)]
        ]
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data=="change_country":
        service=userService.get(uid)
        if service:
            await query.edit_message_text("🌍 Select country", reply_markup=get_country_keyboard(service,"country"))

async def otp_group_listener(update:Update,context:ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    text=update.message.text
    otp=re.search(OTP_REGEX,text)
    if not otp: return
    
    number=None
    for p in NUMBER_PATTERNS:
        m=re.search(p,text)
        if m:
            number=m.group(0)
            break
    if not number: return
    
    clean=number.replace("+","").replace("*","")
    last4=clean[-4:]
    if last4 in numberOwner:
        uid=numberOwner[last4]
        try:
            await context.bot.send_message(uid, f"📩 OTP Received:\n\n{text}")
        except: pass

async def admin(update:Update,context:ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    keyboard=[
        [InlineKeyboardButton("➕ Add Country",callback_data="admin_add_country")],
        [InlineKeyboardButton("🗑 Delete Country",callback_data="admin_delete_country")],
        [InlineKeyboardButton("➕ Add Numbers",callback_data="admin_add_numbers")],
        [InlineKeyboardButton("🗑 Delete Numbers",callback_data="admin_delete_numbers")],
        [InlineKeyboardButton("📊 Country Stats",callback_data="admin_stats")],
        [InlineKeyboardButton("📢 Broadcast",callback_data="admin_broadcast")]
    ]
    await update.message.reply_text("🔧 Admin Panel", reply_markup=InlineKeyboardMarkup(keyboard))

async def admin_buttons(update:Update,context:ContextTypes.DEFAULT_TYPE):
    query=update.callback_query
    await query.answer()
    data=query.data
    uid=query.from_user.id
    if not is_admin(uid): return

    if data=="admin_stats":
        text="📊 Country Stats\n\n"
        for service in ["telegram","facebook","whatsapp"]:
            countries=load_countries(service)
            for f,d in countries.items():
                count=len(read_numbers(service,d["code"]))
                text+=f"{service.capitalize()} {f} {d['name']} : {count}\n"
        await query.edit_message_text(text)

    elif data=="admin_broadcast":
        context.user_data["step"]="broadcast"
        await query.edit_message_text("Send broadcast message:")

    elif data in ["admin_add_country","admin_delete_country","admin_add_numbers","admin_delete_numbers"]:
        context.user_data["step"]=data
        keyboard=[
            [InlineKeyboardButton("Telegram",callback_data=f"{data}_telegram")],
            [InlineKeyboardButton("Facebook",callback_data=f"{data}_facebook")],
            [InlineKeyboardButton("Whatsapp",callback_data=f"{data}_whatsapp")]
        ]
        await query.edit_message_text("Select service:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif any(x in data for x in ["_telegram", "_facebook", "_whatsapp"]):
        action, service = data.rsplit("_", 1)
        context.user_data["admin_service"] = service
        context.user_data["step"] = action
        countries = load_countries(service)

        if action == "admin_add_country":
            await query.edit_message_text("Send format:\n🇧🇩|Bangladesh|880")
        elif action == "admin_delete_country":
            keyboard = [[InlineKeyboardButton(f"{f} {d['name']}", callback_data=f"delcountry_{f}")] for f, d in countries.items()]
            await query.edit_message_text("Select country to DELETE:", reply_markup=InlineKeyboardMarkup(keyboard))
        elif action == "admin_add_numbers":
            keyboard = [[InlineKeyboardButton(f"{f} {d['name']}", callback_data=f"addnum_{f}")] for f, d in countries.items()]
            await query.edit_message_text("Select country to ADD numbers:", reply_markup=InlineKeyboardMarkup(keyboard))
        elif action == "admin_delete_numbers":
            keyboard = [[InlineKeyboardButton(f"{f} {d['name']}", callback_data=f"delnum_{f}")] for f, d in countries.items()]
            await query.edit_message_text("Select country to CLEAR numbers:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("addnum_"):
        flag=data.split("_")[1]
        context.user_data["addnum_flag"]=flag
        context.user_data["step"]="upload_numbers"
        await query.edit_message_text(f"📄 Upload .txt file for {flag}")

    elif data.startswith("delnum_"):
        flag=data.split("_")[1]
        service=context.user_data.get("admin_service")
        countries=load_countries(service)
        code=countries[flag]["code"]
        # শুধুমাত্র ওই দেশের নাম্বার ফাইল মুছে ফেলা হবে
        delete_numbers_file(service,code)
        await query.edit_message_text(f"✅ Numbers cleared for {flag} ({service})")

    elif data.startswith("delcountry_"):
        flag=data.split("_")[1]
        service=context.user_data.get("admin_service")
        countries=load_countries(service)
        if flag in countries:
            code=countries[flag]["code"]
            # ১. মেইন ডেটাবেজ (JSON) থেকে কান্ট্রি মোছা
            del countries[flag]
            save_countries(service,countries)
            # ২. ওই দেশের নাম্বার ফাইল (TXT) মোছা
            delete_numbers_file(service,code)
            await query.edit_message_text(f"✅ {flag} deleted from {service}")

async def message_handler(update:Update,context:ContextTypes.DEFAULT_TYPE):
    uid=update.effective_user.id
    if not is_admin(uid): return
    step=context.user_data.get("step")
    service=context.user_data.get("admin_service")

    if step=="broadcast":
        for u in allUsers:
            try: await context.bot.send_message(u, update.message.text)
            except: pass
        await update.message.reply_text("Broadcast Done")
        context.user_data.clear()

    elif step=="admin_add_country":
        try:
            flag,name,code=update.message.text.split("|")
            countries=load_countries(service)
            countries[flag]={"name":name,"code":code}
            save_countries(service,countries)
            await update.message.reply_text(f"✅ {name} added to {service}")
        except:
            await update.message.reply_text("❌ Format:\n🇧🇩|Bangladesh|880")
        context.user_data.clear()

    elif step=="upload_numbers" and update.message.document:
        flag = context.user_data.get("addnum_flag")
        countries = load_countries(service)
        code = countries[flag]["code"]
        file = await update.message.document.get_file()
        content = await file.download_as_bytearray()
        numbers = content.decode("utf-8").splitlines()
        append_numbers(service, code, numbers)
        await update.message.reply_text(f"✅ {len(numbers)} numbers added to {flag} ({service})")
        context.user_data.clear()

def main():
    app=Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start",start))
    app.add_handler(CommandHandler("admin",admin))
    app.add_handler(CallbackQueryHandler(button_handler,pattern="^(service_|country_|next|change_country)"))
    app.add_handler(CallbackQueryHandler(admin_buttons))
    app.add_handler(MessageHandler(filters.TEXT & filters.ChatType.GROUPS,otp_group_listener))
    app.add_handler(MessageHandler((filters.TEXT | filters.Document.ALL) & ~filters.COMMAND,message_handler))
    print("✅ Dynamo OTP Bot Running with Folder Structure Support")
    app.run_polling(drop_pending_updates=True)

if __name__=="__main__":
    main()
  
