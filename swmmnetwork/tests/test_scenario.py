import os
from itertools import product
import pytest
import warnings
warnings.filterwarnings("ignore")

import pytest
import pandas as pd
import pandas.util.testing as pdtest

from swmmnetwork import SwmmNetwork
from swmmnetwork.scenario import Scenario  # , ScenarioLoading,
from swmmnetwork.util import _upper_case_column
from swmmnetwork.scenario import load_rpt_link_flows
from .utils import data_path


def test_load_rpt_link_flow_volumes():

    link_test = pd.DataFrame(
        {'pol_lbs': [.0035, 3, 11.4, 20.686, 2958.938]},
        index=['a', 'b', 4, 'c', 'd']
    )

    volume_mg = pd.Series(
        name='volume',
        data=[
            0.001287,
            1.103196,
            4.192143,
            7.606901,
            1088.095739,
        ],
        index=['A', 'B', '4', 'C', 'D']
    )

    _key = ['pol', 'Pol', 'pol_lbs', 'POL_LBS']
    _conc_val = [1]
    _unit_factor = [1, 1, 1000, 1000, 1000]
    _conc_unit = ['MG/L', 'mg/l', 'ug/l', 'UG/L', 'µg/L']
    _out_unit = ['acre-ft', 'acre*ft', 'acre-feet', 'acre*feet', 'acft']

    tests = product(_key, _conc_val, zip(_conc_unit, _unit_factor), _out_unit)

    for proxy_keyword, conc_val, conc_info, out_unit in tests:

        c_unit, c_fac = conc_info
        df = load_rpt_link_flows(
            link_test, proxy_keyword, conc_val, c_unit, out_unit)
        pdtest.assert_series_equal(
            round(df.volume / c_fac, 4), round(volume_mg, 4))


class TestScenario(object):

    def setup(self):

        self.known_inp_path = data_path('test.inp')
        self.known_rpt_path = data_path('test.rpt')
        self.known_proxycol = 'water'

        self.known_all_nodes = (
            pd.read_csv(data_path('all_nodes.csv'), index_col=[0])
            .pipe(_upper_case_column, include_index=True)
        )
        self.known_all_edges = (
            pd.read_csv(data_path('all_edges.csv'), index_col=[0])
            .pipe(_upper_case_column, cols=['inlet_node', 'outlet_node'], include_index=True)
        )

        self.sh = Scenario(self.known_inp_path,
                           self.known_rpt_path,
                           proxy_keyword=self.known_proxycol,
                           )
        self.G = SwmmNetwork(scenario=self.sh)
        self.G.solve_network()

    def teardown(self):
        None

    def test_attributes(self):
        assert hasattr(self.sh, 'inp')
        assert hasattr(self.sh, 'rpt')
        assert hasattr(self.sh, 'flow_unit')
        assert hasattr(self.sh, 'vol_unit')
        assert hasattr(self.sh, '_subcatchment_depth_col')
        assert hasattr(self.sh, '_subcatchment_area_col')
        assert hasattr(self.sh, '_node_vol_col')
        assert hasattr(self.sh, '_node_vol_unit')
        assert hasattr(self.sh, '_depth_unit')
        assert hasattr(self.sh, '_area_unit')
        assert hasattr(self.sh, '_proxy_load_unit')
        assert hasattr(self.sh, 'subcatchment_volume')
        assert hasattr(self.sh, 'node_inflow_volume')
        assert hasattr(self.sh, 'edges_df')
        assert hasattr(self.sh, 'edge_list')
        assert hasattr(self.sh, 'nodes_df')
        assert hasattr(self.sh, 'node_list')

    def test_all_nodes(self):
        pdtest.assert_frame_equal(
            round(self.sh.nodes_df.sort_index().drop('xtype', axis=1), 2),
            round(self.known_all_nodes.sort_index().drop('xtype', axis=1), 2),
            check_names=False,
        )

    def test_all_edges(self):
        pdtest.assert_frame_equal(
            round(self.sh.edges_df.sort_index().drop('xtype', axis=1), 2),
            round(self.known_all_edges.sort_index().drop('xtype', axis=1), 2),
            check_names=False,
        )


def test_load_equals_concentration():
    inp = data_path('test.inp')
    rpt = data_path('test.rpt')
    sub_conc_path = data_path('conc.csv')
    sub_conc = pd.read_csv(sub_conc_path)

    sc = Scenario(inp, rpt, concentration_df=sub_conc,
                  pollutant_value_col='concentration')

    sub_load = (
        sc.load
        .query('xtype == "subcatchment"')
        .assign(unit=lambda df: df.unit.str.split("/").str[0])
        .reindex(columns=['subcatchment','pollutant','load', 'unit'])
        .reset_index(drop=True)
    )
    sl = Scenario(inp, rpt, load_df=sub_load,
                  pollutant_value_col='load')

    pd.testing.assert_frame_equal(sc.wide_load, sl.wide_load)
