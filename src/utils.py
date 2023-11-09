"""Utility functions."""

from typing import Union
import pandas as pd


def semi_join(df1:pd.DataFrame, df2:pd.DataFrame, on:Union(str, list)):
    """Returns the rows of df1 whose values in a certain column (or more) exist on df2.

    Note: If the relation df1 to df2 is one-to-many, no duplicates will occur in the 
    result.

    Args:
        df1 (pandas.DataFrame): left dataframe.
        df2 (pandas.DataFrame): right dataframe.
        on (str or list): column(s) to join on.

    Returns:
        pandas.DataFrame: rows of df1 whose values in a certain column (or more) exist 
        on df2.
    """
    on = on if isinstance(on, list) else [on]
    df2_on = df2[on].drop_duplicates()
    df1_only = df1.merge(df2_on, on=on, how="inner")

    return df1_only


def anti_join(df1:pd.DataFrame, df2:pd.DataFrame, on:Union(str, list)):
    """Returns the rows of df1 whose values in a certain column (or more) do not exist 
    on df2.

    Args:
        df1 (pandas.DataFrame): left dataframe.
        df2 (pandas.DataFrame): right dataframe.
        on (str or list): column(s) to join on.

    Returns:
        pandas.DataFrame: rows of df1 whose values in a certain column (or more) do not 
        exist on df2.
    """
    on = on if isinstance(on, list) else [on]
    intersect_cols_not_on = [col for col in df1.columns 
                             if col in df2.columns and col not in on]
    df_merged = df1.merge(df2, on=on, how="left", indicator=True)
    df1_only = df_merged[df_merged["_merge"] == "left_only"]
    # drop "_merge" and columns in intersect_cols + _y
    df1_only = df1_only.drop(
        columns=["_merge"]+[col+"_y" for col in intersect_cols_not_on])
    df1_only = df1_only.rename(
        columns={col+"_x": col for col in intersect_cols_not_on})

    return df1_only
