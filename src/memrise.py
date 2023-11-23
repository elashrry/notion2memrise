"""Utility functions to control Memrise account and course."""

from io import StringIO
from time import sleep
from typing import List, Literal, Union

import pandas as pd
import numpy as np
from bs4 import BeautifulSoup as bs
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver import Firefox, Remote
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.remote.webelement import WebElement

from src.constants import (
    COL_LIST, NOT_NULL_COL_LIST, COURSE_EDIT_URL,
    DB_NAME, LEVEL_WORD_LIMIT, COURSE_DB_URL)

# TODO: enforce type checking

FIREFOX_PATH = "/opt/homebrew/bin/geckodriver"
TIMEOUT_LIMIT = 10  # in seconds
WORD_SEARCH_TIME_OUT = 5  # in seconds
LOGIN_URL = "https://app.memrise.com/signin"
EMAIL_ID = "username"
PASSWORD_ID = "password"
SUBMIT_XPATH = "//button[@type='submit']"
YES_BTN_CLASS = "btn btn-primary btn-yes"
SAVE_CHANGES_CLASS = "btn btn-success"
MODAL_BACKDROP_CLASS = "modal-backdrop fade"
YES_NO_MODAL_ID = "modal-yesno"
UPDATE_CELL_JAVA_SCRIPT = """arguments[0].value = arguments[1];arguments[0].blur();"""


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

def agree_to_cookies(driver: Remote):
    """Agrees to cookies.

    Args:
        driver (selenium.webdriver.Remote): a selenium webdriver

    Returns:
        selenium.webdriver.Remote: the passed driver after agreeing to cookies
    """
    driver.get(COURSE_EDIT_URL)
    # wait until the cookies dialogue appears
    agree_btn = WebDriverWait(driver, TIMEOUT_LIMIT).until(
        EC.presence_of_element_located(
            (By.XPATH, "//a[contains(text(),'I agree')]")))
    agree_btn.click()

    return driver

def click_save_changes(driver: Remote):
    """Clicks on the save changes button.

    Note: The admin user must be logged in the passed driver.

    Args:
        driver (selenium.webdriver.Remote): a selenium webdriver

    Returns:
        selenium.webdriver.Remote: the passed driver after clicking on save changes
    """
    # The admin user must be logged in the passed driver.
    driver.get(COURSE_EDIT_URL)
    # wait until the "save changes" appear
    save_changes_btn = WebDriverWait(driver, TIMEOUT_LIMIT).until(
            EC.element_to_be_clickable(
                (By.XPATH, f"//a[@class='{SAVE_CHANGES_CLASS}']")))
    driver.execute_script("arguments[0].click();", save_changes_btn)
    # wait until you go back to main page of the course
    WebDriverWait(driver, TIMEOUT_LIMIT).until(
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

    Args:
        driver (selenium.webdriver.Remote): a selenium webdriver

    Returns:
        selenium.webdriver.Remote: the passed driver after showing all level tables
    """
    show_btn_list = WebDriverWait(driver, TIMEOUT_LIMIT).until(
        EC.presence_of_all_elements_located(
            (By.XPATH, "//a[@class='show-hide btn btn-small']")))
    for show_btn in show_btn_list:
        level_element = show_btn.find_element_by_xpath('../../..')
        try:
            level_element.find_element_by_xpath(
                ".//table[@class='level-things table ui-sortable']")
        except NoSuchElementException:
            driver.execute_script("arguments[0].click();", show_btn)

    return driver

def delete_words_old(driver: Remote, word_ids: Union[List[str], Literal["ALL"]]):
    """Deletes words from the Memrise course.

    # ! duplicated
    Note: The admin user must be logged in the passed driver.

    Args:
        driver (selenium.webdriver.Remote): a selenium webdriver
        word_ids (list of str or "ALL"): list of cell ids of words to be deleted or 
        "ALL" to delete all words.

    Returns:
        selenium.webdriver.Remote: the passed driver after deleting the words
        pandas.DataFrame: a dataframe with the result of deleting each word
    """
    driver.get(COURSE_EDIT_URL)
    # wait until the "save changes" appear
    WebDriverWait(driver, TIMEOUT_LIMIT).until(
            EC.element_to_be_clickable((By.XPATH, f"//a[@class='{SAVE_CHANGES_CLASS}']")))

    if word_ids == "ALL":
        driver, words_df = get_all_words(driver)
        return delete_words(driver, words_df["cell id"].tolist())
    else:
        res_dict = {
            "cell id": [],  # str
            "deleted": [],  # bool
            "error": [],  # str
        }
        if len(word_ids) == 0:
            return driver, pd.DataFrame(res_dict)
        driver = show_all_level_tables(driver)
        for w_id in word_ids:
            res_dict["cell id"].append(w_id)
            try:
                word_element = WebDriverWait(driver, TIMEOUT_LIMIT).until(
                    EC.presence_of_element_located(
                        (By.XPATH, f'//div[text()="{w_id}"]')))
                remove_action = word_element.find_element_by_xpath(
                    '../../..//i[@data-role="remove"]')
                driver.execute_script("arguments[0].click();", remove_action)
                yes_btn = WebDriverWait(driver, TIMEOUT_LIMIT).until(
                    EC.element_to_be_clickable(
                        (By.XPATH, f"//a[@class='{YES_BTN_CLASS}']")))
                driver.execute_script("arguments[0].click();", yes_btn)
                # wait until the dialogue disappear
                WebDriverWait(driver, TIMEOUT_LIMIT).until(
                    EC.invisibility_of_element_located(
                        (By.XPATH, f"//div[@id='{YES_NO_MODAL_ID}']")))
                # I verify that the word in not in the page outside the for loop
                res_dict["deleted"].append(True)
                res_dict["error"].append(np.nan)
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
        sleep(1)  # to make sure the words are deleted
        for w_id in res_df[res_df["deleted"]]["cell id"]:
            try:
                WebDriverWait(driver, WORD_SEARCH_TIME_OUT).until(
                    EC.presence_of_element_located(
                        (By.XPATH, f'//div[text()="{w_id}"]')))
                res_df.loc[res_df["cell id"] == w_id, "deleted"] = False
                res_df.loc[res_df["cell id"] == w_id, "error"] = "Unknown"
            except TimeoutException:
                pass
        # TODO: delete the words from the database

    return driver, res_df

def _delete_one_word_from_db(driver: Remote, cell_id: str):
    """Deletes one word from the Memrise course database.

    Args:
        driver (selenium.webdriver.Remote): A selenium webdriver.
        cell_id (str): The ID of the word to be deleted.

    Returns:
        selenium.webdriver.Remote: the passed driver after deleting the words
        bool: indicates success or failure of deletion.
        str: If deletion fails, the error message; otherwise, np.nan.
    """
    driver.get(COURSE_DB_URL)
    # search for the word in the db and delete it
    search_field = WebDriverWait(driver, TIMEOUT_LIMIT).until(
        EC.element_to_be_clickable((By.ID, "search_string")))
    search_field.send_keys(cell_id)
    search_btn = driver.find_element_by_xpath("//button[@class='btn-default btn-ico']")
    search_btn.click()
    try: 
        thing_list = WebDriverWait(driver, TIMEOUT_LIMIT).until(
            EC.presence_of_all_elements_located(
                (By.CLASS_NAME, "thing")))
    except TimeoutException: 
        return driver, False, "The word doesn't exist"
    # I am deleting all occurrences of the word because memrise's DB allow duplicates
    # There should be a better way to handle that
    # because it could cover an error somewhere else, e.g. the add function.
    # I also loop while refreshing the page so that if there are more than one page
    # of the word, they all get deleted.
    while thing_list:
        driver, res_df_temp = _delete_db_page(driver)
        driver.refresh()
        try:
            thing_list = WebDriverWait(driver, TIMEOUT_LIMIT).until(
                EC.presence_of_all_elements_located(
                    (By.CLASS_NAME, "thing")))
        except TimeoutException:
            break
    # if while ends, this means there is no more occurrences of the word in the DB
    return driver, True, np.nan


def _delete_db_page(driver: Remote):
    """Deletes all entries in a Memrise course database page.

    Note: the driver should be at the page desired to be deleted and it should contain
    at least one entry.
    # ? should the function handle empty pages? I think so.

    Args:
        driver (selenium.webdriver.Remote): A selenium webdriver.

    Returns:
        selenium.webdriver.Remote: the passed driver after deleting the words
        pandas.DataFrame: a dataframe with the result of deleting each word
    """
    # get the cell col dict to find cell id later
    # save the url for the current page first
    current_page_url = driver.current_url
    driver, col_predicate_dict = cell_col_to_xpath_predicate(driver)
    cell_id_predicate = col_predicate_dict["cell id"]
    driver.get(current_page_url)
    res_dict = {
        "cell id": [],  # str
        "deleted": [],  # bool
        "error": [],  # str
    }
    thing_list = WebDriverWait(driver, TIMEOUT_LIMIT).until(
        EC.presence_of_all_elements_located(
            (By.CLASS_NAME, "thing")))
    for thing_element in thing_list:
        cell_element = thing_element.find_element_by_xpath(
            f".//td[{cell_id_predicate}]")
        text_element = cell_element.find_element_by_xpath(
            ".//div[@class='text']")
        cell_id = text_element.text
        res_dict["cell id"].append(cell_id)
        try:
            remove_action = thing_element.find_element_by_xpath(
                ".//i[@data-role='delete']")
            driver.execute_script("arguments[0].click();", remove_action)
            yes_btn = WebDriverWait(driver, TIMEOUT_LIMIT).until(
                EC.element_to_be_clickable(
                    (By.XPATH, f"//a[@class='{YES_BTN_CLASS}']")))
            driver.execute_script("arguments[0].click();", yes_btn)
            # wait until the dialogue disappear
            WebDriverWait(driver, TIMEOUT_LIMIT).until(
                EC.invisibility_of_element_located(
                    (By.XPATH, f"//div[@id='{YES_NO_MODAL_ID}']")))
            res_dict["deleted"] = True
            res_dict["error"] = np.nan
        except Exception as e:
            res_dict["deleted"].append(False)
            res_dict["error"].append(str(e))

    res_df = pd.DataFrame(res_dict)
    return driver, res_df


def delete_words(driver: Remote, word_ids: Union[List[str], Literal["ALL"]]):
    """Deletes words from the Memrise course database.

    Note: The admin user must be logged in the passed driver.

    Args:
        driver (selenium.webdriver.Remote): a selenium webdriver
        word_ids (list of str or "ALL"): list of cell ids of words to be deleted or 
        "ALL" to delete all words.

    Returns:
        selenium.webdriver.Remote: the passed driver after deleting the words
        pandas.DataFrame: a dataframe with the result of deleting each word
    """
    driver.get(COURSE_DB_URL)
    # wait until the search button be clickable
    WebDriverWait(driver, TIMEOUT_LIMIT).until(
        EC.element_to_be_clickable(
            (By.XPATH, "//button[@class='btn-default btn-ico']")))
    res_dict = {
        "cell id": [],  # str
        "deleted": [],  # bool
        "error": [],  # str
    }
    if word_ids == "ALL":
        res_df = pd.DataFrame(res_dict)
        # loop until you delete all pages of the DB.
        try:
            thing_list = WebDriverWait(driver, TIMEOUT_LIMIT).until(
                EC.presence_of_all_elements_located(
                    (By.CLASS_NAME, "thing")))
        except TimeoutException:  # empty DB
            return driver, res_df
        
        while thing_list:
            try:
                driver, res_df_temp = _delete_db_page(driver)
                res_df = pd.concat([res_df, res_df_temp]) 
                driver.refresh()
                thing_list = WebDriverWait(driver, TIMEOUT_LIMIT).until(
                EC.presence_of_all_elements_located(
                    (By.CLASS_NAME, "thing")))
            except TimeoutException:  # ? what happens if _delete_db_page raises an error?
                break
        return driver, res_df
    
    for cell_id in word_ids:
        driver, res_bool, error_str = _delete_one_word_from_db(driver, cell_id)
        res_dict["cell id"].append(cell_id)
        res_dict["deleted"].append(res_bool)
        res_dict["error"].append(error_str)
    res_df = pd.DataFrame(res_dict)
    return driver, res_df


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

def _update_cell(driver: Remote, cell_element: WebElement, new_value:str):
    """Updates a cell with a new value.

    Note: The admin user must be logged in the passed driver.

    When you update a cell in the level page, it also gets updated in the DB.

    Args:
        driver (selenium.webdriver.Remote): a selenium webdriver
        cell_element (selenium.webdriver.remote.webelement.WebElement): a cell element
        new_value (str): new value of the cell

    Returns:
        selenium.webdriver.Remote: the passed driver after updating the cell
    
    """
    text_element = cell_element.find_element_by_xpath(
        ".//div[@class='text']")
    driver.execute_script("arguments[0].click();", text_element)
    # wait for the input element, not the best way wait but ...
    # I can use WebDriverWait when I update the function to use row id and column id 
    # and type instead of xpaths
    sleep(0.001)
    input_element = text_element.find_element_by_xpath(
        ".//input[@type='text']")
    
    driver.execute_script(UPDATE_CELL_JAVA_SCRIPT, input_element, new_value)
    # wait until you find the now updated text
    updated = False
    while not updated:
        updated = (text_element.text == new_value)

    return driver


def update_words(driver: Remote, word_df: pd.DataFrame):
    """Updates words in the Memrise course.

    Note: The admin user must be logged in the passed driver.

    When you update a word in the level page, it also gets updated in the DB.

    Args:
        driver (selenium.webdriver.Remote): a selenium webdriver
        word_df (pandas.DataFrame): dataframe of words to be updated in Memrise.

    Returns:
        selenium.webdriver.Remote: the passed driver after updating the words
        pandas.DataFrame: a dataframe with the result of updating each word
    """
    word_df = validate_input(word_df)
    driver.get(COURSE_EDIT_URL)
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
                value = str(row[col]) if pd.notna(row[col]) else ""
                xpath_predicate = column_predicate_dict[col]
                cell_element = row_element.find_element_by_xpath(
                    f".//td[{xpath_predicate}]")
                driver = _update_cell(driver, cell_element, value)
            res_dict["updated"].append(True)
            res_dict["error"].append(np.nan)
        except TimeoutException:
            res_dict["updated"].append(False)
            res_dict["error"].append(
                f"TimeoutException: Word not found within {TIMEOUT_LIMIT} seconds"
            )
        except Exception as e:
            res_dict["updated"].append(False)
            res_dict["error"].append(str(e))
    res_df = pd.DataFrame(res_dict)
    driver = click_save_changes(driver)

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
    all_words_df = pd.DataFrame({}, columns=COL_LIST)
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
        if not table_df.empty:
            table_df = table_df[COL_LIST]
            all_words_df = pd.concat([all_words_df, table_df])
    # check dtypes and columns order and index
    all_words_df["date modified"] = pd.to_datetime(all_words_df["date modified"])
    columns_with_all_na = all_words_df.columns[all_words_df.isna().all()]
    all_words_df = all_words_df.astype({col: np.float64 for col in columns_with_all_na})
    all_words_df = all_words_df[COL_LIST].reset_index(drop=True)

    return driver, all_words_df


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


def _add_bulk(driver, level_id: str, word_df: pd.DataFrame):
    """Adds words to a level using the bulk add feature.

    The webelement to pass is the div with class="level-options".
    
    Passing the level options means the level is shown in the page.

    Args:
        driver (selenium.webdriver.Remote): a selenium webdriver
        level_element (selenium.webdriver.remote.webelement.WebElement): a level element.
            It is the div with lass='level' and @data-level-id='{level_id}'.
        word_df (pandas.DataFrame): dataframe of words to be added to Memrise.

    Returns:
        selenium.webdriver.Remote: the passed driver after adding the words
        pandas.DataFrame: a dataframe with the result of adding each word
    """
    # choose add bulk words
    # wait until the level is shown and get level options and table element
    level_element = WebDriverWait(driver, TIMEOUT_LIMIT).until(
        EC.presence_of_element_located(
            (By.XPATH, f"//div[@class='level' and @data-level-id='{level_id}']")))
    level_options = level_element.find_element_by_xpath(
            ".//div[@class='level-options']")
    advanced_btn = level_options.find_element_by_xpath(
        ".//button[contains(text(),'Advanced')]")
    driver.execute_script("arguments[0].click();", advanced_btn)
    bulk_add_btn = level_options.find_element_by_xpath(
        ".//a[contains(text(),'Bulk add words')]")
    driver.execute_script("arguments[0].click();", bulk_add_btn)
    text_area = WebDriverWait(driver, TIMEOUT_LIMIT).until(
        EC.element_to_be_clickable((By.XPATH, '//textarea')))

    # past the csv string of word_df
    word_df_string = word_df.to_csv(index=False, sep="\t", header=False)
    text_area.send_keys(word_df_string)

    # click on add button
    add_btn = driver.find_element_by_xpath("//a[text()='Add']")
    driver.execute_script("arguments[0].click();", add_btn)

    # wait until the dialogue disappear
    WebDriverWait(driver, TIMEOUT_LIMIT).until(
        EC.invisibility_of_element_located(
            (By.XPATH, f"//div[@class='{MODAL_BACKDROP_CLASS}']")))
    # one more second to make sure the words are added
    sleep(1)
    # ? save things?

    # loop over the rows of word_df and check if the word is in the page
    res_dict = {"cell id": [],  # str
                "added": [],  # bool
                "error": [],  # str
                }
    for cell_id in word_df["cell id"].values:
        res_dict["cell id"].append(cell_id)
        try:
            WebDriverWait(driver, WORD_SEARCH_TIME_OUT).until(
                EC.presence_of_element_located(
                    (By.XPATH, f'//div[text()="{cell_id}"]')))
            res_dict["added"].append(True)
            res_dict["error"].append(np.nan)
        except TimeoutException:
            res_dict["added"].append(False)
            res_dict["error"].append(
                f"TimeoutException: Word not found within {WORD_SEARCH_TIME_OUT} seconds"
            )
        except Exception as e:
            res_dict["added"].append(False)
            res_dict["error"].append(str(e))

    res_df = pd.DataFrame(res_dict)

    return driver, res_df


def count_level_words(driver, level_id: str):
    """Returns the number of words in a level.

    Args:
        level_element (selenium.webdriver.remote.webelement.WebElement): a level element.
            It is the div with lass='level' and @data-level-id='{level_id}'.

    Returns:
        int: the number of words in a level
    """
    table_element = WebDriverWait(driver, TIMEOUT_LIMIT).until(
        EC.presence_of_element_located(
            (By.XPATH,
                f"//table[@class='level-things table ui-sortable' and @data-level-id='{level_id}']")))  # noqa: E501
    level_word_count = len(table_element.find_elements_by_xpath(
        ".//tbody/tr[@class='thing']"))

    return level_word_count

def add_words(driver: Remote, word_df: pd.DataFrame):
    """Adds words to the Memrise course.

    Note: The admin user must be logged in the passed driver.

    First, it checks if there are any empty levels. If there are, it adds words to them.
    After that, it fills the last level if it is not full. Finally, it creates new
    levels as needed.

    Args:
        driver (selenium.webdriver.Remote): a selenium webdriver
        word_df (pandas.DataFrame): dataframe of words to be added to Memrise.

    Returns:
        selenium.webdriver.Remote: the passed driver after adding the words
        pandas.DataFrame: a dataframe with the result of adding each word
    """
    word_df = validate_input(word_df)  # only valid
    if word_df.empty:
        res_df = pd.DataFrame({
            "cell id": [],  # str
            "added": [],  # bool
            "error": [],  # str
        })
        return driver, res_df
    # go to the edit page
    driver.get(COURSE_EDIT_URL)
    # loop over levels
    # if the level is empty, add words to it
    # TODO: raise an error saying there is no levels in the course
    level_collapsed_list = WebDriverWait(driver, TIMEOUT_LIMIT).until(
        EC.presence_of_all_elements_located(
            (By.XPATH, "//div[@class='level collapsed']")))
    level_id_list = [
        level_collapsed_element.get_attribute("data-level-id")
        for level_collapsed_element in level_collapsed_list
    ]
    i = 0
    res_df = pd.DataFrame()
    for level_id in level_id_list:
        level_collapsed_element = WebDriverWait(driver, TIMEOUT_LIMIT).until(
            EC.presence_of_element_located(
                (By.XPATH,
                 f"//div[@class='level collapsed' and @data-level-id='{level_id}']")))
        show_btn = level_collapsed_element.find_element_by_xpath(
            ".//a[@class='show-hide btn btn-small']")
        driver.execute_script("arguments[0].click();", show_btn)
        level_word_count = count_level_words(driver, level_id)
        # if the level is empty, add words to it
        if level_word_count == 0 and i < len(word_df):  # only if there are more words
            driver, tmp_res_df = _add_bulk(
                driver, level_id, word_df.iloc[i:i+LEVEL_WORD_LIMIT])
            level_word_count += len(tmp_res_df[tmp_res_df["added"]])
            i += LEVEL_WORD_LIMIT
            res_df = pd.concat([res_df, tmp_res_df])

    # here, level_element is the last level
    # add words to it if it is not full
    if len(level_id_list) > 0:  # so level_id is defined
        if level_word_count < LEVEL_WORD_LIMIT and i < len(word_df):
            n_words_to_add = LEVEL_WORD_LIMIT - level_word_count
            driver, tmp_res_df = _add_bulk(
                driver, level_id, word_df.iloc[i:i+n_words_to_add])
            i += n_words_to_add
            res_df = pd.concat([res_df, tmp_res_df])
    # create new levels if needed
    word_df = word_df.iloc[i:] if i < len(word_df) else pd.DataFrame()
    # cut the remaining words LEVEL_WORD_LIMIT words per level and create new levels
    for i in range(0, len(word_df), LEVEL_WORD_LIMIT):
        batch_df = word_df.iloc[i:i+LEVEL_WORD_LIMIT]
        # create a new level
        driver = create_new_level(driver)
        # the page will refresh and the new level will be the only level not collapsed
        # wait until the page reload (the button is not visible)
        WebDriverWait(driver, TIMEOUT_LIMIT).until(
            EC.invisibility_of_element_located(
                (By.XPATH,
                 f"//a[@data-role='level-add' and contains(text(),'{DB_NAME}')]")))
        # get level options
        level_element = WebDriverWait(driver, TIMEOUT_LIMIT).until(
            EC.presence_of_element_located(
                (By.XPATH, "//div[@class='level']")))
        level_id = level_element.get_attribute("data-level-id")
        # add words to the new level
        driver, tmp_res_df = _add_bulk(driver, level_id, batch_df)
        res_df = pd.concat([res_df, tmp_res_df])

    return driver, res_df

def create_new_level(driver: Remote):
    """Creates a new level in the Memrise course.

    Note: The admin user must be logged in the passed driver.
    Note: The driver must be in the edit page.

    Args:
        driver (selenium.webdriver.Remote): a selenium webdriver

    Returns:
        selenium.webdriver.Remote: the passed driver after creating a new level
    """
    add_level_btn = WebDriverWait(driver, TIMEOUT_LIMIT).until(
        EC.element_to_be_clickable(
            (By.XPATH, "//button[@class='dropdown-toggle btn btn-icos-active']")))
    driver.execute_script("arguments[0].click();", add_level_btn)
    add_level_btn = WebDriverWait(driver, TIMEOUT_LIMIT).until(
        EC.element_to_be_clickable(
            (By.XPATH,
                f"//a[@data-role='level-add' and contains(text(),'{DB_NAME}')]")))
    driver.execute_script("arguments[0].click();", add_level_btn)

    return driver
