"""Functions to control Memrise account and course."""

from time import sleep
from typing import List, Literal, Union
import pandas as pd
import numpy as np
from selenium.common.exceptions import TimeoutException
from selenium.webdriver import Remote
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.remote.webelement import WebElement

from src.constants import COL_LIST
from src.memrise import constants as cont
from src.memrise import utils as ut
from src.memrise.errors import MinNumberOfLevels
# TODO: enforce type checking

def _delete_one_word_from_db(driver: Remote, course_edit_url: str, course_db_url: str, cell_id: str):
    """Deletes one word from the Memrise course database.

    Args:
        driver (selenium.webdriver.Remote): A selenium webdriver.
        course_edit_url (str): url of the edit page of the course.
        course_db_url (str): url of the database page of the course.
        cell_id (str): The ID of the word to be deleted.

    Returns:
        selenium.webdriver.Remote: the passed driver after deleting the words
        bool: indicates success or failure of deletion.
        str: If deletion fails, the error message; otherwise, np.nan.
    """
    driver.get(course_db_url)
    # search for the word in the db and delete it
    search_field = WebDriverWait(driver, cont.TIMEOUT_LIMIT).until(
        EC.element_to_be_clickable((By.ID, "search_string")))
    search_field.send_keys(cell_id)
    search_btn = driver.find_element_by_xpath("//button[@class='btn-default btn-ico']")
    search_btn.click()
    try:
        thing_list = WebDriverWait(driver, cont.TIMEOUT_LIMIT).until(
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
        driver, res_df_temp = _delete_db_page(driver, course_edit_url)
        driver.refresh()
        try:
            thing_list = WebDriverWait(driver, cont.TIMEOUT_LIMIT).until(
                EC.presence_of_all_elements_located(
                    (By.CLASS_NAME, "thing")))
        except TimeoutException:
            break
    # if while ends, this means there is no more occurrences of the word in the DB
    return driver, True, np.nan


def _delete_db_page(driver: Remote, course_edit_url: str):
    """Deletes all entries in a Memrise course database page.

    Note: the driver should be at the page desired to be deleted and it should contain
    at least one entry.
    # ? should the function handle empty pages? I think so.

    Args:
        driver (selenium.webdriver.Remote): A selenium webdriver.
        course_edit_url (str): url of the edit page of the course.

    Returns:
        selenium.webdriver.Remote: the passed driver after deleting the words
        pandas.DataFrame: a dataframe with the result of deleting each word
    """
    # get the cell col dict to find cell id later
    # save the url for the current page first
    current_page_url = driver.current_url
    driver, col_predicate_dict = ut.cell_col_to_xpath_predicate(driver, course_edit_url)
    cell_id_predicate = col_predicate_dict["cell id"]
    driver.get(current_page_url)
    res_dict = {
        "cell id": [],  # str
        "deleted": [],  # bool
        "error": [],  # str
    }
    thing_list = WebDriverWait(driver, cont.TIMEOUT_LIMIT).until(
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
            yes_btn = WebDriverWait(driver, cont.TIMEOUT_LIMIT).until(
                EC.element_to_be_clickable(
                    (By.XPATH, f"//a[@class='{cont.YES_BTN_CLASS}']")))
            driver.execute_script("arguments[0].click();", yes_btn)
            # wait until the dialogue disappear
            WebDriverWait(driver, cont.TIMEOUT_LIMIT).until(
                EC.invisibility_of_element_located(
                    (By.XPATH, f"//div[@id='{cont.YES_NO_MODAL_ID}']")))
            res_dict["deleted"] = True
            res_dict["error"] = np.nan
        except Exception as e:
            res_dict["deleted"].append(False)
            res_dict["error"].append(str(e))

    res_df = pd.DataFrame(res_dict)
    return driver, res_df


def delete_words(driver: Remote, course_edit_url, course_db_url: str, word_ids: Union[List[str], Literal["ALL"]]):
    """Deletes words from the Memrise course database.

    Note: The admin user must be logged in the passed driver.

    Args:
        driver (selenium.webdriver.Remote): a selenium webdriver.
        course_edit_url (str): url of the edit page of the course.
        course_db_url (str): url of the database page of the course.
        word_ids (list of str or "ALL"): list of cell ids of words to be deleted or 
        "ALL" to delete all words.

    Returns:
        selenium.webdriver.Remote: the passed driver after deleting the words
        pandas.DataFrame: a dataframe with the result of deleting each word
    """
    driver.get(course_db_url)
    # wait until the search button be clickable
    WebDriverWait(driver, cont.TIMEOUT_LIMIT).until(
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
            thing_list = WebDriverWait(driver, cont.TIMEOUT_LIMIT).until(
                EC.presence_of_all_elements_located(
                    (By.CLASS_NAME, "thing")))
        except TimeoutException:  # empty DB
            return driver, res_df

        while thing_list:
            try:
                driver, res_df_temp = _delete_db_page(driver, course_edit_url)
                res_df = pd.concat([res_df, res_df_temp])
                driver.refresh()
                thing_list = WebDriverWait(driver, cont.TIMEOUT_LIMIT).until(
                EC.presence_of_all_elements_located(
                    (By.CLASS_NAME, "thing")))
            except TimeoutException:  # ? what happens if _delete_db_page raises an error?
                break
        return driver, res_df

    for cell_id in word_ids:
        driver, res_bool, error_str = _delete_one_word_from_db(
            driver, course_edit_url, course_db_url, cell_id)
        res_dict["cell id"].append(cell_id)
        res_dict["deleted"].append(res_bool)
        res_dict["error"].append(error_str)
    res_df = pd.DataFrame(res_dict)
    return driver, res_df


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

    driver.execute_script(cont.UPDATE_CELL_JAVA_SCRIPT, input_element, new_value)
    # wait until you find the now updated text
    updated = False
    while not updated:
        updated = (text_element.text == new_value)

    return driver


def update_words(driver: Remote, course_edit_url: str, word_df: pd.DataFrame):
    """Updates words in the Memrise course.

    Note: The admin user must be logged in the passed driver.

    When you update a word in the level page, it also gets updated in the DB.

    Args:
        driver (selenium.webdriver.Remote): a selenium webdriver.
        course_edit_url (str): url of the edit page of the course.
        word_df (pandas.DataFrame): dataframe of words to be updated in Memrise.

    Returns:
        selenium.webdriver.Remote: the passed driver after updating the words
        pandas.DataFrame: a dataframe with the result of updating each word
    """
    word_df = ut.validate_input(word_df)
    driver.get(course_edit_url)
    driver, column_predicate_dict = ut.cell_col_to_xpath_predicate(
        driver, course_edit_url)
    driver = ut.show_all_level_tables(driver)
    res_dict = {
        "cell id": [],  # str
        "updated": [],  # bool
        "error": [],  # str
    }
    for _, row in word_df.iterrows():
        res_dict["cell id"].append(row["cell id"])
        try:
            cell_id_element = WebDriverWait(driver, cont.TIMEOUT_LIMIT).until(
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
                f"TimeoutException: Word not found within {cont.TIMEOUT_LIMIT} seconds"
            )
        except Exception as e:
            res_dict["updated"].append(False)
            res_dict["error"].append(str(e))
    res_df = pd.DataFrame(res_dict)
    driver = ut.click_save_changes(driver, course_edit_url)

    return driver, res_df

def get_all_words(driver, course_edit_url: str):
    """Returns all words in the Memrise course.

    Note: The admin user must be logged in the passed driver.

    Args:
        driver (selenium.webdriver.Remote): a selenium webdriver.
        course_edit_url (str): url of the edit page of the course.

    Returns:
        selenium.webdriver.Remote: the passed driver after showing all level tables
        pandas.DataFrame: a dataframe with all words in the Memrise course
    """
    # go to the edit page
    driver.get(course_edit_url)
    # show all tables
    driver = ut.show_all_level_tables(driver)
    # get all table element with class="level-things table ui-sortable"
    table_list = WebDriverWait(driver, cont.TIMEOUT_LIMIT).until(
        EC.presence_of_all_elements_located(
            (By.XPATH, "//table[@class='level-things table ui-sortable']")))
    all_words_df = pd.DataFrame({}, columns=COL_LIST)
    if not table_list:
        raise MinNumberOfLevels()
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
        table_df = ut.table_element_to_df(table_element)
        table_df.drop(columns="Unnamed: 0",
                      inplace=True)  # first columns for actions
        table_df["level"] = level_name

        # concat
        if not table_df.empty:
            table_df = table_df[COL_LIST]
            all_words_df = pd.concat([all_words_df, table_df])
    # check dtypes and columns order and index
    columns_with_all_na = all_words_df.columns[all_words_df.isna().all()]
    all_words_df = all_words_df.astype({col: np.float64 for col in columns_with_all_na})
    all_words_df["date modified"] = pd.to_datetime(all_words_df["date modified"])
    all_words_df = all_words_df[COL_LIST].reset_index(drop=True)

    return driver, all_words_df


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
    level_element = WebDriverWait(driver, cont.TIMEOUT_LIMIT).until(
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
    text_area = WebDriverWait(driver, cont.TIMEOUT_LIMIT).until(
        EC.element_to_be_clickable((By.XPATH, '//textarea')))

    # past the csv string of word_df
    word_df_string = word_df.to_csv(index=False, sep="\t", header=False)
    text_area.send_keys(word_df_string)

    # click on add button
    add_btn = driver.find_element_by_xpath("//a[text()='Add']")
    driver.execute_script("arguments[0].click();", add_btn)

    # wait until the dialogue disappear
    WebDriverWait(driver, cont.TIMEOUT_LIMIT).until(
        EC.invisibility_of_element_located(
            (By.XPATH, f"//div[@class='{cont.MODAL_BACKDROP_CLASS}']")))
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
            WebDriverWait(driver, cont.WORD_SEARCH_TIME_OUT).until(
                EC.presence_of_element_located(
                    (By.XPATH, f'//div[text()="{cell_id}"]')))
            res_dict["added"].append(True)
            res_dict["error"].append(np.nan)
        except TimeoutException:
            res_dict["added"].append(False)
            res_dict["error"].append(
                f"TimeoutException: Word not found within {cont.WORD_SEARCH_TIME_OUT} seconds"
            )
        except Exception as e:
            res_dict["added"].append(False)
            res_dict["error"].append(str(e))

    res_df = pd.DataFrame(res_dict)

    return driver, res_df



def add_words(
        driver: Remote,
        course_edit_url: str,
        db_name: str,
        word_df: pd.DataFrame,
        level_word_limit: int
):
    """Adds words to the Memrise course.

    Note: The admin user must be logged in the passed driver.

    First, it checks if there are any empty levels. If there are, it adds words to them.
    After that, it fills the last level if it is not full. Finally, it creates new
    levels as needed.

    Args:
        driver (selenium.webdriver.Remote): a selenium webdriver.
        course_edit_url (str): url of the edit page of the course.
        db_name (str): name of the database of the course on memrise.
            This is found when you click on Databases tab in the edit page. 
        level_word_limit (int): number of words per level.
        word_df (pandas.DataFrame): dataframe of words to be added to Memrise.

    Returns:
        selenium.webdriver.Remote: the passed driver after adding the words
        pandas.DataFrame: a dataframe with the result of adding each word
    """
    word_df = ut.validate_input(word_df)  # only valid
    if word_df.empty:
        res_df = pd.DataFrame({
            "cell id": [],  # str
            "added": [],  # bool
            "error": [],  # str
        })
        return driver, res_df
    # go to the edit page
    driver.get(course_edit_url)
    # loop over levels
    # if the level is empty, add words to it
    # TODO: raise an error saying there is no levels in the course
    level_collapsed_list = WebDriverWait(driver, cont.TIMEOUT_LIMIT).until(
        EC.presence_of_all_elements_located(
            (By.XPATH, "//div[@class='level collapsed']")))
    level_id_list = [
        level_collapsed_element.get_attribute("data-level-id")
        for level_collapsed_element in level_collapsed_list
    ]
    i = 0
    res_df = pd.DataFrame()
    for level_id in level_id_list:
        level_collapsed_element = WebDriverWait(driver, cont.TIMEOUT_LIMIT).until(
            EC.presence_of_element_located(
                (By.XPATH,
                 f"//div[@class='level collapsed' and @data-level-id='{level_id}']")))
        show_btn = level_collapsed_element.find_element_by_xpath(
            ".//a[@class='show-hide btn btn-small']")
        driver.execute_script("arguments[0].click();", show_btn)
        level_word_count = ut.count_level_words(driver, level_id)
        # if the level is empty, add words to it
        if level_word_count == 0 and i < len(word_df):  # only if there are more words
            driver, tmp_res_df = _add_bulk(
                driver, level_id, word_df.iloc[i:i+level_word_limit])
            level_word_count += len(tmp_res_df[tmp_res_df["added"]])
            i += level_word_limit
            res_df = pd.concat([res_df, tmp_res_df])

    # here, level_element is the last level
    # add words to it if it is not full
    if len(level_id_list) > 0:  # so level_id is defined
        if level_word_count < level_word_limit and i < len(word_df):
            n_words_to_add = level_word_limit - level_word_count
            driver, tmp_res_df = _add_bulk(
                driver, level_id, word_df.iloc[i:i+n_words_to_add])
            i += n_words_to_add
            res_df = pd.concat([res_df, tmp_res_df])
    # create new levels if needed
    word_df = word_df.iloc[i:] if i < len(word_df) else pd.DataFrame()
    # cut the remaining words level_word_limit words per level and create new levels
    for i in range(0, len(word_df), level_word_limit):
        batch_df = word_df.iloc[i:i+level_word_limit]
        # create a new level
        driver = ut.create_new_level(driver, db_name)
        # the page will refresh and the new level will be the only level not collapsed
        # wait until the page reload (the button is not visible)
        WebDriverWait(driver, cont.TIMEOUT_LIMIT).until(
            EC.invisibility_of_element_located(
                (By.XPATH,
                 f"//a[@data-role='level-add' and contains(text(),'{db_name}')]")))
        # get level options
        level_element = WebDriverWait(driver, cont.TIMEOUT_LIMIT).until(
            EC.presence_of_element_located(
                (By.XPATH, "//div[@class='level']")))
        level_id = level_element.get_attribute("data-level-id")
        # add words to the new level
        driver, tmp_res_df = _add_bulk(driver, level_id, batch_df)
        res_df = pd.concat([res_df, tmp_res_df])

    return driver, res_df
