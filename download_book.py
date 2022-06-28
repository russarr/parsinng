import clipboard

from common.exceptions import CompileException, DataBaseExceptions, ParsingException, GetPageSourseException
from common.utils import parse_book_url
from site_parsers.sol.sol_book import SolBook
from site_parsers.sfsb.sf_sb_book import SfSbBook
import logging.config
import logging
from requests import Session

from settings.settings import LOGGING_CONFIG

logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger(__name__)


def main() -> None:
    logger.debug('Начинаем загрузку книги')
    choose_book_class = {'https://forums.sufficientvelocity.com': SfSbBook,
                         'https://forums.spacebattles.com': SfSbBook,
                         'https://storiesonline.net': SolBook
                         }
    book_url = clipboard.paste()
    site_name, book_link, book_class = parse_book_url(book_url, choose_book_class)
    book = book_class(site_name, book_link)
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
