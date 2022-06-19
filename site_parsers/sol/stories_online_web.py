import os
from selenium.webdriver.firefox.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from bs4 import BeautifulSoup
import time
import pickle


class SolBookSelenium:
    def get_sol_book_soup(book_url: str, driver: WebDriver) -> BeautifulSoup:
        driver.get(book_url)
        driver.find_element(By.ID, "det-link").click()
        soup = _get_soup(driver)

        # with open('temp_html2.html', 'w') as file:
        #     file.write(page_source)
        return soup


def get_sol_chapter_soup(chapter_url: str, driver: WebDriver) -> BeautifulSoup:
    driver.get('https://storiesonline.net' + chapter_url)
    # защита от ботов, нужно несколько раз ткнуть, чтобы загрузилась вся страница
    while True:
        try:
            driver.find_element(By.XPATH, '//a[starts-with(@onclick, "ld")]').click()
            time.sleep(2)
        except NoSuchElementException:
            break

    soup = _get_soup(driver)
    return soup


def get_sol_updated_stories_soup(driver: WebDriver) -> BeautifulSoup:
    driver.get('https://storiesonline.net/library/updated_stories.php')
    soup = _get_soup(driver)
    return soup


def get_sol_new_stories_soup(driver: WebDriver) -> BeautifulSoup:
    driver.get('https://storiesonline.net/library/new_stories.php')
    soup = _get_soup(driver)
    return soup


def _get_soup(driver: WebDriver) -> BeautifulSoup:
    page_source = driver.page_source
    soup = BeautifulSoup(page_source, 'html5lib')
    return soup


def _save_soup_on_disk(soup: BeautifulSoup, page_name: str) -> None:
    os.chdir('C:\\Users\\Necros\\GDrive\\coding\\parsing2\\temp')
    with open(f'{page_name}.pickle', 'wb') as file:
        pickle.dump(str(soup), file)


def _get_soup_from_disk(pickle_file_name: str) -> BeautifulSoup:
    os.chdir('C:\\Users\\Necros\\GDrive\\coding\\parsing2\\temp')
    with open(pickle_file_name, 'rb') as file:
        soup = pickle.load(file)
        soup = BeautifulSoup(soup, 'html5lib')
    return soup
