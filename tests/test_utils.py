import pandas as pd
from src.utils import semi_join, anti_join


def test_semi_join():
    # case when on is a string
    df1 = pd.DataFrame({
        'id': [1, 2, 3, 4],
        'name': ['Alice', 'Bob', 'Charlie', 'David']
    })

    df2 = pd.DataFrame({
        'id': [3, 4, 5, 6],
        'name': ['Charlie', 'David', 'Eve', 'Frank']
    })
    df1_only = semi_join(df1, df2, 'id')
    assert df1_only.reset_index(drop=True).equals(df1.iloc[2:].reset_index(drop=True))

    # case when on is a list
    # redefine df1 and df2, just in case
    df1 = pd.DataFrame({
        'id': [1, 2, 3, 4],
        'name': ['Alice', 'Bob', 'Charlie', 'David']
    })

    df2 = pd.DataFrame({
        'id': [3, 4, 5, 6],
        'name': ['Charlie', 'David', 'Eve', 'Frank']
    })
    df1['key'] = ['key1', 'key2', 'key3', 'key4']
    df2['key'] = ['key3', 'key4', 'key5', 'key6']
    df1_only = semi_join(df1, df2, ['id', 'key'])
    assert df1_only.reset_index(drop=True).equals(df1.iloc[2:].reset_index(drop=True))

def test_anti_join():
    # case when on is a string
    df1 = pd.DataFrame({
        'id': [1, 2, 3, 4],
        'name': ['Alice', 'Bob', 'Charlie', 'David']
    })

    df2 = pd.DataFrame({
        'id': [3, 4, 5, 6],
        'name': ['Charlie', 'David', 'Eve', 'Frank']
    })
    df1_only = anti_join(df1, df2, 'id')
    assert df1_only.reset_index(drop=True).equals(df1.iloc[:2].reset_index(drop=True))

    # case when on is a list
    # redefine df1 and df2, just in case
    df1 = pd.DataFrame({
        'id': [1, 2, 3, 4],
        'name': ['Alice', 'Bob', 'Charlie', 'David']
    })

    df2 = pd.DataFrame({
        'id': [3, 4, 5, 6],
        'name': ['Charlie', 'David', 'Eve', 'Frank']
    })
    df1['key'] = ['key1', 'key2', 'key3', 'key4']
    df2['key'] = ['key3', 'key4', 'key5', 'key6']
    df1_only = anti_join(df1, df2, ['id', 'key'])
    assert df1_only.reset_index(drop=True).equals(df1.iloc[:2].reset_index(drop=True))
    