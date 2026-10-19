"""Row order of the generated tables."""


def by_count(df, count_column, name_column):
    """Sort by `count_column`, highest first; ties by `name_column`, ignoring case.

    A fixed order for ties keeps the files the same between runs, so that a new
    run only shows the rows that really changed.
    """
    if df.empty:
        return df
    order = df.assign(_name=df[name_column].astype(str).str.casefold())
    order = order.sort_values([count_column, '_name'], ascending=[False, True], kind='mergesort')
    return order.drop(columns='_name')
