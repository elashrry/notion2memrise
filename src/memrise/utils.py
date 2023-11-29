"""Utility functions to help control Memrise account and course."""

from io import StringIO
import pandas as pd
from bs4 import BeautifulSoup as bs
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver import Firefox, Remote
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.remote.webelement import WebElement

from src.memrise import constants as cont
from src.constants import (
    COL_LIST, NOT_NULL_COL_LIST)


def create_driver(headless=True):
    """Creates a Firefox webdriver from Selenium

    Args:
        headless (bool, optional): whether to run the browser in headless mode. 
        Defaults to True.

    Returns:
        selenium.webdriver.FireFox: a selenium webdriver using Firefox
    """
    if headless:
        options = Options()
        options.headless = True
        return Firefox(executable_path=cont.FIREFOX_PATH, options=options)
    return Firefox(executable_path=cont.FIREFOX_PATH)


def sign_in(driver: Remote, email: str, password: str):
    """Signs in to Memrise using the passed driver.

    Args:
        driver (selenium.webdriver.Remote): a selenium webdriver
        email (str): email of the Memrise account
        password (str): password of the Memrise account

    Returns:
        selenium.webdriver.Remote: the passed driver after signing in
    """
    driver.get(cont.LOGIN_URL)
    element = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, cont.EMAIL_ID)))
    element.send_keys(email)
    element = driver.find_element_by_id(cont.PASSWORD_ID)
    element.send_keys(password)
    button = driver.find_element_by_xpath(cont.SUBMIT_XPATH)
    button.click()
    # wait  login in. i.e. a button with title "Your account"
    WebDriverWait(driver, cont.TIMEOUT_LIMIT).until(
        EC.presence_of_element_located(
            (By.XPATH, '//button[@title="Your account"]')))

    return driver

def click_save_changes(driver: Remote, course_edit_url: str):
    """Clicks on the save changes button.

    Note: The admin user must be logged in the passed driver.

    Args:
        driver (selenium.webdriver.Remote): a selenium webdriver.
        course_edit_url (str): url of the edit page of the course.

    Returns:
        selenium.webdriver.Remote: the passed driver after clicking on save changes
    """
    # The admin user must be logged in the passed driver.
    driver.get(course_edit_url)
    # wait until the "save changes" appear
    save_changes_btn = WebDriverWait(driver, cont.TIMEOUT_LIMIT).until(
            EC.element_to_be_clickable(
                (By.XPATH, f"//a[@class='{cont.SAVE_CHANGES_CLASS}']")))
    driver.execute_script("arguments[0].click();", save_changes_btn)
    # wait until you go back to main page of the course
    WebDriverWait(driver, cont.TIMEOUT_LIMIT).until(
        EC.presence_of_element_located(
            (By.XPATH, "//span[@class='leaderboard-text']")))

    return driver

def validate_input(word_df):
    """Validates the passed dataframe.

    Make sure that:
    - all columns exist and in the right order using the COL_LIST constant
    - Important columns have no nas

    Args:
        word_df (pandas.DataFrame): dataframe of words to be added to Memrise.

    Returns:
        pandas.DataFrame: validated dataframe.
    """
    # make sure it is a dataframe
    if isinstance(word_df, pd.Series): # convert to a dataframe
        word_df = word_df.to_frame().T
    # this is not needed if I enforce the type of args in all the code.
    if not isinstance(word_df, pd.DataFrame):
        raise ValueError("word_df must be a pandas dataframe")

    # all column exist and in the right order
    # French, English, and date modified columns have no nas
    # TODO: to be more verbose about the errors
    df_valid = word_df[COL_LIST].dropna(subset=NOT_NULL_COL_LIST)

    return df_valid

def show_all_level_tables(driver: Remote):
    """Show all level tables in the edit page.

    Note: The admin user must be logged in the passed driver.
    
    The driver must be in the course edit page.

    Args:
        driver (selenium.webdriver.Remote): a selenium webdriver

    Returns:
        selenium.webdriver.Remote: the passed driver after showing all level tables
    """
    # every time I click show the page change its source and the element in the list
    # becomes stale, so I check for valid show buttons each time.
    driver, show_btn_list = _get_show_btns_for_folded_levels(driver)
    all_shown = False
    while not all_shown:
        if show_btn_list:
            show_btn = show_btn_list[0]
            level_element = show_btn.find_element_by_xpath('../../../..')
            level_id = level_element.get_attribute("data-level-id")
            driver.execute_script("arguments[0].click();", show_btn)
            # wait until the table appears
            WebDriverWait(driver, cont.TIMEOUT_LIMIT).until(
                EC.presence_of_element_located(
                    (By.XPATH, f"//table[@data-level-id='{level_id}']")))
            driver, show_btn_list = _get_show_btns_for_folded_levels(driver)
        else:  # empty show buttons for folded levels
            all_shown = True
    return driver

def _get_show_btns_for_folded_levels(driver):
    # all show buttons
    show_btn_list = WebDriverWait(driver, cont.TIMEOUT_LIMIT).until(
        EC.presence_of_all_elements_located(
            (By.XPATH, "//a[@class='show-hide btn btn-small']")))
    # loop and check if the level is shown or not
    valid_show_btn_list = []
    for show_btn in show_btn_list:
        level_element = show_btn.find_element_by_xpath('../../../..')
        try:  # level is shown
            level_element.find_element_by_xpath(
                ".//table[@class='level-things table ui-sortable']")
        except NoSuchElementException:
            valid_show_btn_list.append(show_btn)
    
    return driver, valid_show_btn_list

def cell_col_to_xpath_predicate(driver: Remote, course_edit_url: str):
    """Returns a dictionary of column names and their xpath predicates.

    Note: The admin user must be logged in the passed driver.

    Args:
        driver (selenium.webdriver.Remote): a selenium webdriver.
        course_edit_url (str): url of the edit page of the course.

    Returns:
        selenium.webdriver.Remote: the passed driver after showing all level tables
        dict: a dictionary of column names and their xpath predicates
    """
    driver.get(course_edit_url)
    driver = show_all_level_tables(driver)
    # on thead element with class="columns"
    thead_element = WebDriverWait(driver, cont.TIMEOUT_LIMIT).until(
        EC.presence_of_element_located(
            (By.XPATH, "//thead[@class='columns']")))
    thead_html = thead_element.get_attribute('outerHTML')
    soup = bs(thead_html, 'html.parser')
    column_predicate_dict = {}
    for th in soup.find_all('th'):
        span = th.find('span')
        column_name = span.text if span else ""
        class_list = th.get("class") if th.get("class") else []
        # column class is column text or attribute text
        # while cell class if cell text column or cell text attribute
        class_name = " ".join(class_list[-1::-1]) if class_list else ""
        class_name = "cell "+class_name if class_name else ""
        data_key = th.get("data-key") if th.get("data-key") else ""
        xpath_predicate = f"@class='{class_name}' and @data-key='{data_key}'"
        column_predicate_dict[column_name] = xpath_predicate

    return driver, column_predicate_dict



def table_element_to_df(table_element: WebElement):
    """Returns a dataframe from a table element.

    Args:
        table_element (selenium.webdriver.remote.webelement.WebElement): a table element

    Returns:
        pandas.DataFrame: a dataframe of the table element
    """
    table_html = table_element.get_attribute('outerHTML')
    soup = bs(table_html, 'html.parser')

    # Extract the thead and the first tbody
    # second and third tbody are for something else
    thead = soup.find('thead')
    first_tbody = soup.find('tbody')

    # Create a new table with the thead and the first tbody
    new_table = soup.new_tag('table')
    new_table.append(thead)
    new_table.append(first_tbody)
    # remove any button
    # ?: is there a simpler way to keep only text from each cell?
    for button in new_table.find_all('button'):
        button.decompose()

    table_io = StringIO(str(new_table))
    table_df = pd.read_html(table_io)[0]

    return table_df


def count_level_words(driver, level_id: str):
    """Returns the number of words in a level.

    Args:
        level_element (selenium.webdriver.remote.webelement.WebElement): a level element.
            It is the div with lass='level' and @data-level-id='{level_id}'.

    Returns:
        int: the number of words in a level
    """
    table_element = WebDriverWait(driver, cont.TIMEOUT_LIMIT).until(
        EC.presence_of_element_located(
            (By.XPATH,
                f"//table[@class='level-things table ui-sortable' and @data-level-id='{level_id}']")))  # noqa: E501
    level_word_count = len(table_element.find_elements_by_xpath(
        ".//tbody/tr[@class='thing']"))

    return level_word_count


def create_new_level(driver: Remote, db_name: str):
    """Creates a new level in the Memrise course.

    Note: The admin user must be logged in the passed driver.
    Note: The driver must be in the edit page.

    Args:
        driver (selenium.webdriver.Remote): a selenium webdriver.
        db_name (str): name of the database of the course on memrise.
            This is found when you click on Databases tab in the edit page. 

    Returns:
        selenium.webdriver.Remote: the passed driver after creating a new level
    """
    add_level_btn = WebDriverWait(driver, cont.TIMEOUT_LIMIT).until(
        EC.element_to_be_clickable(
            (By.XPATH, "//button[@class='dropdown-toggle btn btn-icos-active']")))
    driver.execute_script("arguments[0].click();", add_level_btn)
    add_level_btn = WebDriverWait(driver, cont.TIMEOUT_LIMIT).until(
        EC.element_to_be_clickable(
            (By.XPATH,
                f"//a[@data-role='level-add' and contains(text(),'{db_name}')]")))
    driver.execute_script("arguments[0].click();", add_level_btn)

    return driver
