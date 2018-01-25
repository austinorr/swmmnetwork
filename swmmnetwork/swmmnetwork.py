# -*- coding: utf-8 -*-

from __future__ import division
import warnings

import numpy
import pandas

import networkx as nx

from . import core
from . import convert


class SwmmNetwork(nx.MultiDiGraph):
    """The SwmmNetwork is initialized by the 'cards' given
    by the SWMM.INP file.
    """

    def __init__(self,
                 data=None,
                 scenario=None,
                 **kwargs):

        nx.MultiDiGraph.__init__(self, data, **kwargs)

        """
        Parameters
        ----------
        scenario : scenario.Scenario, optional (default=None)
            if defined this will load the edges, nodes, and check_nodes
            from the scenario object to build the network.

        """

        if scenario is not None:
            self.scenario = scenario
            self.add_edges_from(scenario.edge_list)
            self.add_nodes_from(scenario.node_list)
            self.add_nodes_from(scenario.check_node_list)

    @classmethod
    def from_swmm_inp(cls, inp):
        return convert.from_swmm_inp(inp, cls())

    def add_edges_from_swmm_inp(self, inp):
        return convert.add_edges_from_swmm_inp(self, inp)

    def to_dataframe(self, index_col='id'):
        return convert.network_to_df(self, index_col=index_col)

    def solve_network(self, **kwargs):
        return core.solve_network(self, **kwargs)
