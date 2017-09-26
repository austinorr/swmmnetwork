import pytest

import networkx as nx

from swmmnetwork import SwmmNetwork, sum_edge_attr

GT = nx.MultiDiGraph([
    (1, 0, {'name':'1', 'value':2, 'weight':5}),
    (2, 0, {'name':'2', 'value':3, 'weight':2}),
    (0, 3, {'name':'3', 'value':4, 'weight':10}),
    (0, 3, {'name':'5', 'value':7, 'weight':6}),
    (0, 4, {'name':'4', 'value':5, 'weight':3}),
])

# Test graph GT looks like this:
#   1    2
#    \  /
#     0
#  //  \
# 3     4
# direction is top to bottom

@pytest.mark.parametrize(('G', 'node', 'attr', 'dct', 'exp'), [
    (GT.to_undirected(), 0, 'weight', dict(method='edges', filter_key=None, include_filter_flags=None, exclude_filter_flags=None), 26),
    (GT.to_undirected(), 0, 'value',  dict(method='edges', filter_key=None, include_filter_flags=None, exclude_filter_flags=None), 21),
    (GT.to_undirected(), 0, 'weight', dict(method='edges', filter_key='name', include_filter_flags=['1','5'], exclude_filter_flags=None), 11),
    (GT.to_undirected(), 0, 'weight', dict(method='edges', filter_key='name', include_filter_flags=None, exclude_filter_flags=['4','2']), 21),
    (GT.to_undirected(), 0, 'weight', dict(method='edges', filter_key='name', include_filter_flags=['1','2','3','5'],
                           exclude_filter_flags=['1','3']), 8),
    (GT, 0, 'weight', dict(method='out_edges', filter_key=None, include_filter_flags=None, exclude_filter_flags=None), 19),
    (GT, 0, 'value',  dict(method='out_edges', filter_key=None, include_filter_flags=None, exclude_filter_flags=None), 16),
    (GT, 0, 'weight', dict(method='out_edges', filter_key='name', include_filter_flags=['1','5'], exclude_filter_flags=None), 6),
    (GT, 0, 'weight', dict(method='out_edges', filter_key='name', include_filter_flags=None, exclude_filter_flags=['4','2']), 16),
    (GT, 0, 'weight', dict(method='out_edges', filter_key='name', include_filter_flags=['1','2','3','5'],
                           exclude_filter_flags=['1','3']), 6),
    (GT, 0, 'weight', dict(method='in_edges', filter_key=None, include_filter_flags=None, exclude_filter_flags=None), 7),
    (GT, 0, 'value',  dict(method='in_edges', filter_key=None, include_filter_flags=None, exclude_filter_flags=None), 5),
    (GT, 0, 'weight', dict(method='in_edges', filter_key='name', include_filter_flags=['1','5'], exclude_filter_flags=None), 5),
    (GT, 0, 'weight', dict(method='in_edges', filter_key='name', include_filter_flags=None, exclude_filter_flags=['4','2']), 5),
    (GT, 0, 'weight', dict(method='in_edges', filter_key='name', include_filter_flags=['1','2','3','5'],
                           exclude_filter_flags=['1','3']), 2),
])
def test_sum_edge_attr(G, node, attr, dct, exp):
    assert sum_edge_attr(G, node, attr, **dct) == exp



