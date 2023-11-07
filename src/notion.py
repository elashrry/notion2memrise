"""This module contains functions to get data from Notion via API.

I will get all data from notion every time to check if there is any deletion
done on notion and consequently make the changes in memrise.
"""

import os
import requests
import pandas as pd
# ? the right way to import from constants ?
from .constants import COL_LIST

NOTION_SECRET = os.environ.get("NOTION_SECRET")
NOTION_VERSION = "2022-06-28"  # Notion API version from their website
# ? can I get the ID using Notion integration?
NOTION_DATABASE_ID = "7c83b2ef86e941b986e8c8461fb5134d"

HEADERS = {
    "Authorization": f"Bearer {NOTION_SECRET}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}
ENDPOINT = f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query"

DATE_COL_LIST = ["date created", "date modified"]  # only used here

def get_data_from_notion():
    """Gets and processes data from Notion via API.

    Returns:
        pandas.DataFrame: dataframe of the entries in the Notion database.
    """
    response = requests.post(
        ENDPOINT,
        headers=HEADERS,
        timeout=10,
    )
    df_clean = handle_response(response)
    has_more = response.json()["has_more"]
    while has_more:
        next_cursor = response.json()["next_cursor"]
        response = requests.post(
            ENDPOINT,
            headers=HEADERS,
            timeout=10,
            json={
                "start_cursor": next_cursor
            },
        )
        df_clean = pd.concat([df_clean, handle_response(response)])
        has_more = response.json()["has_more"]
    return df_clean




def handle_response(response):
    """Handles the response from the Notion API.

    Args:
        response (requests.Response): response from the Notion API.

    Returns:
        pandas.DataFrame: dataframe of the entries in the Notion database.
    """
    results_list = response.json()["results"]
    df = pd.DataFrame(results_list)
    # we only need id and properties
    df_copy = df[["id", "properties"]]
    df_copy.loc[:,
                "properties"] = df_copy["properties"].apply(handle_properties)
    # add id to properties which will be turned into a new dataframe
    # also name it cell id
    df_copy.loc[:, "properties"] = df_copy.apply(lambda row: {
        "cell id": row["id"],
        **row["properties"]
    },
                                                 axis=1)
    new_df = pd.DataFrame(df_copy["properties"].tolist())
    for col in new_df:
        new_df[col] = new_df[col].str.strip()
    for col in DATE_COL_LIST:
        new_df[col] = pd.to_datetime(new_df[col])

    return new_df[COL_LIST]


def handle_properties(properties_dict):
    """Handles the properties of a Notion entry from API.

    Properties returned from the API contain a lot of information. We are only
    interested in the content of the property, not the type or id.

    Args:
        properties_dict (dict): properties of a Notion entry.

    Returns:
        dict: properties of a Notion entry.
    """
    new_prop_dict = {}
    for prop, prop_dict in properties_dict.items():
        new_prop_dict[prop] = get_property_content(prop_dict)

    return new_prop_dict


def get_property_content(property_dict):
    """Gets the content of a Notion property.

    A Notion property is a dictionary with a key "type" and a value that
    indicates the type of the property. The content of the property is stored
    in a key that has the same name as the type.

    This function handles the following types:
    - rich_text
    - title
    - select
    - multi_select

    For other types, the function returns the value stored in the key that has
    the same name as the type. If there is no such key, it returns None.

    It will be updated as we come across more types.

    Args:
        property_dict (dict): property of a Notion entry.

    Returns:
        str: content of the property.
    """
    # most cell will have the content in a key
    # and that key is stored in property_dict["type"]
    # we treat exceptions
    property_type = property_dict["type"]
    if property_type in ["rich_text", "title"]:
        rich_text_list = property_dict[property_type]
        if len(rich_text_list) > 0:
            return rich_text_list[0]["plain_text"]
        else:
            return None
    elif property_type == "select":
        select_dict = property_dict.get("select", {})
        # if None selected, select_dict will be None
        select_dict = {} if select_dict is None else select_dict
        return select_dict.get("name", None)
    elif property_type == "multi_select":
        select_list = [
            select["name"] for select in property_dict["multi_select"]
        ]
        return ", ".join(select_list)
    else:
        return property_dict.get(property_type, None)
