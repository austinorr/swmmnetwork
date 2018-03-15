import numpy
import pytest
import networkx as nx

from swmmnetwork import util


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
    assert util.find_cycle(G) == exp


@pytest.mark.parametrize(('G', 'exp'), [
    (
        nx.MultiDiGraph([
            (0, '1'), ('1', '1'), (2, 0)
        ]), False
    ),
    (
        nx.MultiDiGraph([
            (0, '1'), ('1', 0), (2, 0)
        ]), False
    ),
    (
        nx.MultiDiGraph([
            (0, 1), (1, 1), (2, 0)
        ]), False
    ),
    (
        nx.MultiDiGraph([
            (0, 1), (1, 0), (2, 0)
        ]), False
    ),
    (
        nx.MultiDiGraph([
            (0, 1), (1, 2), (2, 3)
        ]), True
    ),

])
def test_validate(G, exp):
    if exp:
        util.validate_swmmnetwork(G)
    else:
        with pytest.raises(Exception):
            util.validate_swmmnetwork(G)


@pytest.mark.parametrize(('x', 'n', 'exp'), [
    (0, 4, 0),
    (0, None, 0),
    (555.98, None, 555.98),
    (5.5, 3, 5.5),
    (0.33333, 1, 0.3),
    (6.9999999999999999, 1, 7),
    (6.999111, 2, 7.0),
    (6.999111, 3, 7.0),
    (6.999111, 4, 6.999),
    (151354845, 2, 150000000),
    (.0000000012, 1, .000000001),
    ([6.62, 5.52], 2, [6.6, 5.5]),
    (numpy.array([6.62, 55001.52]), 2, numpy.array([6.6, 55000])),
    (numpy.array([.03, 0.3]), 1, numpy.array([.03, 0.3])),
])
def test_sigfigs(x, n, exp):
    numpy.testing.assert_array_equal(util.sigfigs(x, n), exp)
