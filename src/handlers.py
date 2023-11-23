"""This module contains the functions that handle the data from Notion and Memrise."""

import numpy as np
import pandas as pd
from selenium.webdriver import Remote

from src import memrise as mem
from src import utils as ut

COL_ORDER_LIST = ["French", "cell id", "action", "success", "error"]

def notion2memrise(driver: Remote, notion_df: pd.DataFrame):
    """Handles the data from Notion and Memrise.

    Creates a Selenium driver, signs in to Memrise, gets all the words from Memrise,
    handles the duplicates from Notion, handles the words deleted from Notion, handles
    the words that were already on Memrise and got updated on Notion, handles the new
    words from Notion, and finally quits the driver.

    Args:
        driver (selenium.webdriver.Remote): driver of the browser.
        notion_df (pandas.DataFrame): dataframe of the entries in the Notion database.

    Returns:
        selenium.webdriver.Remote: the passed driver after the words are added, updated,
        or deleted.
    """
    notion_df = mem.validate_input(notion_df)
    if notion_df.empty:
        print("Notion Database is empty.")
        return

    global_res_df = pd.DataFrame({col: [] for col in COL_ORDER_LIST})
    # sort from oldest to newest so that older words get added first later
    notion_df.sort_values(by="date modified", inplace=True, ascending=True)

    # handle duplicates from notion (case insensitive)
    # print them out to the user and keep the most recent one
    notion_df, duplicate_res_df = handle_notion_duplicates(notion_df)
    global_res_df = pd.concat([global_res_df, duplicate_res_df])

    # read words from memrise
    driver, memrise_df = mem.get_all_words(driver)

    if not memrise_df.empty:
        memrise_df.sort_values(by="date modified", inplace=True, ascending=False)
        memrise_df["source"] = "memrise"
        memrise_most_recent = pd.to_datetime(memrise_df.iloc[0]["date modified"])
        # handle words deleted from notion
        deleted_from_notion_df = ut.anti_join(memrise_df, notion_df, "cell id")
        driver, delete_res_df = handle_deleted_from_notion(
            driver, deleted_from_notion_df)
        global_res_df = pd.concat([global_res_df, delete_res_df])
        # get new words from notion
        notion_df = notion_df[notion_df["date modified"] > memrise_most_recent]
        # handle words that were already on memrise and got updated on notion
        update_from_notion_df = ut.semi_join(notion_df, memrise_df, "cell id")
        driver, updated_res_df = handle_updated_from_notion(
            driver, update_from_notion_df)
        global_res_df = pd.concat([global_res_df, updated_res_df])
        # driver = mem.click_save_changes(driver)
        # update notion_df to only contain the words that are not in memrise
        notion_df = notion_df[np.logical_not(
            notion_df["cell id"].isin(update_from_notion_df["cell id"]))]

    # handle new words from notion, drop the ones that already got updated
    driver, added_res_df = handle_new_from_notion(driver, notion_df)
    global_res_df = pd.concat([global_res_df, added_res_df])
    now_timestamp = pd.to_datetime("now").strftime("%Y-%m-%d %H:%M:%S")
    global_res_df.to_csv(f"logs/results_{now_timestamp}.csv", index=False)
    print("All done!")

    return driver

def handle_notion_duplicates(notion_df: pd.DataFrame):
    """Handles the duplicates from Notion (case insensitive).

    Duplicates are checked as case insensitive in the `French` column. The most recent
    duplicate is kept and the rest are dropped.

    Args:
        notion_df (pandas.DataFrame): dataframe of the entries in the Notion database.

    Returns:
        pandas.DataFrame: dataframe of the entries in the Notion database without the 
        duplicates.
        pandas.DataFrame: dataframe of the duplicates that were dropped. It contains the
        dropped words and the action that was taken. Columns:
            - French: dropped word.
            - cell id: ID of the word on Notion.
            - action: action taken on the word, in this case "duplicate_drop".
            - success: True.
    """
    notion_df = mem.validate_input(notion_df)
    notion_df_copy = notion_df.copy()
    notion_df_copy["French"] = notion_df_copy["French"].str.lower()
    notion_duplicate_df = notion_df_copy[
        notion_df_copy.duplicated(subset=["French"], keep="last")]
    notion_df = notion_df[np.logical_not(notion_df["cell id"].isin(
        notion_duplicate_df["cell id"]))]
    if notion_duplicate_df.empty:
        return notion_df, pd.DataFrame(columns=COL_ORDER_LIST)

    print("Duplicate words from Notion (case insensitive):")
    print("**We kept the most recent one**")
    print(notion_duplicate_df["French"].to_string(index=False))
    print("-"*10, "\n")
    duplicate_res_df = notion_duplicate_df[["French", "cell id"]]
    duplicate_res_df[["action", "success"]] = "duplicate_drop", True

    return notion_df, duplicate_res_df[COL_ORDER_LIST]

def handle_deleted_from_notion(driver: Remote, deleted_from_notion_df: pd.DataFrame):
    """Handles the words deleted from Notion.

    Args:
        driver (selenium.webdriver.Remote): driver of the browser.
        deleted_from_notion_df (pandas.DataFrame): dataframe of the words deleted from 
            Notion.

    Returns:
        selenium.webdriver.Remote: the passed driver after the words are deleted.
        pandas.DataFrame: dataframe of the words deleted from Notion. It contains the
        deleted words and the action that was taken. Columns:
            - French: deleted word.
            - cell id: ID of the word on Notion.
            - action: action taken on the word, in this case "delete".
            - success: True if the word was deleted successfully, False otherwise.
            - error: error message if the word was not deleted successfully, NaN
            otherwise.
    """
    deleted_from_notion_df = mem.validate_input(deleted_from_notion_df)
    if deleted_from_notion_df.empty:
        return driver, pd.DataFrame(columns=COL_ORDER_LIST)

    driver, delete_res_df = mem.delete_words(
        driver, deleted_from_notion_df["cell id"].tolist())
    delete_res_df = delete_res_df.merge(
        deleted_from_notion_df, on="cell id", how="left")
    deleted_words_df = delete_res_df[delete_res_df["deleted"]]
    not_deleted_words_df = delete_res_df[
        np.logical_not(delete_res_df["deleted"])]
    if not deleted_words_df.empty:
        print("Deleted words from Memrise:")
        print(deleted_words_df["French"].to_string(index=False))
    if not not_deleted_words_df.empty:
        print("Not deleted words from Memrise:")
        print(not_deleted_words_df[["French", "error"]].to_string(index=False))
    print("-"*10, "\n")
    delete_res_df = delete_res_df[["French", "cell id", "deleted", "error"]]
    delete_res_df["action"] = "delete"
    delete_res_df.rename(columns={"deleted": "success"}, inplace=True)
    driver = mem.click_save_changes(driver)

    return driver, delete_res_df[COL_ORDER_LIST]

def handle_updated_from_notion(driver: Remote, update_from_notion_df: pd.DataFrame):
    """Handles the words that were already on Memrise and got updated on Notion.

    Args:
        driver (selenium.webdriver.Remote): driver of the browser.
        update_from_notion_df (pandas.DataFrame): dataframe of the words that were already
            on Memrise and got updated on Notion.

    Returns:
        selenium.webdriver.Remote: the passed driver after the words are updated.
        pandas.DataFrame: dataframe of the words that were already on Memrise and got 
        updated on Notion. 
            It contains the updated words and the action that was taken. 
            Columns:
                - French: updated word.
                - cell id: ID of the word on Notion.  
                - action: action taken on the word, in this case "update".  
                - success: True if the word was updated successfully, False otherwise.
                - error: error message if the word was not updated successfully, NaN
                otherwise.
    """
    update_from_notion_df = mem.validate_input(update_from_notion_df)
    if update_from_notion_df.empty:
        return driver, pd.DataFrame(columns=COL_ORDER_LIST)
    driver, updated_res_df = mem.update_words(driver, update_from_notion_df)
    updated_res_df = updated_res_df.merge(
        update_from_notion_df, on="cell id", how="left")
    updated_words_df = updated_res_df[updated_res_df["updated"]]
    not_updated_words_df = updated_res_df[np.logical_not(updated_res_df["updated"])]
    if not updated_words_df.empty:
        print("Updated words on Memrise:")
        print(updated_words_df["French"].to_string(index=False))
    if not not_updated_words_df.empty:
        print("Not updated words on Memrise:")
        print(not_updated_words_df[["French", "error"]].to_string(index=False))
    print("-"*10, "\n")
    updated_res_df = updated_res_df[["French", "cell id", "updated", "error"]]
    updated_res_df["action"] = "update"
    updated_res_df.rename(columns={"updated": "success"}, inplace=True)
    # driver = mem.click_save_changes(driver)

    return driver, updated_res_df[COL_ORDER_LIST]

def handle_new_from_notion(driver: Remote, new_from_notion_df: pd.DataFrame):
    """Handles the new words from Notion.

    Args:
        driver (selenium.webdriver.Remote): driver of the browser.
        new_from_notion_df (pandas.DataFrame): dataframe of the new words from Notion.

    Returns:
        selenium.webdriver.Remote: the passed driver after the words are added.
        pandas.DataFrame: dataframe of the new words from Notion. It contains the new
        words and the action that was taken. Columns:
            - French: new word.
            - cell id: ID of the word on Notion.
            - action: action taken on the word, in this case "add".
            - success: True if the word was added successfully, False otherwise.
            - error: error message if the word was not added successfully, NaN
            otherwise.
    """
    new_from_notion_df = mem.validate_input(new_from_notion_df)
    if new_from_notion_df.empty:
        return driver, pd.DataFrame(columns=COL_ORDER_LIST)
    driver, added_res_df = mem.add_words(driver, new_from_notion_df)
    added_res_df = added_res_df.merge(new_from_notion_df, on="cell id", how="left")
    added_words_df = added_res_df[added_res_df["added"]]
    not_added_words_df = added_res_df[np.logical_not(added_res_df["added"])]
    if not added_words_df.empty:
        print("Added words to Memrise:")
        print(added_words_df["French"].to_string(index=False))
    if not not_added_words_df.empty:
        print("Not added words to Memrise:")
        print(not_added_words_df[["French", "error"]].to_string(index=False))
    print("-"*10, "\n")
    added_res_df = added_res_df[["French", "cell id", "added", "error"]]
    added_res_df["action"] = "add"
    added_res_df.rename(columns={"added": "success"}, inplace=True)
    driver = mem.click_save_changes(driver)

    return driver, added_res_df[COL_ORDER_LIST]
