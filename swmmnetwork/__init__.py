# -*- coding: utf-8 -*-

"""Top-level package for SWMM Network Water Quality."""

__author__ = 'Austin Orr'
__email__ = 'austinmartinorr@gmail.com'
__version__ = '0.2.1'

from .swmmnetwork import SwmmNetwork
from .convert import (
    from_swmm_inp,
    add_edges_from_swmm_inp,
    pandas_edgelist_from_swmm_inp,
    pandas_edgelist_to_edgelist,
    pandas_node_attrs_from_swmm_inp,
)
from .scenario import Scenario
from .tests import test
