import json
import requests
from config import APIKEY_GEO, URL_GEO


def standart(toponym):
    return list(''.join(toponym).replace('ё', 'е').lower())


def print_guessed_letters(context):
    letters = context.user_data["guessed_letters"]
    guessed_town = standart(context.user_data["guessed_town"])
    out = []
    for val in guessed_town:
        if val in letters:
            out += guessed_town[guessed_town.index(val)]
            guessed_town = list(''.join(guessed_town).replace(val, '*', 1))
        elif val == ' ':
            out += ' '
        else:
            out += '_'
    return out


def few_facts_abt_town(town):
    out = ''
    params = {
        "geocode": town,
        "apikey": APIKEY_GEO,
        "format": "json",
        "lang": "ru_RU"
    }
    r = requests.get(url=URL_GEO, params=params).json()
    out += f'Название - <b>{town.capitalize()}</b>\n'
    with open('town2population.json', encoding='utf8') as file:
        population = json.load(file).get(town.capitalize())
        out += f"Население - <b>{population}</b>\n"
    adm_area_name = r["response"]["GeoObjectCollection"]["featureMember"][0]["GeoObject"]
    adm_area_name = adm_area_name["metaDataProperty"]["GeocoderMetaData"]["AddressDetails"]
    adm_area_name = adm_area_name["Country"]["AdministrativeArea"]["AdministrativeAreaName"]
    out += f'Административный округ - <b>{adm_area_name}</b>'
    return out
