# -*- coding: utf-8 -*-

from __future__ import division

import warnings

import numpy
import pandas

import networkx as nx

from . import core
from .convert import network_to_df, add_edges_from_swmm_inp, from_swmm_inp


class SwmmNetwork(nx.MultiDiGraph):
    """The SwmmNetwork is initialized by the 'cards' given
    by the SWMM.INP file. This file separates the
    """

    def __init__(self,
                 data=None,
                 scenario=None,
                 **kwargs):

        # scenario = kwargs.pop('scenario', None)

        nx.MultiDiGraph.__init__(self, data, **kwargs)

        """
        Parameters
        ----------
        **All agruments in this constructor are passed to the node
        solver algorithm `_solve_node()` except "scenario"

        scenario : scenario.Scenario, optional (default=None)
            if defined this will load the edges, nodes, and check_nodes
            from the scenario object to build the network.

        Attributes
        ----------
        results : pandas.DataFrame
            this is the result of the `_solve_node()` operation for each
            node in the graph. It can be easily written to a csv, or joined
            with another dataframe to build simulation summaries.

        """

        if scenario is not None:
            self.scenario = scenario
            self.add_edges_from(scenario.edge_list)
            self.add_nodes_from(scenario.node_list)
            self.add_nodes_from(scenario.check_node_list)

    @classmethod
    def from_swmm_inp(cls, inp):
        return from_swmm_inp(inp, cls())

    def add_edges_from_swmm_inp(self, inp):
        return add_edges_from_swmm_inp(self, inp)

    def to_dataframe(self, index_col='id'):
        return network_to_df(self, index_col=index_col)

    def solve_network(self, **kwargs):

        return core.solve_network(self, **kwargs)
