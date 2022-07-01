import logging
import pickle
import time
from os import getenv

import bs4
import cloudscraper
import dotenv
import fake_useragent
from bs4 import BeautifulSoup
from requests import Session
from requests.adapters import HTTPAdapter, Retry

from common.exceptions import GetPageSourseException
from common.project_types import site_alias_list
from common.utils import create_soup

logger = logging.getLogger(__name__)
DEFAULT_TIMEOUT = 5  # seconds


# Переопределяем класс HTTPAdapter для возможности выствления timeout по дефолту вместо None, и настройки количества попыток
class TimeoutHTTPAdapter(HTTPAdapter):
    def __init__(self, *args, **kwargs):  # type: ignore
        self.timeout = DEFAULT_TIMEOUT
        if "timeout" in kwargs:
            self.timeout = kwargs["timeout"]
            del kwargs["timeout"]
        super().__init__(*args, **kwargs)

    def send(self, request, **kwargs):  # type: ignore
        timeout = kwargs.get("timeout")
        if timeout is None:
            kwargs["timeout"] = self.timeout
        return super().send(request, **kwargs)


retries = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
adapter = TimeoutHTTPAdapter(timeout=5, max_retries=retries)


def create_auth_session(site_alias: site_alias_list = None) -> Session:
    match site_alias:
        case 'sol':
            session = create_request_session()
        case 'ficbook':
            session = create_cloudscraper_session()
        case 'aooo':
            session = create_request_session()
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
    session.mount("https://", adapter)
    session.mount("http://", adapter)
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
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    # session.headers.update(header)
    return session


def _is_authorized(session: Session, site_alias: site_alias_list) -> bool:
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
        case 'aooo':
            response = session.get('https://archiveofourown.org/')
            soup = BeautifulSoup(response.text, 'html5lib')
            test_auth = soup.find('a', href="/users/logout")
        case _:
            error_message = f'Не верный site_alias {site_alias}'
            logger.error(error_message)
            raise GetPageSourseException
    if test_auth:
        logger.debug('Есть авторизация')
    return True if test_auth else False


def _post_auth_data(session: Session, site_alias: site_alias_list) -> Session:
    match site_alias:
        case 'sol':
            auth_data = _create_auth_data(site_alias='sol', session=session)
            session = _post_sol_auth_data(session, auth_data)
        case 'ficbook':
            auth_data = _create_auth_data(site_alias='ficbook', session=session)
            session = _post_ficbook_auth_data(auth_data)
        case 'aooo':
            auth_data = _create_auth_data(site_alias='aooo', session=session)
            session = _post_aooo_auth_data(session, auth_data)
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


def _post_aooo_auth_data(session: Session, auth_data: dict[str, str]) -> Session:
    logger.debug('Отправляем данные для авторизации')
    login_url = 'https://archiveofourown.org/users/login'
    session.post(login_url, data=auth_data)
    # session.headers.update({
    #     "Location": "/account.php",
    #     'Referer': 'https://login.wlpc.com/account.php',
    # })
    return session


def _post_ficbook_auth_data(auth_data: dict[str, str]) -> Session:
    login_url = 'https://ficbook.net/login_check'
    session = cloudscraper.create_scraper()
    session.post(login_url, data=auth_data)
    return session


def _create_auth_data(site_alias: site_alias_list, session: Session) -> dict[str, str]:
    match site_alias:
        case 'sol':
            auth_data = _create_sol_auth_data()
        case 'ficbook':
            auth_data = _create_ficbook_auth_data()
        case 'aooo':
            auth_data = _create_aooo_auth_data(session)
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


def _create_aooo_auth_data(session: Session) -> dict[str, str]:
    login, password = _load_auth_data_from_env(site_alias='aooo')
    token = _get_aooo_auth_token(session)
    data = {
        "authenticity_token": token,
        "user[login]": login,
        "user[password]": password,
        "user[remember_me]": '1',
        "commit": "Log+In"
    }
    return data


def _get_aooo_auth_token(session: Session) -> str:
    logger.debug('Получаем токен авторизации archiveofourown.org')
    response = session.get('https://archiveofourown.org/users/login')
    error_message = 'Ошибка получения токена авторизации на aooo'
    if response.status_code == 200:
        soup = create_soup(response.text)
        token_tag = soup.select_one('meta[name="csrf-token"]')
        if isinstance(token_tag, bs4.Tag):
            token = token_tag.get('content')
            if isinstance(token, str):
                logger.debug(f'{token=}')
                return token
            else:
                logger.error(error_message)
                raise GetPageSourseException(error_message)
        else:
            logger.error(error_message)
            raise GetPageSourseException(error_message)
    else:
        logger.error(error_message)
        raise GetPageSourseException(error_message)


def _load_auth_data_from_env(site_alias: site_alias_list) -> tuple[str, str]:
    match site_alias:
        case 'sol':
            login_name, password_name = 'SOL_LOGIN', 'SOL_PASSWORD'
        case 'ficbook':
            login_name, password_name = 'FICBOOK_LOGIN', 'FICBOOK_PASSWORD'
        case 'aooo':
            login_name, password_name = 'AOOO_LOGIN', 'AOOO_PASSWORD'
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


def _load_cookiejar(session: Session, site_alias: site_alias_list) -> Session:
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


def _save_cookiejar(session: Session, site_alias: site_alias_list) -> None:
    cookie_file_name = f'temp/cookies_{site_alias}.pickle'
    try:
        with open(cookie_file_name, 'wb') as file:
            pickle.dump(session.cookies, file)
            logger.debug(f'cookies {site_alias} сохранены')
    except FileNotFoundError:
        error_message = f'Не могу сохранить cookies {site_alias}'
        logger.error(error_message)
        raise GetPageSourseException(error_message)
