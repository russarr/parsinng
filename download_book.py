import logging.config

import clipboard
from requests import Session

from common.exceptions import CompileException, DataBaseExceptions, ParsingException, GetPageSourseException
from common.utils import parse_book_url
from settings.settings import LOGGING_CONFIG
from site_parsers.archiveofourown.aooo import AoooBook
from site_parsers.ficbook.ficbook_book import FicbookBook
from site_parsers.sfsb.sf_sb_book import SfSbBook
from site_parsers.sol.sol_book import SolBook

logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger(__name__)
logging.captureWarnings(True)


def main() -> None:
    logger.debug('Начинаем загрузку книги')
    choose_book_class = {'https://forums.sufficientvelocity.com': SfSbBook,
                         'https://forums.spacebattles.com': SfSbBook,
                         'https://storiesonline.net': SolBook,
                         'https://ficbook.net': FicbookBook,
                         'https://archiveofourown.org': AoooBook
                         }
    book_url = clipboard.paste()
    site_name, book_link, book_class = parse_book_url(book_url, choose_book_class)
    book = book_class(book_link, site_name)
    session = None
    try:
        session = book.downoload_book(session=session, redownload=False)
    except (GetPageSourseException, DataBaseExceptions, ParsingException, CompileException):
        logger.exception('Ошибка запланированная')
    except:
        logger.exception('Незапланированная ошибка')
    finally:
        if isinstance(session, Session):
            session.close()


if __name__ == '__main__':
    main()
