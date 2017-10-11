import pandas
import pytest

import networkx as nx

from ..swmmnetwork import SwmmNetwork, sum_edge_attr
from .utils import data_path

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
    assert sum_edge_attr(G, node, attr, **dct) == exp


@pytest.fixture
def links_and_nodes():
    """
                    J4     S1
                   / \    /
                  /   \  /
          S3     /     J3   S2
           \    /       |  /
            \  /        | /
             J6         BR
             |         // \
             |        //   \
            ~BI      J2    INF
             |       |
             |       |
             J5     BF
              \    //
               \  //
                J1
                |
                |
                OF
    """
    s = [
        ('S1', {"load1": 6, "load2": 10, "volume": 12}),
        ('S2', {"load1": 8, "load2": 10, "volume": 13}),
        ('S3', {"load1": 5, "load2": 10, "volume": 10}),
    ]

    l = [
        ('S1', 'J3', {'id': "^S1", "volume": 12}),
        ('S2', 'BR', {'id': "^S2", "volume": 13}),
        ('J3', 'BR', {'id': "C3", "volume": 12}),
        ('BR', 'J2', {'id': "w2", "volume": 2}),
        ('BR', 'J2', {'id': "TR-BR", "volume": 13}),
        ('BR', 'INF-OF', {'id': "INF-1", "volume": 10}),
        ('J2', 'BF', {'id': "C2", "volume": 15}),
        ('BF', 1, {'id': "w1", "volume": 2}),
        ('BF', 1, {'id': "TR-BF", "volume": 13}),
        (1, 'OF', {'id': "C1", "volume": 16.8}),
        ('J4', 'J3', {'id': "C4", "volume": 0}),
        ('J4', 'J6', {'id': "C7", "volume": 0}),
        ('S3', 'J6', {'id': "^S3", "volume": 10}),
        ('J6', 'BI', {'id': 2, "volume": 10}),
        ('BI', 'J5', {'id': "w3", "volume": 1.8}),
        ('J5', 1, {'id': "C5", "volume": 1.8}),
    ]
    return l, s


def test_SwmmNetwork(links_and_nodes):
    bmp_performance_mapping_conc = {
        "BR": {
            "load1": lambda x: .2 * x  # 80% reduced
        },
        "BI": {
            "load1": lambda x: .2 * x  # 80% reduced
        },
        "BF": {
            "load1": lambda x: .5 * x  # 50% reduced
        },
    }

    l, s = links_and_nodes

    G = SwmmNetwork(
        load_cols='load1',
        tmnt_flags=['TR'],
        vol_reduced_flags=['INF'],
        bmp_performance_mapping_conc=bmp_performance_mapping_conc,
    )
    G.add_edges_from(l)
    G.add_nodes_from(s)
    results = G.results

    known = pandas.read_csv(data_path('test_full_network.csv'), index_col=[0])
    pandas.testing.assert_frame_equal(
        results.drop('to', axis='columns'),
        known.drop('to', axis='columns')
    )
