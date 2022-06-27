import clipboard
from common.utils import parse_book_url
from site_parsers.sol.sol_book import SolBook
from site_parsers.sfsb.sf_sb_book import SfSbBook
import logging.config
import logging


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
    session = book.downoload_book(redownload=True)
    session.close()


if __name__ == '__main__':
    main()
