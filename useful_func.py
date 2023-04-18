import json
import requests
from bs4 import BeautifulSoup

from config import APIKEY_GEO, URL_GEO

towns_exceptions = ["Йошкар-Ола", 'Каменск-Уральский', 'Комсомольск-на-Амуре', 'Орехово-Зуево',
                    'Петропавловск-Камчатский', 'Ростов-на-Дону', 'Санкт-Петербург', 'Улан-Удэ',
                    'Ханты-Мансийск', 'Южно-Сахалинск']


def print_guessed_letters(context):
    letters = context.user_data["guessed_letters"]
    guessed_town = context.user_data["guessed_town"]
    out = []
    for val in guessed_town:
        if val.lower() in letters:
            out += guessed_town[guessed_town.index(val)]
            guessed_town = list(''.join(guessed_town).replace(val, '*', 1))
        elif val == ' ' or val == '-':
            out += ' '
        else:
            out += '_'
    if ' ' in out:
        return ' '.join([i.capitalize() for i in ''.join(out).split(' ')])
    return out


def get_desc_of_town(town):
    with open('Cyrillic2Latin.json', encoding='utf8') as f:
        if '-' in town and town not in towns_exceptions:
            Latin_town = json.load(f).get(' '.join([i.capitalize() for i in town.split('-')]))
        else:
            if len(town.split(' ')) > 1 and town.split(' ')[1]:
                town = ' '.join([i.capitalize() for i in town.split(' ')])
            Latin_town = json.load(f).get(town)
        url = f"https://wikiway.com/russia/{Latin_town.lower().replace(' ', '-')}/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36"}
    r = requests.get(url=url, headers=headers).content
    soup = BeautifulSoup(r, 'lxml')
    try:
        main_moments = soup.find(class_='element-publ').find('p').text
    except Exception:
        main_moments = 'К сожалению статьи не будет'
    return [main_moments, url]


def few_facts_abt_town(town):
    if '-' in town and town not in towns_exceptions:
        town = ' '.join([i.capitalize() for i in town.split('-')])
    elif len(town.split(' ')) > 1 and town.split(' ')[1]:
        town = ' '.join([i.capitalize() for i in town.split(' ')])
    out = ''
    params = {
        "geocode": town,
        "apikey": APIKEY_GEO,
        "format": "json",
        "lang": "ru_RU"
    }
    r = requests.get(url=URL_GEO, params=params).json()
    out += f'Название - <b>{town}</b>\n'
    with open('town2population.json', encoding='utf8') as file:
        population = json.load(file).get(town)
        out += f"Население - <b>{population}</b>\n"
    adm_area_name = r["response"]["GeoObjectCollection"]["featureMember"][0]["GeoObject"]
    adm_area_name = adm_area_name["metaDataProperty"]["GeocoderMetaData"]["AddressDetails"]
    adm_area_name = adm_area_name["Country"]["AdministrativeArea"]["AdministrativeAreaName"]
    out += f'Административный округ - <b>{adm_area_name}</b>\n'
    main_moments, url = get_desc_of_town(town)
    if main_moments != 'К сожалению статьи не будет':
        out += f'\n<b>Небольшая статья</b>\n\n{main_moments}\n\n'
        out += f'Больше можно узнать по ссылке <b>{url}</b>'
    return out
