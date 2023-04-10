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


def standart(toponym):
    return toponym.replace('ё', 'е').lower()


def fix_results(update: Update, context, result):
    sess = create_session()
    user = sess.query(User).filter(User.user_id == update.effective_user.id).first()
    if user is None:
        user = User()
        user.user_id = update.effective_user.id
        sess.add(user)
        sess.commit()
        user = sess.query(User).filter(User.user_id == update.effective_user.id).first()
    if result == 'WIN':
        user.wins = user.wins + 1
    elif result == 'LOSE':
        user.loses += 1
    if context.user_data.get('attempts', 0) != 0:
        user.last_attempts = context.user_data['attempts']
        user.min_attempts = min(user.min_attempts, context.user_data['attempts'])
        user.most_attempts = max(user.most_attempts, context.user_data['attempts'])
        user.attempts += context.user_data['attempts']
    sess.commit()
    context.user_data.clear()


async def start(update, context):
    user = update.effective_user
    keyboard = [['ДА', 'НЕТ']]
    markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_html(
        f"Привет {user.mention_html()}! Я игровой тг бот. Не хочешь сыграть в <b>"
        f"Угадай город/страну?</b>",
        reply_markup=markup
    )
    return LAUNCH_DIALOG


async def help_(update: Update, context):
    await update.message.reply_html('<b>/start - Начало игры</b>\n'
                                    '<b>/stats - Статистика игрока</b>\n')


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
    context.user_data["attempts"] = context.user_data.get("attempts", 0) + 1

    if standart(update.message.text) == context.user_data["guessed_town"]:
        await update.message.reply_html(f'Молодец! Ты угадал! Загаданный город - '
                                        f'<b> {context.user_data["guessed_town"]}'
                                        f'Хотите сыграть еще раз?</b>',
                                        reply_markup=ReplyKeyboardMarkup([['ДА', 'НЕТ']],
                                                                         resize_keyboard=True,
                                                                         one_time_keyboard=True))
        fix_results(update, context, 'WIN')
        return LAUNCH_DIALOG
    else:
        await update.message.reply_text('К сожалению, это неправильный ответ. Попробуй еще раз!',
                                        reply_markup=ReplyKeyboardMarkup([['/help', '/stop']]))


async def dev(update: Update, context):
    await update.message.reply_text(context.user_data['guessed_town'])


async def bye(update: Update, context):
    await update.message.reply_text('Жаль, что не смог победить! Спасибо за игру! Жду снова!',
                                    reply_markup=ReplyKeyboardMarkup([['/start', '/help']],
                                                                     resize_keyboard=True))
    fix_results(update, context, "LOSE")
    return ConversationHandler.END


async def statistics(update: Update, context):
    sess = create_session()
    user = sess.query(User).filter(User.user_id == update.effective_user.id).first()
    if user is None:
        user = User()
        user.user_id = update.effective_user.id
        sess.add(user)
        sess.commit()
        user = sess.query(User).filter(User.user_id == update.effective_user.id).first()
    await update.message.reply_html(
        f"<b>Статистика игрока  {update.effective_user.mention_html()}</b>\n"
        f"<b>Победы - {user.wins}</b>\n<b>Поражения - {user.loses}</b>\n"
        f"<b>Наибольшее кол-во попыток для угадывания - {user.most_attempts}</b>\n"
        f"<b>Наименьшее кол-во попыток для угадывания - {user.min_attempts}</b>\n"
        f"<b>Последнее кол-во попыток для угадывания - {user.wins}</b>\n"
        f"<b>Всего попыток - {user.attempts}</b>")


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
    app.add_handler(CommandHandler('dev', dev))
    app.add_handler(CommandHandler('stats', statistics))
    app.add_handler(CommandHandler('help', help_))

    app.run_polling()
