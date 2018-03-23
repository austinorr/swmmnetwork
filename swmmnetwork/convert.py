
import pandas
import networkx as nx

import hymo

from .util import _upper_case_column, _validate_hymo_inp
from .compat import from_pandas_edgelist, set_node_attributes


SWMM_LINK_TYPES = [
    'weirs',
    'orifices',
    'conduits',
    'outlets',
    'pumps',
]

SWMM_NODE_TYPES = [
    'subcatchments',
    'junctions',
    'outfalls',
    'dividers',
    'storage',
]


def nodes_to_df(G, index_col=None):
    ls = []
    for node in G.nodes(data=True):
        df = {}
        n, data = node
        if index_col is not None:
            df[index_col] = str(n)
        df['from'] = str(n)
        df['to'] = str(sorted(G.successors(n)))
        df['type'] = 'node'
        df.update(data)
        ls.append(df)
    return pandas.DataFrame(ls)


def edges_to_df(G):
    ls = []
    for edge in G.edges(data=True):
        df = {}
        _from, _to, data = edge
        df['from'] = str(_from)
        df['to'] = str(_to)
        df['type'] = 'link'
        df.update(data)
        ls.append(df)
    return pandas.DataFrame(ls)


def network_to_df(G, index_col=None):
    df = (
        pandas.concat([nodes_to_df(G, index_col), edges_to_df(G)])
        .reset_index(drop=True)
    )
    if index_col is not None:
        df = df.set_index(index_col)
        df.index = df.index.map(str)
        df = df.sort_index()
    return df


def pandas_edgelist_from_swmm_inp(inp):
    """
    """
    inp = _validate_hymo_inp(inp)

    catchment_links = (
        inp.subcatchments
        .pipe(_upper_case_column, cols='Outlet', include_index=True)
        .assign(Inlet_Node=lambda df: df.index)
        .assign(id=lambda df: df.index.map(lambda s: '^' + s))
        .assign(xtype='dt')
        .rename(columns={'Outlet': 'Outlet_Node'})
        .loc[:, ['Inlet_Node', 'Outlet_Node', 'xtype', 'id']]
        .rename(columns=lambda s: s.lower())
    )

    edge_types = SWMM_LINK_TYPES

    edge_dfs = []
    for xtype in edge_types:
        df = getattr(inp, xtype, None)
        if df is not None:
            df = (
                df
                .rename(columns={'From_Node': 'Inlet_Node', 'To_Node': 'Outlet_Node'})
                .pipe(_upper_case_column, cols=['Inlet_Node', 'Outlet_Node'], include_index=True)
                .loc[:, ['Inlet_Node', 'Outlet_Node']]
                .assign(id=lambda df: df.index)
                .assign(xtype=xtype if xtype[-1] != 's' else xtype[:-1])
                .loc[:, ['Inlet_Node', 'Outlet_Node', 'xtype', 'id']]
                .rename(columns=lambda s: s.lower())
            )

            edge_dfs.append(df)

    edges = pandas.concat([catchment_links] + edge_dfs).astype(str)

    return edges


def pandas_edgelist_to_edgelist(df, source='source', target='target', cols=None):
    edges = df.set_index([source, target])
    if cols is not None:
        if isinstance(cols, str):
            cols = [cols]
        edges = edges.loc[:, cols]
    edge_list = []
    for index, row in edges.iterrows():
        _to, _from = index
        data = row.to_dict()
        edge_list.append([_to, _from, data])
    return edge_list


def pandas_nodelist_to_nodelist(df):

    return list(df.to_dict('index').items())


def pandas_node_attrs_from_swmm_inp(inp):
    """
    """

    inp = _validate_hymo_inp(inp)

    node_types = SWMM_NODE_TYPES
    node_dfs = []
    for xtype in node_types:
        df = getattr(inp, xtype, None)
        if df is not None:
            df = (
                df
                .pipe(_upper_case_column, include_index=True)
                .assign(xtype=xtype if xtype[-1] != 's' else xtype[:-1])
                .loc[:, ['xtype']]
                .rename(columns=lambda s: s.lower())
            )
            node_dfs.append(df)

    return pandas.concat(node_dfs).astype(str)


def add_edges_from_swmm_inp(G, inp):
    """Add the edges and nodes from a SWMM 5.1 input file.

    Parameters
    ----------
    G : nx.Graph-like object
    inp : file_path or hymo.SWMMInpFile
    """

    inp = _validate_hymo_inp(inp)

    df_edge_list = pandas_edgelist_from_swmm_inp(inp=inp)

    edge_list = pandas_edgelist_to_edgelist(df_edge_list,
                                            source='inlet_node',
                                            target='outlet_node')

    G.add_edges_from(edge_list)

    df_node_attrs = pandas_node_attrs_from_swmm_inp(inp=inp).to_dict('index')
    set_node_attributes(G, values=df_node_attrs)


def from_swmm_inp(inp, create_using=None):
    """Create new nx.Graph-like object from a SWMM5.1 inp file

    Parameters
    ----------
    inp : file_path or hymo.SWMMInpFile
    create_using : nx.Graph-like object, optional (default=None)
        the type of graph to make. If None is specified, then this
        function defaults to an nx.MultiDiGraph() instance

    Returns
    -------
    Graph

    Reference
    ---------

    This function is meant to be similar to the nx.from_pandas_edgelist()


    """

    inp = _validate_hymo_inp(inp)

    if create_using is None:
        create_using = nx.MultiDiGraph()

    df_edge_list = pandas_edgelist_from_swmm_inp(inp=inp)

    G = from_pandas_edgelist(df_edge_list,
                             source='inlet_node',
                             target='outlet_node',
                             edge_attr=True,
                             create_using=create_using,
                             )

    df_node_attrs = pandas_node_attrs_from_swmm_inp(inp=inp).to_dict('index')
    set_node_attributes(G, values=df_node_attrs)

    return G


def swmm_inp_layout_to_pos(inp):
    """Reads and converts swmm node coordinates and subcatchment from inp
    file to networkx drawing `pos` format, i.e., a dict of node names with
    x, y coordinates as values.
    Parameters
    ----------
    inp : string or hymo.SwmmInputFile
        this file will be read to pull the node coordinates and subcatchment
        positions. Polygons are converted to coordinate pairs through their
        centroid.

    Returns
    -------
    dict suitable for use as the `pos` kwarg of networkx drawing methods.
    """

    inp = _validate_hymo_inp(inp)

    coords = inp.coordinates.pipe(_upper_case_column, include_index=True)
    polys = inp.polygons.pipe(_upper_case_column, include_index=True)

    pos = (
        coords
        .astype(float)
        .append(
            polys
            .astype(float)
            .groupby(polys.index)
            .mean())
        .T
        .to_dict('list')
    )

    return {str(k): list(map(float, v)) for k, v in pos.items()}
