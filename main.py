import json
import logging
import random
import requests
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, Bot
from telegram.ext import Application, CommandHandler, ConversationHandler, MessageHandler, filters
from config import BOT_TOKEN
from data.db_session import global_init, create_session
from data.users import User
from useful_func import *

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG
)

logger = logging.getLogger(__name__)

LAUNCH_DIALOG, LETTER_OR_TOWN, LETTER, TOWN = range(4)

# towns = [i.strip("\n") for i in open('cities.txt', encoding='utf8')]
towns_exceptions = ["Йошкар-Ола", 'Каменск-Уральский', 'Комсомольск-на-Амуре', 'Орехово-Зуево',
                    'Петропавловск-Камчатский', 'Ростов-на-Дону', 'Санкт-Петербург', 'Улан-Удэ',
                    'Ханты-Мансийск', 'Южно-Сахалинск']
towns = ["Артём"]

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
        if user.min_attempts > 0:
            user.min_attempts = min(user.min_attempts, context.user_data['attempts'])
        else:
            user.min_attempts = context.user_data['attempts']
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
        f"Угадай город?</b>",
        reply_markup=markup
    )
    return LAUNCH_DIALOG


async def help_(update: Update, context):
    await update.message.reply_html('<b>/start - Начало игры</b>\n'
                                    '<b>/stats - Статистика игрока</b>\n')


async def launch(update: Update, context):
    if update.message.text == 'ДА':
        keyboard = ReplyKeyboardMarkup([['Назову букву', 'Назову город целиком']],
                                       one_time_keyboard=True, resize_keyboard=True)
        context.user_data['guessed_town'] = list(random.choice(towns).replace(' ', '-'))
        context.user_data["guessed_letters"] = list()
        await update.message.reply_text('Хорошо, сыграем! Я загадал попробуй угадать! Выбери один '
                                        'из вариантов.',
                                        reply_markup=keyboard)
        return LETTER_OR_TOWN
    elif update.message.text == 'НЕТ':
        await update.message.reply_text('Жаль. До скорой встречи!',
                                        reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END
    await update.message.reply_text('Я тебя не понял. Повтори пожалуйста')
    return LAUNCH_DIALOG


async def letter_or_town(update: Update, context):
    msg = update.message.text
    if msg == 'Назову букву':
        await update.message.reply_html('Хорошо! Называй букву из названия города.\n'
                                        'Угаданные буквы\n'
                                        f'<b>{" ".join(print_guessed_letters(context)).capitalize()}</b>')
        return LETTER
    elif msg == 'Назову город целиком':
        await update.message.reply_text('Хорошо! Называй название города целиком.')
        return TOWN


def win(context):
    keyboard = ReplyKeyboardMarkup([['ДА', 'НЕТ']], resize_keyboard=True, one_time_keyboard=True)
    msg1 = f'Молодец! Ты угадал! Загаданный город - <b> {"".join(context.user_data["guessed_town"])}\nХотите сыграть еще раз?</b>'
    msg2 = few_facts_abt_town(''.join(context.user_data["guessed_town"]))
    return [keyboard, msg1, msg2]


async def check_letter(update: Update, context):
    msg = update.message.text
    context.user_data["attempts"] = context.user_data.get("attempts", 0) + 1
    if msg == 'Назову город целиком':
        await update.message.reply_text('Хорошо! Называй название города целиком.')
        return TOWN
    if len(msg) == 1 and msg.isalpha() and msg.lower() not in context.user_data["guessed_letters"]:
        context.user_data["guessed_letters"].append(msg.lower())
        if " ".join(print_guessed_letters(context)).count('_') == 0:
            # await update.message.reply_html(f'Молодец! Ты угадал! Загаданный город - '
            #                                 f'<b> {"".join(context.user_data["guessed_town"]).capitalize()}\n'
            #                                 f'Хотите сыграть еще раз?</b>',
            #                                 reply_markup=ReplyKeyboardMarkup([['ДА', 'НЕТ']],
            #                                                                  resize_keyboard=True,
            #                                                                  one_time_keyboard=True))
            # await update.message.reply_text(few_facts_abt_town(''.join(context.user_data[
            #                                                                "guessed_town"])))
            win_params = win(context)
            await update.message.reply_html(win_params[1], reply_markup=win_params[0])
            await update.message.reply_html(win_params[2])
            fix_results(update, context, 'WIN')
            return LAUNCH_DIALOG
        if msg.lower() in context.user_data["guessed_town"] or msg in context.user_data[
            "guessed_town"]:
            await update.message.reply_text('Отлично! Эта буква есть в названии.')
    elif len(msg) > 1:
        await update.message.reply_text('Вводи по одной букве!')
    else:
        await update.message.reply_text('Эта буква уже использовалась! Попробуй другую')
    await update.message.reply_html(f'Угаданные буквы\n'
                                    f'<b>{" ".join(print_guessed_letters(context))}</b>')


async def check_town(update: Update, context):
    context.user_data["attempts"] = context.user_data.get("attempts", 0) + 1
    if update.message.text == 'Назову букву':
        await update.message.reply_html('Хорошо! Называй букву из названия города.\n'
                                        'Угаданные буквы\n'
                                        f'<b>{" ".join(print_guessed_letters(context))}</b>')
        return LETTER
    if update.message.text.lower() == ''.join(context.user_data["guessed_town"]).lower().replace(
            '-', ' ') or update.message.text.lower() == ''.join(context.user_data[
            "guessed_town"]).lower():
        # await update.message.reply_html(f'Молодец! Ты угадал! Загаданный город - '
        #                                 f'<b> {"".join(context.user_data["guessed_town"]).capitalize()}\n'
        #                                 f'Хотите сыграть еще раз?</b>',
        #                                 reply_markup=ReplyKeyboardMarkup([['ДА', 'НЕТ']],
        #                                                                  resize_keyboard=True,
        #                                                                  one_time_keyboard=True))
        # await update.message.reply_html(
        #     few_facts_abt_town(''.join(context.user_data["guessed_town"])))
        win_params = win(context)
        await update.message.reply_html(win_params[1], reply_markup=win_params[0])
        await update.message.reply_html(win_params[2])
        fix_results(update, context, 'WIN')
        return LAUNCH_DIALOG
    else:
        await update.message.reply_text('К сожалению, это неправильный ответ. Попробуй еще раз!',
                                        reply_markup=ReplyKeyboardMarkup(
                                            [['Назову букву', 'Назову город целиком']],
                                            one_time_keyboard=True, resize_keyboard=True))


async def dev(update: Update, context):
    await update.message.reply_text(''.join(context.user_data['guessed_town']))


async def bye(update: Update, context):
    await update.message.reply_text('Жаль, что не смог победить! Спасибо за игру! Жду снова!',
                                    reply_markup=ReplyKeyboardMarkup([['/start', '/help']],
                                                                     resize_keyboard=True))
    fix_results(update, context, "LOSE")
    return ConversationHandler.END


async def get_photo(update):
    photo = await bot.get_user_profile_photos(update.effective_user.id)
    photo = photo.photos[0][0]
    file = await bot.get_file(photo.file_id)
    await file.download_to_drive(f'data/photos/{update.effective_user.id}.jpeg')


async def statistics(update: Update, context):
    sess = create_session()
    user = sess.query(User).filter(User.user_id == update.effective_user.id).first()
    if user is None:
        user = User()
        user.user_id = update.effective_user.id
        sess.add(user)
        sess.commit()
        user = sess.query(User).filter(User.user_id == update.effective_user.id).first()
    await get_photo(update)
    await update.message.reply_photo(f'data/photos/{update.effective_user.id}.jpeg')
    await update.message.reply_html(
        f"<b>Статистика игрока  {update.effective_user.mention_html()}</b>\n"
        f"<b>Победы - {user.wins}</b>\n<b>Поражения - {user.loses}</b>\n"
        f"<b>Наибольшее кол-во попыток для угадывания - {user.most_attempts}</b>\n"
        f"<b>Наименьшее кол-во попыток для угадывания - {user.min_attempts}</b>\n"
        f"<b>Последнее кол-во попыток для угадывания - {user.wins}</b>\n"
        f"<b>Всего попыток - {user.attempts}</b>")


if __name__ == '__main__':
    app = Application.builder().token(BOT_TOKEN).build()
    bot = Bot(BOT_TOKEN)

    global_init('db/user.db')

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            LAUNCH_DIALOG: [MessageHandler(filters.TEXT & ~filters.COMMAND, launch)],
            LETTER_OR_TOWN: [MessageHandler(filters.TEXT & ~filters.COMMAND, letter_or_town),
                             CommandHandler('stop', bye)],
            LETTER: [MessageHandler(filters.TEXT & ~filters.COMMAND, check_letter),
                     CommandHandler('stop', bye)],
            TOWN: [MessageHandler(filters.TEXT & ~filters.COMMAND, check_town),
                   CommandHandler('stop', bye)]
        },
        fallbacks=[CommandHandler('stop', bye)]
    )

    app.add_handler(conv_handler)
    app.add_handler(CommandHandler('dev', dev))
    app.add_handler(CommandHandler('stats', statistics))
    app.add_handler(CommandHandler('help', help_))

    app.run_polling()
