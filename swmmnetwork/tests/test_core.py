import pytest
import networkx as nx
import swmmnetwork
from swmmnetwork import core

GT = nx.MultiDiGraph([
    (1, 0, {'name': 'C-1', 'value': 2, 'weight': 5}),
    (2, 0, {'name': 'C-2', 'value': 3, 'weight': 2}),
    (0, 3, {'name': 'BR-3-TR', 'value': 4, 'weight': 10}),
    (0, 3, {'name': 'DD-5-TR', 'value': 7, 'weight': 6}),
    (0, 4, {'name': 'OF-4-INF', 'value': 5, 'weight': 3}),
])

'''
Test graph GT looks like this:
      1    2
       \  /
        0
     //  \
    3     4
flow direction is top to bottom
'''


@pytest.fixture
def GT_VOL():
    GT = nx.MultiDiGraph()
    l = [
        (1, 0, {'name': 'C-1', 'vol': 9}),
        (2, 0, {'name': 'C-2', 'vol': 3}),
        (0, 3, {'name': 'BR-3-TR', 'vol': 9}),
        (0, 3, {'name': 'DD-5-TR', 'vol': 2}),
        (0, 4, {'name': 'OF-4-INF', 'vol': 1}),
    ]
    n = [
        (1, {'poc1': 3, 'vol': 9}),
        (2, {'poc1': 3, 'vol': 3})
    ]
    GT.add_edges_from(l)
    GT.add_nodes_from(n)

    exp = {
        'node_vol_gain': 0,
        'poc1_conc_eff': 0.5,
        'poc1_conc_in': 0.5,
        'poc1_conc_pct_reduced': 0.0,
        'poc1_load_eff': 5.5,
        'poc1_load_in': 6.0,
        'poc1_load_pct_reduced': (0.5 / 6) * 100,
        'poc1_load_reduced': 0.5,
        'vol_capture': 12,
        'vol_eff': 11,
        'vol_in': 12,
        'vol_out': 12,
        'vol_pct_capture': 100.0,
        'vol_pct_reduced': 0.5 / 6 * 100,
        'vol_pct_treated': 100 - (1 / 12 * 100),
        'vol_reduced': 1,
        'vol_treated': 11
    }

    return GT, exp


@pytest.mark.parametrize(('G', 'node', 'attr', 'dct', 'exp'), [
    (GT.to_undirected(), 0, 'weight', dict(method='edges', filter_key=None,
                                           include_filter_flags=None, exclude_filter_flags=None), 26),
    (GT.to_undirected(), 0, 'value',  dict(method='edges', filter_key=None,
                                           include_filter_flags=None, exclude_filter_flags=None), 21),
    (GT.to_undirected(), 0, 'weight', dict(method='edges', filter_key='name',
                                           include_filter_flags=['1', '5'], exclude_filter_flags=None), 11),
    (GT.to_undirected(), 0, 'weight', dict(method='edges', filter_key='name',
                                           include_filter_flags=None, exclude_filter_flags=['4', '2']), 21),
    (GT.to_undirected(), 0, 'weight', dict(method='edges', filter_key='name', include_filter_flags=['1', '2', '3', '5'],
                                           exclude_filter_flags=['1', '3']), 8),
    (GT, 0, 'weight', dict(method='out_edges', filter_key=None,
                           include_filter_flags=None, exclude_filter_flags=None), 19),
    (GT, 0, 'value',  dict(method='out_edges', filter_key=None,
                           include_filter_flags=None, exclude_filter_flags=None), 16),
    (GT, 0, 'weight', dict(method='out_edges', filter_key='name',
                           include_filter_flags=['1', '5'], exclude_filter_flags=None), 6),
    (GT, 0, 'weight', dict(method='out_edges', filter_key='name',
                           include_filter_flags=None, exclude_filter_flags=['4', '2']), 16),
    (GT, 0, 'weight', dict(method='out_edges', filter_key='name', include_filter_flags=['1', '2', '3', '5'],
                           exclude_filter_flags=['1', '3']), 6),
    (GT, 0, 'weight', dict(method='in_edges', filter_key=None,
                           include_filter_flags=None, exclude_filter_flags=None), 7),
    (GT, 0, 'value',  dict(method='in_edges', filter_key=None,
                           include_filter_flags=None, exclude_filter_flags=None), 5),
    (GT, 0, 'weight', dict(method='in_edges', filter_key='name',
                           include_filter_flags=['1', '5'], exclude_filter_flags=None), 5),
    (GT, 0, 'weight', dict(method='in_edges', filter_key='name',
                           include_filter_flags=None, exclude_filter_flags=['4', '2']), 5),
    (GT, 0, 'weight', dict(method='in_edges', filter_key='name', include_filter_flags=['1', '2', '3', '5'],
                           exclude_filter_flags=['1', '3']), 2),
    (GT.to_undirected(), 0, 'weight', dict(method='edges', filter_key='name',
                                           include_filter_flags=['BR', 'DD'], exclude_filter_flags=None), 16),
    (GT.to_undirected(), 0, 'weight', dict(method='edges', filter_key='name',
                                           include_filter_flags=None, exclude_filter_flags=['INF']), 23),
    (GT.to_undirected(), 0, 'weight', dict(method='edges', filter_key='name', include_filter_flags=['TR'],
                                           exclude_filter_flags=['DD']), 10),
    (GT, 0, 'weight', dict(method='out_edges', filter_key='name',
                           include_filter_flags=['1', '5', 'INF'], exclude_filter_flags=None), 9),
    (GT, 0, 'weight', dict(method='in_edges', filter_key='name',
                           include_filter_flags=['C', '1'], exclude_filter_flags=None), 7),
])
def test_sum_edge_attr(G, node, attr, dct, exp):
    assert core._sum_edge_attr(G, node, attr, **dct) == exp


def test_solve_node(GT_VOL):
    G, exp = GT_VOL

    nodes = [1, 2, 0, 3, 4]
    for node in nodes:
        core.solve_node(G, node, edge_name_col='name', split_on='-',
                        vol_col='vol', load_cols='poc1', tmnt_flags=['TR'],
                        vol_reduced_flags=['INF'])

    for k, v in exp.items():
        val = G.node[0][k]
        assert swmmnetwork.util.sigfigs(
            val, 5) == swmmnetwork.util.sigfigs(v, 5)


def test_solve_network(GT_VOL):
    G, exp = GT_VOL

    core.solve_network(G, edge_name_col='name', split_on='-',
                       vol_col='vol', load_cols='poc1', tmnt_flags=['TR'],
                       vol_reduced_flags=['INF'])

    for k, v in exp.items():
        val = G.node[0][k]
        assert swmmnetwork.util.sigfigs(
            val, 5) == swmmnetwork.util.sigfigs(v, 5)
