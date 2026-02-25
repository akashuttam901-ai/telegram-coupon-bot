import logging
import os
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, CallbackContext, MessageHandler, Filters

BOT_TOKEN = os.getenv("8271855633:AAEOQ0ymg-NFiXHhIu2QtNC3dL_cWtmTwxQ")
ADMIN_ID = int(os.getenv("7662708655"))

logging.basicConfig(level=logging.INFO)

# store users data
user_data_store = {}

# START
def start(update: Update, context: CallbackContext):

    keyboard = [
        [InlineKeyboardButton("🛒 Buy Coupon", callback_data="buy")],
        [InlineKeyboardButton("📞 Support", callback_data="support")]
    ]

    update.message.reply_text(
        "Welcome to Coupon Bot",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# BUTTON HANDLER
def button(update: Update, context: CallbackContext):

    query = update.callback_query
    query.answer()

    user_id = query.from_user.id

    if query.data == "buy":

        keyboard = [
            [InlineKeyboardButton("1", callback_data="qty_1"),
             InlineKeyboardButton("2", callback_data="qty_2")],
            [InlineKeyboardButton("3", callback_data="qty_3"),
             InlineKeyboardButton("Cancel", callback_data="cancel")]
        ]

        query.message.reply_text(
            "Select quantity:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif query.data.startswith("qty_"):

        qty = query.data.split("_")[1]

        user_data_store[user_id] = {"qty": qty}

        keyboard = [
            [InlineKeyboardButton("✅ Paid", callback_data="paid")],
            [InlineKeyboardButton("❌ Cancel", callback_data="cancel")]
        ]

        query.message.reply_text(
            f"Quantity: {qty}\nClick Paid after payment",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif query.data == "paid":

        keyboard = [
            [InlineKeyboardButton("Approve ✅", callback_data=f"approve_{user_id}")],
            [InlineKeyboardButton("Reject ❌", callback_data=f"reject_{user_id}")]
        ]

        context.bot.send_message(
            ADMIN_ID,
            f"User {user_id} clicked Paid\nApprove?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        query.message.reply_text("Waiting for admin approval")

    elif query.data.startswith("approve_"):

        uid = int(query.data.split("_")[1])

        context.bot.send_message(
            uid,
            "✅ Approved\nYour coupon: SHEIN100"
        )

        query.message.edit_text("Approved and coupon sent")

    elif query.data.startswith("reject_"):

        uid = int(query.data.split("_")[1])

        context.bot.send_message(
            uid,
            "❌ Payment rejected"
        )

        query.message.edit_text("Rejected")

    elif query.data == "support":

        query.message.reply_text(
            "Contact admin: @yourusername"
        )

    elif query.data == "cancel":

        query.message.reply_text(
            "Cancelled"
        )


# ADMIN PANEL
def admin(update: Update, context: CallbackContext):

    if update.message.from_user.id != ADMIN_ID:
        return

    keyboard = [
        [InlineKeyboardButton("Users", callback_data="users")]
    ]

    update.message.reply_text(
        "Admin Panel",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


def main():

    updater = Updater(BOT_TOKEN, use_context=True)

    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("admin", admin))
    dp.add_handler(CallbackQueryHandler(button))

    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main()
