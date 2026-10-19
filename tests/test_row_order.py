"""Generated tables have a fixed row order, so that new runs only show real changes."""

import pandas as pd

from scripts.lib.tables import by_count


def test_highest_count_first_and_ties_by_name_ignoring_case():
    df = pd.DataFrame({'username': ['zoe', 'Bob', 'alice', 'carl'], 'total_commits': [3, 5, 3, 3]})
    assert list(by_count(df, 'total_commits', 'username')['username']) == ['Bob', 'alice', 'carl', 'zoe']


def test_the_order_does_not_depend_on_the_input_order():
    df = pd.DataFrame({'organisation': ['b', 'a', 'c'], 'total_pull_requests': [1, 1, 1]})
    first = by_count(df, 'total_pull_requests', 'organisation')
    second = by_count(df.iloc[::-1], 'total_pull_requests', 'organisation')
    assert list(first['organisation']) == list(second['organisation']) == ['a', 'b', 'c']


def test_an_empty_table_stays_empty():
    df = pd.DataFrame(columns=['username', 'total_commits'])
    assert by_count(df, 'total_commits', 'username').empty
