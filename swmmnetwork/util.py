
import pandas

import networkx as nx

import hymo


def find_cycle(G, **kwargs):
    """Wraps networkx.find_cycle to return empty list
    if no cycle is found.
    """
    try:
        return list(nx.find_cycle(G, **kwargs))

    except nx.exception.NetworkXNoCycle:
        return []


def validate_swmmnetwork(G):
    """Checks if there is a cycle, and prints a helpful
    message if there is.
    """
    simplecycles, findcycles = (
        list(nx.simple_cycles(G)), find_cycle(G)
    )

    if simplecycles or findcycles:
        e = (
            '\nCannot sort nodes due to network cycle.'
            '\nThe following nodes form a cycle in the network:'
            '\nNode Cycles [name]: {}'
            '\nLink Cycles [(from, to)]: {}'.format(
                simplecycles, findcycles)
        )
        raise Exception(e)
    return


def _upper_case_index(df):
    """Converts a pandas.DataFrame.index to an uppercase string
    """
    if len(df) == 0:
        return df

    df = df.copy()
    df.index = df.index.map(str).str.upper()
    return df


def _upper_case_column(df, cols):
    """Converts contents of pandas.Series to uppercase string

    Parameters
    ----------
    df : pandas.DataFrame()
    cols : string or list
        column names that will be converted to uppercase

    Returns
    -------
    pandas.DataFrame()
    """
    if len(df) == 0:
        return df

    df = df.copy()
    if isinstance(cols, str):
        cols = [cols]
    for col in cols:
        if col in df.columns:
            df[col] = df[col].map(str).str.upper()
    return df


def _safe_divide(x, y):
    """This returns zero if the denominator is zero
    """
    if y == 0:
        return 0
    return x / y


def _validate_hymo_inp(inp):
    if isinstance(inp, hymo.SWMMInpFile):
        return inp
    elif isinstance(inp, str):
        return hymo.SWMMInpFile(inp)
    else:
        raise ValueError('invalid type for `inp`: {}'.format(type(inp)))


def _validate_hymo_rpt(rpt):
    if isinstance(rpt, hymo.SWMMReportFile):
        return rpt
    elif isinstance(rpt, str):
        return hymo.SWMMReportFile(rpt)
    else:
        raise ValueError('invalid type for `rpt`: {}'.format(type(rpt)))


def _to_list(val):
    if val is None:
        return []
    elif isinstance(val, str):
        val = [val]
    try:
        assert isinstance(val, list)
    except:
        raise TypeError('Pass {} as a list.'.format(name))

    return val
