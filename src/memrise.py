"""Utility functions to control Memrise account and course."""

from io import StringIO
from typing import List, Literal, Union

import pandas as pd
from bs4 import BeautifulSoup as bs
from selenium.common.exceptions import TimeoutException
from selenium.webdriver import Firefox, Remote
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.remote.webelement import WebElement

from src.constants import COL_LIST

# TODO: enforce type checking

FIREFOX_PATH = "/opt/homebrew/bin/geckodriver"
LOGIN_URL = "https://app.memrise.com/signin"
COURSE_EDIT_URL = "https://app.memrise.com/course/6512551/my-french-2/edit/"

EMAIL_ID = "username"
PASSWORD_ID = "password"
SUBMIT_XPATH = "//button[@type='submit']"
YES_BTN_CLASS = "btn btn-primary btn-yes"
SAVE_CHANGES_CLASS = "btn btn-success"

TIMEOUT_LIMIT = 5  # in seconds

# columns that should not have nas
NOT_NULL_COL_LIST = ["French", "English", "date modified", "cell id"]


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
        return Firefox(executable_path=FIREFOX_PATH, options=options)
    return Firefox(executable_path=FIREFOX_PATH)


def sign_in(driver: Remote, email: str, password: str):
    """Signs in to Memrise using the passed driver.

    Args:
        driver (selenium.webdriver.Remote): a selenium webdriver
        email (str): email of the Memrise account
        password (str): password of the Memrise account

    Returns:
        selenium.webdriver.Remote: the passed driver after signing in
    """
    driver.get(LOGIN_URL)
    element = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, EMAIL_ID)))
    element.send_keys(email)
    element = driver.find_element_by_id(PASSWORD_ID)
    element.send_keys(password)
    button = driver.find_element_by_xpath(SUBMIT_XPATH)
    button.click()
    # wait  login in. i.e. a button with title "Your account"
    WebDriverWait(driver, TIMEOUT_LIMIT).until(
        EC.presence_of_element_located(
            (By.XPATH, '//button[@title="Your account"]')))

    return driver


def _validate_input(word_df):
    """Validates the passed dataframe.

    Make sure that:
    - all columns exist and in the right order using the COL_LIST constant
    - Important columns have no nas

    Args:
        word_df (pandas.DataFrame): dataframe of words to be added to Memrise.

    Returns:
        pandas.DataFrame: validated dataframe.
    """
    # all column exist and in the right order
    # French, English, and date modified columns have no nas
    # TODO: to be more verbose about the errors
    df_valid = word_df[COL_LIST].dropna(subset=NOT_NULL_COL_LIST)

    return df_valid

def show_all_level_tables(driver: Remote):
    """Show all level tables in the edit page.

    Note: The admin user must be logged in the passed driver.

    Args:
        driver (selenium.webdriver.Remote): a selenium webdriver

    Returns:
        selenium.webdriver.Remote: the passed driver after showing all level tables
    """
    show_btn_list = WebDriverWait(driver, TIMEOUT_LIMIT).until(
        EC.presence_of_all_elements_located(
            (By.XPATH, "//a[@class='show-hide btn btn-small']")))
    for show_btn in show_btn_list:
        show_btn.click()

    return driver

def delete_words(driver: Remote, word_ids: Union[List[str], Literal["ALL"]]):
    """Deletes words from the Memrise course.

    Note: The admin user must be logged in the passed driver.

    Args:
        driver (selenium.webdriver.Remote): a selenium webdriver
        word_ids (list of str or "ALL"): list of words to be deleted or "ALL" to delete 
        all words.

    Returns:
        selenium.webdriver.Remote: the passed driver after deleting the words
        pandas.DataFrame: a dataframe with the result of deleting each word
    """
    # The admin user must be logged in the passed driver.
    driver.get(COURSE_EDIT_URL)
    # wait until the "save changes" appear
    WebDriverWait(driver, TIMEOUT_LIMIT).until(
            EC.element_to_be_clickable((By.XPATH, f"//a[@class='{SAVE_CHANGES_CLASS}']")))

    if word_ids == "ALL":
        driver, words_df = get_all_words(driver)
        return delete_words(driver, words_df["word"].tolist())
    else:
        res_dict = {
            "cell id": [],  # str
            "deleted": [],  # bool
            "error": [],  # str
        }
        driver = show_all_level_tables(driver)
        for w_id in word_ids:
            res_dict["cell id"].append(w_id)
            try:
                word_element = WebDriverWait(driver, TIMEOUT_LIMIT).until(
                    EC.presence_of_element_located(
                        (By.XPATH, f'//div[text()="{w_id}"]')))
                remove_action = word_element.find_element_by_xpath(
                    '../../..//i[@data-role="remove"]')
                remove_action.click()
                yes_btn = driver.find_element_by_xpath(
                    f'//a[@class="{YES_BTN_CLASS}"]')
                yes_btn.click()
                # wait until the dialogue disappear
                WebDriverWait(driver, TIMEOUT_LIMIT).until(
                    EC.invisibility_of_element_located(
                        (By.XPATH, '//div[@class="modal-backdrop fade"]')))
                # I verify that the word in not in the page outside the for loop
                res_dict["deleted"].append(True)
                res_dict["error"].append(None)
            except TimeoutException:
                res_dict["deleted"].append(False)
                res_dict["error"].append(
                    f"TimeoutException: Word not found within {TIMEOUT_LIMIT} seconds"
                )
            except Exception as e:
                res_dict["deleted"].append(False)
                res_dict["error"].append(str(e))
        # deleting words doesn't need us to click on save changes (weird!)
        res_df = pd.DataFrame(res_dict)
        # verify that the words with deleted=True are not in the page
        for w_id in res_df[res_df["deleted"]]["cell id"]:
            try:
                WebDriverWait(driver, 0.01).until(
                    EC.presence_of_element_located(
                        (By.XPATH, f'//div[text()="{w_id}"]')))
                res_df.loc[res_df["cell id"] == w_id, "deleted"] = False
                res_df.loc[res_df["cell id"] == w_id, "error"] = "Unknown"
            except TimeoutException:
                pass
        # TODO: delete the words from the database

    return driver, res_df

def _delete_words_from_db(driver: Remote, words: Union[List[str], Literal["ALL"]]):
    raise NotImplementedError(
        "Deleting all words from the database is not implemented yet")

def cell_col_to_xpath_predicate(driver: Remote):
    """Returns a dictionary of column names and their xpath predicates.

    Note: The admin user must be logged in the passed driver.

    Args:
        driver (selenium.webdriver.Remote): a selenium webdriver

    Returns:
        selenium.webdriver.Remote: the passed driver after showing all level tables
        dict: a dictionary of column names and their xpath predicates
    """
    driver.get(COURSE_EDIT_URL)
    driver = show_all_level_tables(driver)
    # on thead element with class="columns"
    thead_element = WebDriverWait(driver, TIMEOUT_LIMIT).until(
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

def update_words(driver: Remote, word_df: pd.DataFrame):
    """Updates words in the Memrise course.

    Note: The admin user must be logged in the passed driver.

    Args:
        driver (selenium.webdriver.Remote): a selenium webdriver
        word_df (pandas.DataFrame): dataframe of words to be updated in Memrise.

    Returns:
        selenium.webdriver.Remote: the passed driver after updating the words
        pandas.DataFrame: a dataframe with the result of updating each word
    """
    word_df = _validate_input(word_df)
    driver, column_predicate_dict = cell_col_to_xpath_predicate(driver)
    driver = show_all_level_tables(driver)
    res_dict = {
        "cell id": [],  # str
        "updated": [],  # bool
        "error": [],  # str
    }
    for _, row in word_df.iterrows():
        res_dict["cell id"].append(row["cell id"])
        try:
            cell_id_element = WebDriverWait(driver, TIMEOUT_LIMIT).until(
                EC.presence_of_element_located(
                    (By.XPATH, f"//div[text()='{row['cell id']}']")))
            row_element = cell_id_element.find_element_by_xpath('../../..')
            for col in word_df.columns:
                if col=="cell id":
                    continue
                xpath_predicate = column_predicate_dict[col]
                cell_element = row_element.find_element_by_xpath(
                    f".//td[{xpath_predicate}]")
                text_element = cell_element.find_element_by_xpath(
                    ".//div[@class='text']")
                # text_element.click()
                # text_element.clear()  # doesn't work with div elements
                # text_element.send_keys(row[col])  # doesn't work with div elements
                driver.execute_script(
                    f"arguments[0].innerText = '{row[col]}'", text_element)
            res_dict["updated"].append(True)
            res_dict["error"].append(None)
        except TimeoutException:
            res_dict["updated"].append(False)
            res_dict["error"].append(
                f"TimeoutException: Word not found within {TIMEOUT_LIMIT} seconds"
            )
        except Exception as e:
            res_dict["updated"].append(False)
            res_dict["error"].append(str(e))
    res_df = pd.DataFrame(res_dict)

    return driver, res_df

def get_all_words(driver):
    """Returns all words in the Memrise course.

    Note: The admin user must be logged in the passed driver.

    Args:
        driver (selenium.webdriver.Remote): a selenium webdriver

    Returns:
        selenium.webdriver.Remote: the passed driver after showing all level tables
        pandas.DataFrame: a dataframe with all words in the Memrise course
    """
    # go to the edit page
    driver.get(COURSE_EDIT_URL)
    # show all tables
    driver = show_all_level_tables(driver)
    # get all table element with class="level-things table ui-sortable"
    table_list = WebDriverWait(driver, TIMEOUT_LIMIT).until(
        EC.presence_of_all_elements_located(
            (By.XPATH, "//table[@class='level-things table ui-sortable']")))
    all_words_df = pd.DataFrame()
    for table_element in table_list:
        # get its name
        # from its grandparent, concat
        # text from a div with class="level-handle"
        # text from an h3 element with class="level-name"
        level_handle_text = table_element.find_element_by_xpath(
            "../..//div[@class='level-handle']").text
        level_name_text = table_element.find_element_by_xpath(
            "../..//h3[@class='level-name']").text
        level_name = level_handle_text + "-" + level_name_text

        # to df
        table_df = _table_element_to_df(table_element)
        table_df.drop(columns="Unnamed: 0",
                      inplace=True)  # first columns for actions
        table_df["level"] = level_name

        # concat
        all_words_df = pd.concat([all_words_df, table_df])

    return driver, all_words_df.reset_index(drop=True)


def _table_element_to_df(table_element: WebElement):
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


def add_words(driver: Remote, word_df: pd.DataFrame):
    # it looks like after add bulk to a level, the level table collapses
    # to work with levels views
    # start by adding words to the empty levels
    # if there is no empty levels, add words to the last level and so on



    # The admin user must be logged in the passed driver.
    word_df = _validate_input(word_df)  # only valid (have FR and EN columns)
    word_notion_list = word_df["French"].tolist()
    if word_df.empty:
        return driver, word_notion_list, []
    else:
        # go to the edit page
        driver.get(COURSE_EDIT_URL)

        # choose add bulk words
        advanced_btn = WebDriverWait(driver, TIMEOUT_LIMIT).until(
            EC.element_to_be_clickable(
                (By.XPATH, '//button[contains(text(),"Advanced")]')))
        advanced_btn.click()
        bulk_add_btn = WebDriverWait(driver, TIMEOUT_LIMIT).until(
            EC.element_to_be_clickable(
                (By.XPATH, '//a[contains(text(),"Bulk add words")]')))
        bulk_add_btn.click()
        text_area = WebDriverWait(driver, TIMEOUT_LIMIT).until(
            EC.element_to_be_clickable((By.XPATH, '//textarea')))

        # past the csv string of word_df
        word_df_string = word_df.to_csv(index=False, sep="\t", header=False)
        text_area.send_keys(word_df_string)

        # click on add button
        add_btn = driver.find_element_by_xpath("//a[text()='Add']")
        add_btn.click()

        # refresh page and check if all words are added
        driver.refresh()
        # TODO: to check the words, loop over the rows of word_df and check if the
        # word is in the page

        # save changes
        save_btn = WebDriverWait(driver, TIMEOUT_LIMIT).until(
            EC.element_to_be_clickable((By.XPATH, f"//a[@class='{SAVE_CHANGES_CLASS}']")))
        save_btn.click()

        # wait until the course page load (exit the edit mode):
        # span with class="leaderboard-text"
        WebDriverWait(driver, TIMEOUT_LIMIT).until(
            EC.presence_of_element_located(
                (By.CLASS_NAME, "leaderboard-text")))
        