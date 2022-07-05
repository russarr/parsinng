import logging
import pickle
import sqlite3 as sq
from datetime import timedelta
from pathlib import Path

import isodate
import requests
from bs4 import BeautifulSoup
from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build as youtube_build_session
from tqdm import tqdm

from common.exceptions import GetPageSourseException
from common.utils import create_soup
from common.utils import send_telegram_message

logger = logging.getLogger(__name__)


def form_rss_list(id_lst: list) -> list[str]:
    """ Функция формирует список rss-каналов"""
    rss_lst = []
    for channel in id_lst:
        rss_url = f'https://www.youtube.com/feeds/videos.xml?channel_id={channel}'
        rss_lst.append(rss_url)
    return rss_lst


def get_subscription_ids(resp: dict, id_lst: list[str] | None = None) -> list[str]:
    logger.debug('Извлекаем список id каналов из текущей страницы')
    if id_lst is None:
        id_lst = []
    for item in resp['items']:
        channel_id = item['snippet']['resourceId']['channelId']
        id_lst.append(channel_id)
    return id_lst


def get_video_duration(youtube_session: youtube_build_session, video_id: str) -> str:
    request = youtube_session.videos().list(part='contentDetails', id=video_id)
    response = request.execute()['items'][0]['contentDetails']['duration']
    duration = isodate.parse_duration(response)
    duration = timedelta(seconds=duration.total_seconds())
    return str(duration)


def _create_channel_id_list(youtube_session: Credentials) -> list[str]:
    logger.debug('Получаем первый лист с youtube подписками')
    request = youtube_session.subscriptions().list(part='snippet',
                                                   mine=True,  # авторизация по моему аккаунту
                                                   maxResults=10,
                                                   order='alphabetical'
                                                   )
    response = request.execute()
    id_list = get_subscription_ids(response)

    # в цикле перебираем следующие страницы
    while request:
        logger.debug('Получаем следующий лист с youtube подписками')
        request = youtube_session.subscriptions().list_next(request, response)
        if request is None:  # почему то while не прерывается при None, поэтому добавил break
            break
        response = request.execute()

        id_list += get_subscription_ids(response)
    return id_list


def _process_videos(id_list: list[str], youtube_session: youtube_build_session) -> None:
    try:
        with open('temp/rss.pickle', 'rb') as f:
            entries_current = pickle.load(f)  # загружаем список всех постов, что идут на rss ленту
    except (EOFError, FileNotFoundError):
        entries_current = []
    print('Загрузили с диска', len(entries_current))

    # проходимся по всем лентам, разбиваем на блоки, и если отсутсвует в общем списке записываем
    for channel_id in tqdm(id_list, desc='YouTube channels:', colour='blue'):
        rss_posts = _get_rss_posts(channel_id)
        with sq.connect('book_database/rss_entries.db') as rss_db:
            cur = rss_db.cursor()
            for rss_post in rss_posts:
                video_link = BeautifulSoup(rss_post, 'lxml').find('link').get('href')  # type: ignore # извлекаем ссылку на видео
                video_id = video_link.split('v=')[-1]  # type: ignore # получаем id видео из ссылки
                author = BeautifulSoup(rss_post, 'lxml').find('name').text  # type: ignore
                cur.execute("""SELECT rss_entry FROM rss_all WHERE rss_entry = ?""", (video_link,))
                if cur.fetchone() is None:
                    video_duration = get_video_duration(youtube_session, video_id)
                    cur.execute("""INSERT INTO rss_all VALUES (?)""", (video_link,))
                    message = f'{author}\nДлительность:{video_duration}\n{video_link}\n'
                    print(message)
                    send_telegram_message('youtube_chat', message)
                    entries_current.insert(0, rss_post)
    if len(entries_current) > 100:
        entries_current = entries_current[:100]

    with open('temp/rss.pickle', 'wb') as f:
        pickle.dump(entries_current, f)


def _get_rss_posts(channel_id: str) -> list[str]:
    logger.debug('Получаем rss-ленту из по id канала')
    rss_url = f'https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}'
    response = requests.get(rss_url, timeout=3)  # получаем ленту
    if response.status_code == 200:
        soup = create_soup(response.text)
        rss_posts_tags = soup.findAll('entry')  # разделяем ленту на посты
        if rss_posts_tags:
            rss_posts = [str(post) for post in rss_posts_tags]
            return rss_posts
        else:
            error_message = f'rss-лента канала {channel_id=} пуста'
            logger.error(error_message)
            raise GetPageSourseException(error_message)
    else:
        error_message = f'Ошибка получения rss-ленты канала {channel_id=}'
        logger.error(error_message)
        raise GetPageSourseException(error_message)


def _get_valid_token() -> Credentials:
    session_token = _load_youtube_session_token()
    if session_token is None:# or not session_token.valid:
        logger.debug('Токен сессии отсутствует или не действующий -  создаем новый')
        session_token = _create_youtube_session_token()
    elif _is_token_expired(session_token):
        session_token = _refresh_token(session_token)
    else:
        pass
    _save_youtube_session_token(session_token)
    return session_token


def _load_youtube_session_token() -> Credentials | None:
    logger.debug('Создаем youtube сессию')
    # загружаем сохраненный токен авторизации google
    logger.debug('грузим токен с диска')
    token_path = Path('temp/youtube_token.pickle')
    if token_path.exists():  # проверяем наличие файла temp/youtobe_token.pickle в текущей директории
        with open(token_path, 'rb') as token:
            session_token: Credentials | None = pickle.load(token)
            logger.debug('Токен загружен')
    else:
        logger.debug('Токена на диске нет')
        session_token = None
    return session_token


def _save_youtube_session_token(session_token: Credentials) -> None:
    token_path = Path('temp/youtube_token.pickle')
    with open(token_path, 'wb') as f:
        logger.debug('Сохраняем токен на диск')
        pickle.dump(session_token, f)


def _create_youtube_session_token() -> Credentials:
    logger.debug('Получаем токен авторизации google')
    try:
        flow = InstalledAppFlow.from_client_secrets_file('temp/client_secret.json',
                                                         scopes=['https://www.googleapis.com/auth/youtube.readonly']  # разрешения доступа
                                                         )
        flow.run_local_server()
        session_token = flow.credentials
        return session_token
    except FileNotFoundError:
        error_message = 'Проблемы загрузки client_secret.json'
        logger.exception(error_message)
        raise GetPageSourseException(error_message)


def _is_token_expired(session_token: Credentials) -> bool:
    if all((session_token is not None, session_token.expired, session_token.refresh_token)):
        logger.debug('Срок действия токена истек и есть возможность обновления. Обновляем')
        return True
    else:
        logger.debug('Токен действующий')
        return False


def _refresh_token(session_token: Credentials) -> Credentials:
    logger.debug('Обновляем токен')
    try:
        session_token.refresh(Request())
    except RefreshError:
        logger.exception('Не получилось обновить токен. Создаем новый')
        session_token = _create_youtube_session_token()
    return session_token


def _create_youtube_session(session_token: Credentials) -> youtube_build_session:
    youtube_session = youtube_build_session('youtube', 'v3', credentials=session_token)
    return youtube_session


def check_youtube_rss() -> None:
    session_token = _get_valid_token()
    youtube_session = _create_youtube_session(session_token)
    id_list = _create_channel_id_list(youtube_session)
    _process_videos(id_list, youtube_session)
