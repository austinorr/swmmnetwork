
import pytest
import pandas

from swmmnetwork import SwmmNetwork
from swmmnetwork.convert import (
    add_edges_from_swmm_inp,
    network_to_df,
    from_swmm_inp,
    pandas_edgelist_to_edgelist,
)

from .utils import data_path

inp_path = data_path('test.inp')


@pytest.fixture
def _G():
    G = SwmmNetwork()
    G.add_edges_from([(0, 1), (1, 2), (2, 3)])
    return G


def test_from_swmm_inp1(_G):

    G = from_swmm_inp(inp_path, create_using=_G)

    # this constructor should clear the network and replace it with
    # the data from the swmm inp file
    with pytest.raises(KeyError):
        G.node[0]

    assert len(G) == 17
    assert len(list(G.edges())) == 17
    assert isinstance(G, SwmmNetwork)


def test_add_edges_from_swmm_inp(_G):

    G = _G
    G.add_edges_from_swmm_inp(inp_path)

    # this constructor should add new edges while preserving old ones.
    assert 0 in G.node

    assert len(G) == 21
    assert len(list(G.edges())) == 20


def test_equivalent_inp_constructor():

    G1 = from_swmm_inp(inp_path, create_using=SwmmNetwork())
    df_G1 = (network_to_df(G1, index_col='id')
             .drop(['inlet_node', 'outlet_node'], axis=1)
             )

    G2 = SwmmNetwork()
    G2.add_edges_from_swmm_inp(inp_path)
    df_G2 = network_to_df(G2, index_col='id')

    pandas.testing.assert_frame_equal(df_G1, df_G2)


def test_pandas_edgelist_to_edgelist():
    dict_el = [
        {
            'source': '0',
            'target': '1',
            'xtype': 'conduit',
            'ident': 'first',
        },
        {
            'source': '0',
            'target': '1',
            'xtype': 'conduit',
            'ident': 'second',
        },
        {
            'source': '0',
            'target': '1',
            'xtype': 'weir',
            'ident': 'third',
        },
        {
            'source': '0',
            'target': '2',
            'xtype': 'conduit',
            'ident': 'fourth',
        },
    ]
    df = pandas.DataFrame(dict_el)
    el = pandas_edgelist_to_edgelist(df)
    assert len(el) == len(df) == len(dict_el)
