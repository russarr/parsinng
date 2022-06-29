import dotenv
import logging
import pickle
import time

import fake_useragent
from bs4 import BeautifulSoup
from common.exceptions import GetPageSourseException
from requests import Session
from os import getenv
from typing import Literal
import cloudscraper

logger = logging.getLogger(__name__)


def create_auth_session(site_alias: Literal['sol', 'ficbook', None] = None) -> Session:
    match site_alias:
        case 'sol':
            session = create_request_session()
        case 'ficbook':
            session = create_cloudscraper_session()
        case _:
            session = create_request_session()
            return session

    logger.debug('авторизуемся')
    session = _load_cookiejar(session, site_alias=site_alias)
    n = 5
    while not _is_authorized(session, site_alias):
        session = _post_auth_data(session, site_alias)
        n -= 1
        time.sleep(1)
        if n == 0:
            error_message = f'Проблема авторизации {site_alias}'
            logger.error(error_message)
            raise GetPageSourseException(error_message)
    _save_cookiejar(session, site_alias=site_alias)
    return session


def create_request_session() -> Session:
    logger.debug('Создаем сессию')
    user = fake_useragent.UserAgent().random
    header = {'user-agent': user,
              'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
              'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
              'DNT': '1',
              'Upgrade-Insecure-Requests': '1'
              }
    session = Session()
    session.headers.update(header)
    return session


def create_cloudscraper_session() -> Session:
    logger.debug('Создаем cloudscraper сессию')
    # user = fake_useragent.UserAgent().random
    # header = {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:101.0) Gecko/20100101 Firefox/101.0',
    # 'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    # 'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
    # 'DNT': '1',
    # 'Upgrade-Insecure-Requests': '1'
    # }
    session = cloudscraper.create_scraper()
    # session.headers.update(header)
    return session


def _is_authorized(session: Session, site_alias: Literal['sol', 'ficbook']) -> bool:
    logger.debug('Проверяем если уже авторизованы')
    match site_alias:
        case 'sol':
            response = session.get('https://storiesonline.net')
            soup = BeautifulSoup(response.text, 'html5lib')
            test_auth = soup.find('a', title="Private Messages")
        case 'ficbook':
            response = session.get('https://ficbook.net')
            soup = BeautifulSoup(response.text, 'html5lib')
            test_auth = soup.find('img', alt="russarr")
        case _:
            error_message = f'Не верный site_alias {site_alias}'
            logger.error(error_message)
            raise GetPageSourseException
    if test_auth:
        logger.debug('Есть авторизация')
    return True if test_auth else False


def _post_auth_data(session: Session, site_alias: Literal['sol', 'ficbook']) -> Session:
    match site_alias:
        case 'sol':
            auth_data = _create_auth_data(site_alias='sol')
            session = _post_sol_auth_data(session, auth_data)
        case 'ficbook':
            auth_data = _create_auth_data(site_alias='ficbook')
            session = _post_ficbook_auth_data(auth_data)
        case _:
            error_message = f'Не верный site_alias {site_alias}'
            logger.error(error_message)
            raise GetPageSourseException
    return session


def _post_sol_auth_data(session: Session, auth_data: dict[str, str]) -> Session:
    logger.debug('Отправляем данные для авторизации')
    login_url = 'https://login.wlpc.com/?cmd=t&sid=1'
    transfer_url = 'https://login.wlpc.com/transfer.php?sid=1'
    session.post(login_url, data=auth_data)
    session.headers.update({
        "Location": "/account.php",
        'Referer': 'https://login.wlpc.com/account.php',
    })
    time.sleep(2)
    session.get(transfer_url, allow_redirects=True)
    return session


def _post_ficbook_auth_data(auth_data: dict[str, str]) -> Session:
    login_url = 'https://ficbook.net/login_check'
    session = cloudscraper.create_scraper()
    session.post(login_url, data=auth_data)
    return session


def _create_auth_data(site_alias: Literal['sol', 'ficbook']) -> dict[str, str]:
    match site_alias:
        case 'sol':
            auth_data = _create_sol_auth_data()
        case 'ficbook':
            auth_data = _create_ficbook_auth_data()
        case _:
            error_message = f'Не могу создать словарь данных для авторизации {site_alias}'
            logger.error(error_message)
            raise GetPageSourseException
    return auth_data


def _create_sol_auth_data() -> dict[str, str]:
    login, password = _load_auth_data_from_env(site_alias='sol')
    data = {"email": login,
            "password": password,
            "cmd": "LOGIN"}
    return data


def _create_ficbook_auth_data() -> dict[str, str]:
    login, password = _load_auth_data_from_env(site_alias='ficbook')
    data = {
        "login": login,
        "password": password,
        "remember": 'on'
    }
    return data


def _load_auth_data_from_env(site_alias: Literal['sol', 'ficbook']) -> tuple[str, str]:
    match site_alias:
        case 'sol':
            login_name, password_name = 'SOL_LOGIN', 'SOL_PASSWORD'
        case 'ficbook':
            login_name, password_name = 'FICBOOK_LOGIN', 'FICBOOK_PASSWORD'
        case _:
            error_message = f'site_alias некорректный {site_alias}'
            logger.error(error_message)
            raise GetPageSourseException

    dotenv.load_dotenv('utils/.env')
    logger.debug('загружаем данные авторизации')
    login = getenv(login_name, default='')
    password = getenv(password_name, default='')
    logger.debug(f'{login=}, {password=}')
    if all([login and isinstance(login, str), password and isinstance(password, str)]):
        return login, password
    else:
        error_message = 'Не могу загрузить login, password из переменных окружения'
        logger.error(error_message)
        raise GetPageSourseException(error_message)


def _load_cookiejar(session: Session, site_alias: Literal['sol', 'ficbook']) -> Session:
    cookie_file_name = f'temp/cookies_{site_alias}.pickle'
    logger.debug(f'Грузим cookies {site_alias}')
    try:
        with open(cookie_file_name, 'rb') as file:
            cookies = pickle.load(file)
            session.cookies.update(cookies)
            logger.debug(f'cookie {site_alias}загружены')
    except FileNotFoundError:
        logger.info(f'Нет файла с cookie {site_alias}')
        return session
    return session


def _save_cookiejar(session: Session, site_alias: Literal['sol', 'ficbook']) -> None:
    cookie_file_name = f'temp/cookies_{site_alias}.pickle'
    try:
        with open(cookie_file_name, 'wb') as file:
            pickle.dump(session.cookies, file)
            logger.debug(f'cookies {site_alias} сохранены')
    except FileNotFoundError:
        error_message = f'Не могу сохранить cookies {site_alias}'
        logger.error(error_message)
        raise GetPageSourseException(error_message)
