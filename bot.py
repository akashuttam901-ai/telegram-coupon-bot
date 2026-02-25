import re
import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ===== SETTINGS =====

BOT_TOKEN = "8271855633:AAEOQ0ymg-NFiXHhIu2QtNC3dL_cWtmTwxQ"
ADMIN_ID = 7662708655

SUPPORT_URL = "https://t.me/Ark456781"

QR_PATH = "qr.jpg"

UTR_FILE = "utrs.txt"

MAX_UTR_ATTEMPTS = 5

# ====================

logging.basicConfig(level=logging.INFO)

coupon_db = {
    "500": {
        "price": 20,
        "coupons": [
            "SVIZS4QPCKD5ZPV",
            "SVIZL4LA9QI5ESI"
        ]
    }
}

pending = {}
utr_wait = {}
utr_attempts = {}
custom_wait = {}
used_utrs = set()

# ===== LOAD UTR =====

if os.path.exists(UTR_FILE):
    with open(UTR_FILE) as f:
        used_utrs = set(line.strip() for line in f)

def save_utr(utr):
    with open(UTR_FILE,"a") as f:
        f.write(utr+"\n")

# ===== START =====

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.message.chat_id

    pending.pop(user,None)
    utr_wait.pop(user,None)

    text="Available Coupons:\n\n"

    keyboard=[]

    for value,data in coupon_db.items():

        stock=len(data["coupons"])

        text+=f"{value} OFF\nPrice ₹{data['price']}\nStock {stock}\n\n"

        if stock>0:

            keyboard.append([
                InlineKeyboardButton(
                    f"Buy {value}",
                    callback_data=f"buy_{value}"
                )
            ])

    keyboard.append([
        InlineKeyboardButton("Support",url=SUPPORT_URL)
    ])

    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ===== BUY =====

async def buy(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query=update.callback_query
    await query.answer()

    value=query.data.split("_")[1]

    keyboard=[

        [
            InlineKeyboardButton("1",callback_data=f"qty_{value}_1"),
            InlineKeyboardButton("2",callback_data=f"qty_{value}_2")
        ],

        [
            InlineKeyboardButton("3",callback_data=f"qty_{value}_3"),
            InlineKeyboardButton("5",callback_data=f"qty_{value}_5")
        ],

        [
            InlineKeyboardButton("Custom",callback_data=f"custom_{value}")
        ],

        [
            InlineKeyboardButton("Cancel",callback_data="cancel")
        ],

        [
            InlineKeyboardButton("Support",url=SUPPORT_URL)
        ]

    ]

    await query.message.reply_text(
        "Select quantity",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ===== PROCESS QTY =====

async def process_qty(user,value,qty,context):

    total=coupon_db[value]["price"]*qty

    pending[user]={
        "value":value,
        "qty":qty
    }

    utr_attempts[user]=0

    with open(QR_PATH,"rb") as photo:

        await context.bot.send_photo(

            user,
            photo,

            caption=f"Pay ₹{total}\nClick Paid after payment",

            reply_markup=InlineKeyboardMarkup([

                [InlineKeyboardButton("Paid",callback_data=f"paid_{user}")],

                [InlineKeyboardButton("Cancel",callback_data="cancel")],

                [InlineKeyboardButton("Support",url=SUPPORT_URL)]

            ])

        )

# ===== QTY =====

async def qty(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query=update.callback_query
    await query.answer()

    value,qty=query.data.split("_")[1:]

    await process_qty(
        query.message.chat_id,
        value,
        int(qty),
        context
    )

# ===== CUSTOM =====

async def custom(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query=update.callback_query
    await query.answer()

    custom_wait[query.message.chat_id]=query.data.split("_")[1]

    await query.message.reply_text("Send quantity")

# ===== PAID =====

async def paid(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query=update.callback_query
    await query.answer()

    user=int(query.data.split("_")[1])

    utr_wait[user]=True

    await context.bot.send_message(
        user,
        "Send 12 digit UTR"
    )

# ===== CANCEL =====

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query=update.callback_query
    await query.answer()

    user=query.message.chat_id

    pending.pop(user,None)

    await query.message.reply_text("Order cancelled")

# ===== TEXT =====

async def text(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user=update.message.chat_id
    msg=update.message.text.strip()

    if user in custom_wait:

        value=custom_wait.pop(user)

        await process_qty(user,value,int(msg),context)

        return

    if not utr_wait.get(user):
        return

    if utr_attempts[user]>=MAX_UTR_ATTEMPTS:

        await update.message.reply_text("Max attempts reached")
        return

    utr_attempts[user]+=1

    if not re.fullmatch(r"\d{12}",msg):

        await update.message.reply_text("Invalid UTR")
        return

    if msg in used_utrs:

        await update.message.reply_text("UTR already used")
        return

    used_utrs.add(msg)
    save_utr(msg)

    keyboard=[[
        InlineKeyboardButton("Approve",callback_data=f"approve_{user}"),
        InlineKeyboardButton("Wrong",callback_data=f"wrong_{user}")
    ]]

    await context.bot.send_message(
        ADMIN_ID,
        f"Payment\nUser:{user}\nUTR:{msg}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ===== APPROVE =====

async def approve(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query=update.callback_query
    await query.answer()

    user=int(query.data.split("_")[1])

    value=pending[user]["value"]
    qty=pending[user]["qty"]

    codes=coupon_db[value]["coupons"][:qty]

    coupon_db[value]["coupons"]=coupon_db[value]["coupons"][qty:]

    await context.bot.send_message(
        user,
        "Approved\n\n"+"\n".join(codes)
    )

# ===== WRONG =====

async def wrong(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query=update.callback_query
    await query.answer()

    user=int(query.data.split("_")[1])

    utr_wait[user]=True

    await context.bot.send_message(
        user,
        "Wrong UTR\nSend again"
    )

# ===== MAIN =====

app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start",start))

app.add_handler(CallbackQueryHandler(buy,pattern="buy_"))
app.add_handler(CallbackQueryHandler(qty,pattern="qty_"))
app.add_handler(CallbackQueryHandler(custom,pattern="custom_"))
app.add_handler(CallbackQueryHandler(paid,pattern="paid_"))
app.add_handler(CallbackQueryHandler(cancel,pattern="cancel"))
app.add_handler(CallbackQueryHandler(approve,pattern="approve_"))
app.add_handler(CallbackQueryHandler(wrong,pattern="wrong_"))

app.add_handler(MessageHandler(filters.TEXT,text))

print("BOT RUNNING ON RENDER")

app.run_polling()
