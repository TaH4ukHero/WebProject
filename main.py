import random
from telegram.ext import Application, CommandHandler, ConversationHandler, MessageHandler, filters
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
import logging
from config import BOT_TOKEN
from data.db_session import global_init, create_session
from data.users import User

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG
)

logger = logging.getLogger(__name__)

LAUNCH_DIALOG, START_GAME = range(2)

towns = [i.strip("\n").replace("ё", "е").lower() for i in open('cities.txt', encoding='utf8')]


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
        context.user_data['guessed_town'] = random.choice(towns)
        await update.message.reply_text('Хорошо, сыграем! Я загадал попробуй угадать! Напиши '
                                        'название города',
                                        reply_markup=ReplyKeyboardRemove())
        return START_GAME
    elif update.message.text == 'НЕТ':
        await update.message.reply_text('Жаль. До скорой встречи!',
                                        reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END
    await update.message.reply_text('Я тебя не понял. Повтори пожалуйста')
    return LAUNCH_DIALOG


async def check_town(update: Update, context):
    context.user_data["attemps"] = context.user_data.get("attemps", 0) + 1
    if update.message.text == context.user_data["guessed_town"]:
        await update.message.reply_text(f'Молодец! Ты угадал! Загаданный город - '
                                        f'{context.user_data["guessed_town"]}Спасибо за игру! Жду снова!')
        return ConversationHandler.END
    else:
        await update.message.reply_text('К сожалению, это неправильный ответ. Попробуй еще раз!')


async def bye(update: Update, context):
    await update.message.reply_text('Спасибо за игру! Жду снова!')
    sess = create_session()
    user = sess.query(User).filter(User.user_id == update.effective_user.id)
    user.loses += 1
    sess.commit()
    return ConversationHandler.END


if __name__ == '__main__':
    app = Application.builder().token(BOT_TOKEN).build()

    global_init('db/user.db')

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            LAUNCH_DIALOG: [MessageHandler(filters.TEXT & ~filters.COMMAND, launch)],
            START_GAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, check_town),
                         CommandHandler('stop', bye)]
        },
        fallbacks=[CommandHandler('stop', bye)]
    )

    app.add_handler(conv_handler)

    app.run_polling()
