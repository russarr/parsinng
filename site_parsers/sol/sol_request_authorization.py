import time

from requests import Session
import fake_useragent  # type: ignore
import pickle
from bs4 import BeautifulSoup
import dotenv
from os import getenv
from common.exceptions import GetPageSourseException  # type: ignore
import logging
from common.utils import raise_exception  # type: ignore

logger = logging.getLogger(__name__)


class SolBookRequests:
    def create_sol_requests_session(self) -> Session:
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
        session = self._sol_authorsation(session)
        return session

    def _sol_authorsation(self, session: Session) -> Session:
        logger.debug('авторизуемся')
        session = self._load_sol_cookiejar(session)
        n = 5
        while not self._is_authorizid(session):
            session = self._send_sol_auth_data(session)
            n -= 1
            time.sleep(1)
            if n == 0:
                raise_exception(GetPageSourseException, 'Проблема авторизации sol')
        self._save_sol_cookiejar(session)
        return session

    def _send_sol_auth_data(self, session: Session) -> Session:
        logger.debug('Отправляем данные для авторизации')
        data = self._get_auth_data()
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

    @staticmethod
    def _is_authorizid(session: Session) -> bool:
        logger.debug('Проверяем если уже авторизованы')
        response = session.get('https://storiesonline.net')
        soup = BeautifulSoup(response.text, 'html5lib')
        test_auth = soup.find('a', title="Private Messages")
        if test_auth:
            logger.debug('Есть авторизация')
        return True if test_auth else False

    @staticmethod
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

    @staticmethod
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

    @staticmethod
    def _save_sol_cookiejar(session: Session) -> None:
        try:
            with open('temp/cookies_requests.pickle', 'wb') as file:
                pickle.dump(session.cookies, file)
        except FileNotFoundError:
            raise_exception(GetPageSourseException, 'Не могу сохранить cookies')
