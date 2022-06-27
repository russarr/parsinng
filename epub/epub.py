import zipfile
from pathlib import Path
from datetime import datetime
from common.exceptions import CompileException
from common.project_types import BookInfo
import logging
from common.utils import form_acceptable_name

logger = logging.getLogger(__name__)


class BookEpub(BookInfo):

    def compile_epub_file(self) -> None:
        """Компилируем и сохраняем книгу в epub"""
        logger.debug('Компилируем epub-файл')
        file_name = self._create_file_name()
        save_path = Path('C:\\Users\\Necros\\YandexDisk\\books')
        save_path = save_path.joinpath(file_name)
        chapters_data = self._create_chapters_data()
        content_file, toc_file = self._create_content_and_toc_data()
        title_page = self._create_title_page()
        meta_inf_data = self._create_meta_inf_data()
        images_files = self._get_images()
        logger.debug('Записываем zip-архив')
        try:
            with zipfile.ZipFile(save_path, mode='w') as zf:
                zf.writestr('OEBPS/content.opf', content_file)
                zf.writestr('OEBPS/toc.ncx', toc_file)
                zf.writestr('META-INF/container.xml', meta_inf_data)
                zf.writestr('mimetype', 'application/epub+zip')
                zf.writestr('OEBPS/Text/titlepage.html', title_page)
                for chapter in chapters_data:
                    zf.writestr('OEBPS/Text/' + chapter[0], chapter[1])
                for image in images_files:
                    zf.write(image[1], 'OEBPS/Images/' + image[0])
                logger.info(f'Сохранена книга {save_path}')
        except OSError as e:
            error_message = f'Ошибка при архивации epub файла: {e}'
            raise CompileException(error_message)

    def _create_file_name(self) -> str:
        file_name = self.author_name + ' - ' + self.book_title
        file_name = form_acceptable_name(file_name, file_name_length=75)
        file_name = file_name + '.epub'
        logger.debug(f'Имя книги {file_name=}')
        return file_name

    def _create_content_and_toc_data(self) -> tuple[str, str]:
        xml_version = '<?xml version="1.0" encoding="utf-8"?>\n'
        package_start = '<package version="2.0" unique-identifier="BookId" xmlns="https://www.idpf.org/2007/opf">\n'
        package_end = '</package>\n'
        metadata = self._create_metadata()
        images_files_list = self._get_files_list()
        manifest = self._create_manifestdata(images_files_list)
        spine = self._create_spine_data()
        content_file = ''.join([xml_version, package_start, metadata, manifest, spine, package_end])
        toc_file = self._create_table_of_content_data()
        return content_file, toc_file

    def _create_metadata(self) -> str:
        metadata_start = '\t<metadata xmlns:dc="https://purl.org/dc/elements/1.1/" xmlns:opf="https://www.idpf.org/2007/opf">\n'
        metadata_end = '\t</metadata>\n'
        metadata_id = f'\t\t<dc:identifier id="BookId">{self.book_title}</dc:identifier>\n'
        metadata_book_title = f'\t\t<dc:title>{self.book_title}</dc:title>\n'
        metadata_book_author = f'\t\t<dc:creator opf:role="">{self.author_name}</dc:creator>\n'
        posted_date = datetime.fromtimestamp(self.book_posted_date).strftime("%d-%b-%Y")
        updated_date = datetime.fromtimestamp(self.book_updated_date).strftime("%d-%b-%Y")
        metadata_posted_date = f'\t\t<dc:date opf:event="publication">{posted_date}</dc:date>\n'
        metadata_updated_date = f'\t\t<dc:date opf:event="modification">{updated_date}</dc:date>\n'
        metadata_book_description = f'\t\t<dc:description>{self.book_description}</dc:description>\n'
        metadata_cover = '\t\t<meta name="cover" content="_cover.jpg"/>\n'
        return ''.join([metadata_start, metadata_id, metadata_book_title, metadata_book_author, metadata_book_description, metadata_posted_date, metadata_updated_date, metadata_cover, metadata_end])

    def _get_files_list(self) -> tuple[str, ...]:
        book_path = Path(self.book_directory)
        images_files_paths_list = sorted(book_path.glob('Images/*.*'))
        images_files_list = tuple(file.name for file in images_files_paths_list)
        return images_files_list

    def _create_manifestdata(self, images_files_list: tuple[str, ...]) -> str:
        text_files_list = [chapter.chapter_file_name for chapter in self.chapters_info_list]
        manifest_start = f'\t<manifest>\n'
        manifest_end = f'\t\t<item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>\n\t</manifest>\n'
        manifest_text_data = ''.join([f'\t\t<item id="{file_name}" href="Text/{file_name}" media-type="application/xhtml+xml"/>\n' for file_name in text_files_list])
        manifest_images_data = ''.join([f'\t\t<item id="{image_name}" href="Images/{image_name}" media-type="image/jpeg"/>\n' for image_name in images_files_list])
        manifest_title_page = '\t\t<item id="titlepage.html" href="Text/titlepage.html" media-type="application/xhtml+xml"/>\n'
        return ''.join((manifest_start, manifest_text_data, manifest_images_data, manifest_title_page, manifest_end))

    def _create_spine_data(self) -> str:
        text_files_list = [chapter.chapter_file_name for chapter in self.chapters_info_list]
        spine_start = '\t<spine toc="ncx">\n\t\t<itemref idref="titlepage.html" linear="no"/>\n'
        spine_end = '\t</spine>\n'
        spine_chapters_data = ''.join([f'\t\t<itemref idref="{file_name}"/>\n' for file_name in text_files_list])
        return ''.join((spine_start, spine_chapters_data, spine_end))

    def _create_table_of_content_data(self) -> str:
        text_files_list = [chapter.chapter_file_name for chapter in self.chapters_info_list]
        toc_start = '<?xml version="1.0" encoding="utf-8"?>\n<!DOCTYPE ncx PUBLIC "-//NISO//DTD ncx 2005-1//EN"\n"https://www.daisy.org/z3986/2005/ncx-2005-1.dtd">\n<ncx xmlns="https://www.daisy.org/z3986/2005/ncx/" version="2005-1">\n'
        toc_head = f'<head>\n\t<meta name="dtb:uid" content="{self.book_title}"/>\n\t<meta name="dtb:depth" content="1"/>\n\t<meta name="dtb:totalPageCount" content="0"/>\n\t<meta name="dtb:maxPageNumber" content="0"/>\n</head>\n'
        toc_title = f'<docTitle><text>{self.author_name} - {self.book_title}</text></docTitle>\n'
        nav_map_start = '\t<navMap>\n'
        nav_map_end = '\t</navMap>\n'
        toc_end = '</ncx>'
        nav_map_data = f'\t\t<navPoint id="navPoint-0" playOrder="0">\n\t\t\t<navLabel><text>Title page</text></navLabel>\n\t\t\t<content src="Text/titlepage.html"/>\n\t\t</navPoint>\n'
        for number, file_name in enumerate(text_files_list):
            chapters_info = self.chapters_info_list[number]
            nav_point = f'\t\t<navPoint id="navPoint-{number + 1}" playOrder="{number + 1}">\n\t\t\t<navLabel><text>{chapters_info.chapter_name}</text></navLabel>\n\t\t\t<content src="Text/{file_name}"/>\n\t\t</navPoint>\n'
            nav_map_data += nav_point
        toc_data = ''.join([toc_start, toc_head, toc_title, nav_map_start, nav_map_data, nav_map_end, toc_end])
        return toc_data

    def _create_chapters_data(self) -> list[tuple[str, str]]:
        chapters_data = []
        for chapter in self.chapters_info_list:
            chapter_path = Path(self.book_directory)
            chapter_name = chapter.chapter_file_name
            chapter_path = chapter_path.joinpath('Text', chapter_name)
            text = chapter_path.read_text(encoding='utf-8')
            chapter_header = '<?xml version="1.0" encoding="utf-8"?>\n<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN"\n"http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">\n<html xmlns="http://www.w3.org/1999/xhtml">\n'
            chapter_title = f'<head><title>{chapter.chapter_name}</title></head>\n'
            chapter_text = f'<body>\n{text}\n</body>\n</html>\n'
            chapter_data = ''.join([chapter_header, chapter_title, chapter_text])
            chapters_data.append((chapter_name, chapter_data))
        return chapters_data

    def _create_title_page(self) -> str:
        book_tags = ', '.join(self.book_tags)
        posted_date = datetime.fromtimestamp(self.book_posted_date).strftime("%d-%b-%Y")
        updated_date = datetime.fromtimestamp(self.book_updated_date).strftime("%d-%b-%Y")
        title_page_start = '<?xml version="1.0" encoding="utf-8"?>\n<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en">\n<body>\n'
        title_page_cover = '\t<div><img src="../Images/_cover.jpg" alt="cover"/></div>\n'
        title_page_book_description = f'\t<div><text>\t{self.book_description}</text></div>\n'
        title_page_book_size = f'\t<div><text><b>Размер:</b> {self.book_size} Кб'
        title_page_book_status = f'\t<b>Статус:</b> {self.book_status}</text></div>\n'
        title_page_book_score = f'\t<div></text><b>Оценка:</b> {self.book_score}'
        title_page_book_genre = f'\t<b>Жанр:</b> {self.book_genre}</text></div>\n'
        title_page_book_tags = f'\t<div></text><b>Тэги:</b> {book_tags}</text></div>\n'
        title_page_book_dates = f'\t<div></text><b>Дата публикации:</b> {posted_date} <b>Последнее обновление:</b> {updated_date}</text></div>\n'
        title_page_end = '</body>\n</html>'
        return ''.join([title_page_start, title_page_cover, title_page_book_description,
                        title_page_book_size, title_page_book_status, title_page_book_score,
                        title_page_book_genre, title_page_book_tags, title_page_book_dates, title_page_end])

    @staticmethod
    def _create_meta_inf_data() -> str:
        meta_inf_data = ('<?xml version="1.0" encoding="UTF-8"?>\n<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">\n'
                         '\t<rootfiles>\t\t<rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>\n\t\t</rootfiles>\n</container> ')
        return meta_inf_data

    def _get_images(self) -> list[tuple[str, Path]]:
        images_path = Path(self.book_directory, 'Images')
        images_files_paths_list = sorted(images_path.glob('*.*'))
        images_list = [(image_path.name, image_path) for image_path in images_files_paths_list]
        return images_list
