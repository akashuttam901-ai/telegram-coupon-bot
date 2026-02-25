import re
import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters
)

# ---------------- CONFIG ----------------

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

QR_FILE = "Screenshot_20260224_224442.jpg"

SUPPORT_USERNAME = "@Ark456781"

MAX_UTR_ATTEMPTS = 5

# ---------------- DATA ----------------

coupon_db = {
    "500": {
        "price": 20,
        "coupons": [
            "SVIZS4QPCKD5ZPV",
            "SVIZL4LA9QI5ESI"
        ]
    }
}

pending_orders = {}
utr_attempts = {}
utr_waiting = {}
used_utrs = set()

# ---------------- START ----------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_chat.id

    utr_waiting[user] = False

    text = "⚠ Coupon apne risk par lein\nSabse kam price par available\n\n"

    keyboard = []

    for value, data in coupon_db.items():

        stock = len(data["coupons"])

        text += f"{value} OFF\nPrice ₹{data['price']}\nStock {stock}\n\n"

        if stock > 0:
            keyboard.append([
                InlineKeyboardButton(
                    f"Buy {value}",
                    callback_data=f"buy_{value}"
                )
            ])

    keyboard.append([
        InlineKeyboardButton("Support", url=f"https://t.me/{SUPPORT_USERNAME.replace('@','')}")
    ])

    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ---------------- BUY ----------------

async def buy(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    value = query.data.split("_")[1]

    keyboard = [

        [InlineKeyboardButton("1", callback_data=f"qty_{value}_1")],
        [InlineKeyboardButton("2", callback_data=f"qty_{value}_2")],
        [InlineKeyboardButton("3", callback_data=f"qty_{value}_3")],
        [InlineKeyboardButton("5", callback_data=f"qty_{value}_5")],

        [InlineKeyboardButton("Cancel Order", callback_data="cancel")],

        [InlineKeyboardButton("Support", url=f"https://t.me/{SUPPORT_USERNAME.replace('@','')}")]

    ]

    await query.message.reply_text(
        "Select quantity:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ---------------- QTY ----------------

async def qty(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    _, value, qty = query.data.split("_")

    qty = int(qty)

    total = coupon_db[value]["price"] * qty

    user = query.message.chat_id

    pending_orders[user] = {

        "value": value,
        "qty": qty

    }

    utr_attempts[user] = 0

    await context.bot.send_photo(

        chat_id=user,
        photo=InputFile(QR_FILE),

        caption=f"""
Coupon: {value}
Qty: {qty}
Total: ₹{total}

Pay and press Paid button
""",

        reply_markup=InlineKeyboardMarkup([

            [InlineKeyboardButton("Paid", callback_data="paid")],
            [InlineKeyboardButton("Cancel Order", callback_data="cancel")]

        ])

    )

# ---------------- PAID ----------------

async def paid(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    user = query.message.chat_id

    utr_waiting[user] = True

    await context.bot.send_message(
        user,
        "Send 12 digit UTR"
    )

# ---------------- TEXT ----------------

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.message.chat_id
    text = update.message.text.strip()

    if not utr_waiting.get(user):
        return

    if utr_attempts[user] >= MAX_UTR_ATTEMPTS:

        await update.message.reply_text(
            "Max attempts reached. Contact support."
        )
        return

    utr_attempts[user] += 1

    if not re.fullmatch(r"\d{12}", text):

        await update.message.reply_text(
            f"Invalid UTR\nAttempts left: {MAX_UTR_ATTEMPTS - utr_attempts[user]}"
        )
        return

    if text in used_utrs:

        await update.message.reply_text(
            "UTR already used"
        )
        return

    used_utrs.add(text)

    keyboard = [

        [

            InlineKeyboardButton(
                "Approve",
                callback_data=f"approve_{user}"
            ),

            InlineKeyboardButton(
                "Wrong",
                callback_data=f"wrong_{user}"
            )

        ]

    ]

    await context.bot.send_message(

        ADMIN_ID,

        f"User: {user}\nUTR: {text}",

        reply_markup=InlineKeyboardMarkup(keyboard)

    )

# ---------------- APPROVE ----------------

async def approve(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    user = int(query.data.split("_")[1])

    order = pending_orders[user]

    value = order["value"]
    qty = order["qty"]

    codes = coupon_db[value]["coupons"][:qty]

    coupon_db[value]["coupons"] = coupon_db[value]["coupons"][qty:]

    await context.bot.send_message(

        user,

        "Approved\n\n" + "\n".join(codes)

    )

# ---------------- WRONG ----------------

async def wrong(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    user = int(query.data.split("_")[1])

    await context.bot.send_message(
        user,
        "Wrong UTR. Send again."
    )

# ---------------- CANCEL ----------------

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    user = query.message.chat_id

    pending_orders.pop(user, None)

    await context.bot.send_message(
        user,
        "Order cancelled"
    )

# ---------------- MAIN ----------------

logging.basicConfig(level=logging.INFO)

app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))

app.add_handler(CallbackQueryHandler(buy, pattern="buy_"))
app.add_handler(CallbackQueryHandler(qty, pattern="qty_"))
app.add_handler(CallbackQueryHandler(paid, pattern="paid"))
app.add_handler(CallbackQueryHandler(approve, pattern="approve_"))
app.add_handler(CallbackQueryHandler(wrong, pattern="wrong_"))
app.add_handler(CallbackQueryHandler(cancel, pattern="cancel"))

app.add_handler(MessageHandler(filters.TEXT, text_handler))

print("BOT RUNNING 24/7")

app.run_polling()
