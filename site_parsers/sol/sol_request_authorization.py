import dotenv
import logging
import pickle
import time
from bs4 import BeautifulSoup
from common.exceptions import GetPageSourseException
from common.utils import create_request_session
from requests import Session
from os import getenv

logger = logging.getLogger(__name__)


def create_sol_auth_session() -> Session:
    logger.debug('Авторизуемся на sol')
    session = create_request_session()
    session = _sol_authorsation(session)
    return session


def _sol_authorsation(session: Session) -> Session:
    logger.debug('авторизуемся')
    session = _load_sol_cookiejar(session)
    n = 5
    while not _is_authorizid(session):
        session = _send_sol_auth_data(session)
        n -= 1
        time.sleep(1)
        if n == 0:
            error_message = 'Проблема авторизации sol'
            logger.error(error_message)
            raise GetPageSourseException(error_message)
    _save_sol_cookiejar(session)
    return session


def _send_sol_auth_data(session: Session) -> Session:
    logger.debug('Отправляем данные для авторизации')
    data = _get_auth_data()
    login_url = 'https://login.wlpc.com/?cmd=t&sid=1'
    transfer_url = 'https://login.wlpc.com/transfer.php?sid=1'
    session.post(login_url, data=data)
    # with open('temp/test1.html', 'w', encoding='utf-8') as file:
    #     file.write(r1.text)
    session.headers.update({
        "Location": "/account.php",
        'Referer': 'https://login.wlpc.com/account.php',
    })
    time.sleep(2)
    session.get(transfer_url, allow_redirects=True)
    # with open('temp/test.html', 'w', encoding='utf-8') as file:
    #     file.write(response.text)
    return session


def _is_authorizid(session: Session) -> bool:
    logger.debug('Проверяем если уже авторизованы')
    response = session.get('https://storiesonline.net')
    soup = BeautifulSoup(response.text, 'html5lib')
    test_auth = soup.find('a', title="Private Messages")
    if test_auth:
        logger.debug('Есть авторизация')
    return True if test_auth else False


def _get_auth_data() -> dict[str, str]:
    dotenv.load_dotenv('utils/.env')
    logger.debug('загружаем данные авторизации')
    login = getenv('SOL_LOGIN', default='')
    password = getenv('SOL_PASSWORD', default='')
    if all([login, password]):
        data = {"email": login,
                "password": password,
                "cmd": "LOGIN"}
        return data
    else:
        error_message = 'Не могу загрузить login, password из переменных окружения'
        logger.error(error_message)
        raise GetPageSourseException(error_message)


def _load_sol_cookiejar(session: Session) -> Session:
    logger.debug('Грузим cookies')
    try:
        with open('temp/cookies_requests.pickle', 'rb') as file:
            cookies = pickle.load(file)
            session.cookies.update(cookies)
            logger.debug('cookie загружены')
    except FileNotFoundError:
        logger.info('Нет файла с cookie')
        return session
    return session


def _save_sol_cookiejar(session: Session) -> None:
    try:
        with open('temp/cookies_requests.pickle', 'wb') as file:
            pickle.dump(session.cookies, file)
    except FileNotFoundError:
        error_message = 'Не могу сохранить cookies'
        logger.error(error_message)
        raise GetPageSourseException(error_message)
