from telegram.ext import Application, CommandHandler, ConversationHandler, MessageHandler, filters
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
import logging

from config import BOT_TOKEN

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG
)

logger = logging.getLogger(__name__)

LAUNCH_DIALOG, START_GAME, EXIT_GAME = range(3)

towns = []


async def start(update, context):
    user = update.effective_user
    keyboard = [['ДА', 'Нет']]
    markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_html(
        rf"Привет {user.mention_html()}! Я игровой тг бот. Не хочешь сыграть в <b>Угадай город?</b>",
        reply_markup=markup
    )
    return LAUNCH_DIALOG


async def launch(update: Update, context):
    if update.message.text == 'ДА':
        await update.message.reply_text('Хорошо, сыграем! Я загадал попробуй угадать!',
                                        reply_markup=ReplyKeyboardRemove())
        return START_GAME
    elif update.message.text == 'НЕТ':
        await update.message.reply_text('Жаль. До скорой встречи!',
                                        reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END
    await update.message.reply_text('Я тебя не понял. Повтори пожалуйста')
    return LAUNCH_DIALOG


async def game(update: Update, context):
    await update.message.reply_text('Заглушка')


async def bye(update: Update, context):
    await update.message.reply_text('Спасибо за игру! Жду снова!')
    return ConversationHandler.END


if __name__ == '__main__':
    app = Application.builder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            LAUNCH_DIALOG: [MessageHandler(filters.TEXT & ~filters.COMMAND, launch)],
            START_GAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, game),
                         CommandHandler('stop', bye)]
        },
        fallbacks=[CommandHandler('stop', bye)]
    )

    app.add_handler(conv_handler)

    app.run_polling()
