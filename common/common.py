import logging
from common.exceptions import GetPageSourseException  # type: ignore
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, NamedTuple

logger = logging.getLogger('logger')


class ChapterLinkName(NamedTuple):
    chapter_link: str
    chapter_name: str
    chapter_order_position: int


@dataclass
class ChapterInfo:
    chapter_file_name: str = ''
    chapter_link: str = ''
    chapter_name: str = ''
    book_link: str = ''
    chapter_updated_date: int = 0
    chapter_posted_date: int = 0


@dataclass()
class BookInfo:
    book_link: str
    site_name: Literal['https://forums.sufficientvelocity.com', 'https://forums.spacebattles.com', 'https://storiesonline.net'] = field(init=False)
    book_title: str = field(repr=False, init=False)
    author_name: str = field(repr=False, init=False)
    author_link: str = field(repr=False, init=False)
    book_directory: Path = field(repr=False, init=False)
    chapters_links: tuple[ChapterLinkName, ...] = field(repr=False, init=False)
    book_size: int = field(repr=False, init=False)
    book_score: float = field(repr=False, init=False)
    chapters_info_list: list[ChapterInfo] = field(default_factory=list)
    book_sex_content: str = field(repr=False, init=False)
    book_posted_date: int = field(repr=False, init=False)
    book_updated_date: int = field(repr=False, init=False)
    book_download_date: int = field(repr=False, init=False)
    book_description: str = field(repr=False, init=False)
    book_genre: str = field(repr=False, init=False)
    book_series: str = field(default='')
    book_tags: tuple[str, ...] = field(repr=False, init=False)
    book_series_order_position: int = field(default=0)
    book_votes_count: int = field(repr=False, init=False)
    book_status: Literal['In progress', 'Concluded', 'Frozen'] = field(repr=False, init=False)
    book_monitoring_status: bool = field(default=False)
