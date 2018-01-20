import pytest
import networkx as nx

from swmmnetwork.util import find_cycle

@pytest.mark.parametrize(('G', 'exp'), [
    (
        nx.MultiDiGraph([
            (0, '1'), ('1', '1'), (2, 0)
        ]), [('1', '1', 0)]
    ),
    (
        nx.MultiDiGraph([
            (0, '1'), ('1', 0), (2, 0)
        ]), [(0, '1', 0), ('1', 0, 0)]
    ),
    (
        nx.MultiDiGraph([
            (0, 1), (1, 1), (2, 0)
        ]), [(1, 1, 0)]
    ),
    (
        nx.MultiDiGraph([
            (0, 1), (1, 0), (2, 0)
        ]), [(0, 1, 0), (1, 0, 0)]
    ),
    (
        nx.MultiDiGraph([
            (0, 1), (1, 2), (2, 3)
        ]), []
    ),

])
def test_find_cycle(G, exp):
    assert find_cycle(G) == exp
