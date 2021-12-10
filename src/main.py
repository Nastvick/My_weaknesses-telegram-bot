import datetime
import logging
import os

from enum import auto, IntEnum

from db import Session
from create_db import create_db
from dotenv import load_dotenv

from telegram import (
    Update,
    ReplyKeyboardMarkup,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ParseMode,
)
from telegram.ext import (
    CallbackContext,
    CommandHandler,
    MessageHandler,
    Filters,
    ConversationHandler,
    Updater,
    CallbackQueryHandler,
    JobQueue,
    Dispatcher,
)

from models import User

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)

PORT = int(os.getenv('PORT', 5001))
TOKEN = os.getenv('TOKEN', 'TOKEN_NOT_PROVIDED')

updater = Updater(token=os.getenv("TOKEN"), use_context=True)
dispatcher = updater.dispatcher


class DescriptionWeakness(IntEnum):
    TITLE = auto()
    DATE = auto()


def start(update: Update, context: CallbackContext):
    telegram_id = update.effective_user.id
    update.message.reply_text("Enter your weakness:")
    with Session() as session:
        existing_user = session.query(User).get(telegram_id)
        if existing_user is None:
            user = User(
                telegram_id=telegram_id,
                username=update.effective_user.username,
                first_name=update.effective_user.first_name,
                last_name=update.effective_user.last_name,
                weakness_start_date=datetime.date.today(),
            )
            session.add(user)
            session.commit()
            update.message.reply_text(
                "You are registered!",
            )
        else:
            update.message.reply_text(
                f"You are already registered, "
                f"{update.effective_user.username if update.effective_user.username is not None else 'Incognito'}! ",
            )

    reply_keyboard = [["/cancel"]]
    update.message.reply_text(
        "Enter your weakness title:",
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard,
            one_time_keyboard=True,
        ),
    )
    return DescriptionWeakness.TITLE


def get_weakness_title(update: Update, context: CallbackContext):
    with Session() as session:
        user = session.query(User).get(update.effective_user.id)
        user.weakness_title = update.message.text
        session.commit()

    reply_keyboard = [["/skip"]]

    update.message.reply_text(
        "Enter start date if any or skip if you want to set automaticaly:",
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard,
            one_time_keyboard=True,
        ),
    )

    return DescriptionWeakness.DATE


def get_weakness_date(update: Update, context: CallbackContext):
    if update.message.text == "/skip":
        return ConversationHandler.END
    else:
        start_date = datetime.datetime.strptime(update.message.text, "%d/%m/%Y").date()

    update.message.reply_text("You have created your weakness!")

    with Session() as session:
        user = session.query(User).get(update.effective_user.id)
        user.weakness_start_date = start_date
        session.commit()

    return ConversationHandler.END


def cancel_creation_weakness(update: Update, context: CallbackContext):
    update.message.reply_text("See you!")

    return ConversationHandler.END


def days(update: Update, context: CallbackContext):
    with Session() as session:
        user = session.query(User).get(update.effective_user.id)
    days_holding = (datetime.date.today() - user.weakness_start_date).days
    update.message.reply_text(f"You are holding on {days_holding} days! Keep going!")


def failed(update: Update, context: CallbackContext):
    with Session() as session:
        user = session.query(User).get(update.effective_user.id)
        user.weakness_start_date = datetime.date.today()
        session.commit()


    update.message.reply_text("Don't give up! You should start over!")

start_conversation_handler = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={
        DescriptionWeakness.TITLE: [
            MessageHandler(Filters.text & ~Filters.command, get_weakness_title)
        ],
        DescriptionWeakness.DATE: [
            MessageHandler(
                Filters.regex("^\d{2}\/\d{2}\/\d{4}$") | Filters.regex("^/skip$"),
                get_weakness_date,
            ),
        ],
    },
    fallbacks=[
        CommandHandler("cancel", cancel_creation_weakness),
    ],
)

def daily(context: CallbackContext):
     with Session() as session:
        for user in session.query(User).filter(User.show_notifications == True):
            days_holding = (datetime.date.today() - user.weakness_start_date).days

            message = f"You are holding on {days_holding} days! Keep going!"

            context.bot.send_message(chat_id=user.telegram_id, text=message)




def start_bot():
    create_db()
    updater = Updater(token=TOKEN, use_context=True)
    dispatcher = updater.dispatcher
    job_queue = updater.job_queue

    dispatcher.add_handler(start_conversation_handler)
    dispatcher.add_handler(CommandHandler("days", days))
    dispatcher.add_handler(CommandHandler("failed", failed))

    job_queue.run_daily(daily, days=tuple(range(7)), time=datetime.time(hour=8, minute=0, second=0))

    logger.info("Starting bot on port %s...", PORT)
    updater.start_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=TOKEN,
        webhook_url=f'https://task-telegram.herokuapp.com/{TOKEN}',
    )

    updater.idle()


if __name__ == '__main__':
    start_bot()


















