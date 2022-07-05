import os
from logging import Handler, LogRecord

import dotenv

from common.utils import send_telegram_message

modules = (('__main__', 'DEBUG'),
           ('site_parsers.sol.sol_book', 'INFO'),
           ('site_parsers.sol.sol_requests_soup', 'INFO'),
           ('db_modules.db_common', 'INFO'),
           ('epub.epub', 'INFO'),
           ('site_parsers.sol.sol_monitoring', 'INFO'),
           ('site_parsers.sfsb.sf_sb_book', 'INFO'),
           ('site_parsers.sfsb.sf_sb_monitoring', 'INFO'),
           ('site_parsers.ficbook.ficbook_book', 'INFO'),
           ('site_parsers.ficbook.ficbook_monitoring', 'INFO'),
           ('site_parsers.archiveofourown.aooo', 'INFO'),
           ('site_parsers.archiveofourown.aooo_monitoring', 'INFO'),
           ('site_parsers.youtube.youtube', 'INFO'),
           ('common.utils', 'INFO'),
           ('common.common', 'INFO'),
           ('common.request_authorization', 'INFO'),
           ('download_book', 'INFO'),
           ('monitoring', 'INFO')
           )
loggers = {}
for logger in modules:
    loggers[logger[0]] = {
        'handlers': ['console_handler', 'file_handler', 'telegram_handler'],
        'level': logger[1],
        'propagate': False}

formatters = {
    'file_formatter': {
        'format': '[{levelname}: {asctime}] [{filename}:{funcName}:{lineno}]: "{message}"',
        'style': '{'
    },
    'debug_formatter': {
        'format': '[{levelname}] [{filename}:{funcName}:{lineno}]: "{message}"',
        'style': '{'
    },
    'telegram_formatter': {
        'format': '{message}',
        'style': '{'
    }
}

dotenv.load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')


class TelegramBotHandler(Handler):
    def __init__(self, token: str, chat_id: str):
        super().__init__()
        self.token = token
        self.chat_id = chat_id

    def emit(self, record: LogRecord) -> None:
        send_telegram_message(channel_name='common', text=self.format(record))


handlers = {
    'console_handler': {
        'class': 'logging.StreamHandler',
        'level': 'DEBUG',
        'formatter': 'debug_formatter',
        'stream': 'ext://sys.stdout',  # Default is stderr
    },
    'file_handler': {
        'class': 'logging.FileHandler',
        'level': 'INFO',
        'formatter': 'file_formatter',
        'filename': 'temp/logs/debug.log',
        'mode': 'a',  # default 'a'
        'encoding': 'utf-8'
    },
    'telegram_handler': {
        'class': 'settings.settings.TelegramBotHandler',
        'level': 'INFO',
        'token': TELEGRAM_BOT_TOKEN,
        'chat_id': TELEGRAM_CHAT_ID
    }
}

LOGGING_CONFIG = {
    'version': 1,
    'formatters': formatters,
    'handlers': handlers,
    'loggers': loggers
}
