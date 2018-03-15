import pandas
import pytest
import networkx as nx

from swmmnetwork import SwmmNetwork
from swmmnetwork.core import _sum_edge_attr
from swmmnetwork.convert import network_to_df

from .utils import data_path


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


@pytest.fixture
def SN(links_and_nodes):
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

    G = SwmmNetwork()
    G.add_edges_from(l)
    G.add_nodes_from(s)
    G.solve_network(
        load_cols='load1',
        tmnt_flags=['TR'],
        vol_reduced_flags=['INF'],
        bmp_performance_mapping_conc=bmp_performance_mapping_conc)

    return G


def test_SwmmNetwork_no_mutation(SN, links_and_nodes):
    G = SN
    l, s = links_and_nodes

    # check that all of the original node attributes have not been mutated.
    for node, data in s:
        for k, v in data.items():
            assert G.node[node][k] == v

    # check that all of the original edge attributes have not been mutated.
    for edge_f, edge_to, data in l:
        matches = filter(lambda x: x[2]['id'] == data['id'],
                         G.edges([edge_f, edge_to], data=True))
        _from, _to, _data = list(matches)[0]
        for k, v in data.items():
            assert _data[k] == v


def test_SwmmNetwork_results(SN):
    G = SN
    results = G.to_dataframe(index_col='id')
    known = pandas.read_csv(data_path('test_full_network.csv'), index_col=[0])
    pandas.testing.assert_frame_equal(
        results.drop(['to', '_bmp_tmnt_flag'], axis='columns'),
        known.drop(['to', '_bmp_tmnt_flag'], axis='columns')
    )


def test_SwmmNetwork_constructors():
    inp_path = data_path('test.inp')
    G = SwmmNetwork.from_swmm_inp(inp_path)
    assert len(G) > 0

    G = SwmmNetwork()
    G.add_edges_from_swmm_inp(inp_path)
    assert len(G) > 0
