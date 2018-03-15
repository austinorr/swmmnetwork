
import pandas
import numpy

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


def _upper_case_column(df, cols=None, include_index=False):
    """Converts contents of pandas.Series to uppercase string

    Parameters
    ----------
    df : pandas.DataFrame()
    cols : string or list, optional (default=None)
        column names that will be converted to uppercase
    unclude_index : bool, optional (default=False)
        whether to convert the index to an uppercase string

    Returns
    -------
    pandas.DataFrame()
    """
    if len(df) == 0:
        return df

    df = df.copy()

    if cols is not None:
        if isinstance(cols, str):
            cols = [cols]

        for col in cols:
            if col in df.columns:
                df[col] = df[col].map(str).str.upper()

    if include_index:
        df.index = df.index.map(str).str.upper()

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
        raise TypeError('Pass {} as a list.'.format(val))

    return val


def sigfigs(x, n=None):
    if n is None:
        return x
    if isinstance(x, (int, float, numpy.number)):
        rnd = n - numpy.floor(numpy.log10(numpy.abs(x)) if x != 0 else 0) - 1
        return numpy.around(x, int(rnd))
    if isinstance(x, list):
        return [sigfigs(i, n) for i in x]
    if isinstance(x, numpy.ndarray):
        tmp = numpy.floor(numpy.log10(numpy.abs(x), where=(x != 0)))
        tmp[~numpy.isfinite(tmp)] = 0
        rnd = n - tmp - 1
        return numpy.array(list(map(numpy.around, x, rnd.astype(int))))
    if isinstance(x, pandas.Series):
        return pandas.Series(data=sigfigs(x.values, n), index=x.index, name=x.name)
    if isinstance(x, pandas.DataFrame):
        out = []
        nums = x.select_dtypes(include=numpy.number).copy()
        others = x.select_dtypes(exclude=numpy.number).copy()
        for c in nums:
            out.append(sigfigs(nums[c], n))
        out.append(others)
        df = pandas.concat(out, axis=1)
        return df.reindex(x.columns, axis=1)
