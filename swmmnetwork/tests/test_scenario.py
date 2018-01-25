import os
from itertools import product
import pytest
import warnings
warnings.filterwarnings("ignore")

import pytest
import pandas as pd
import pandas.util.testing as pdtest

from swmmnetwork.scenario import Scenario #, ScenarioLoading,
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


# class TestScenarioLoading(object):

#     def setup(self):
#         self.known_all_nodes = pd.read_csv(
#             data_path('all_nodes.csv'), index_col=[0])
#         self.known_all_edges = pd.read_csv(
#             data_path('all_edges.csv'), index_col=[0])
#         self.known_edges_vol = pd.read_csv(
#             data_path('edges_vol.csv'), index_col=[0])
#         self.known_conc = pd.read_csv(data_path('conc.csv'))

#         self.sl = ScenarioLoading(self.known_all_nodes, self.known_all_edges,
#                                   conc=self.known_conc, wq_value_col='concentration'
#                                   )

#     def teardown(self):
#         None

#     def test_attributes(self):
#         assert hasattr(self.sl, '_wq_value_col')
#         assert hasattr(self.sl, '_subcatchment_col')
#         assert hasattr(self.sl, '_pollutant_col')
#         assert hasattr(self.sl, '_wq_unit_col')
#         assert hasattr(self.sl, '_xtype_col')
#         assert hasattr(self.sl, '_volume_val_col')
#         assert hasattr(self.sl, '_vol_unit_col')
#         assert hasattr(self.sl, '_inlet_col')
#         assert hasattr(self.sl, '_outlet_col')
#         assert hasattr(self.sl, 'raw_nodes_vol')
#         assert hasattr(self.sl, 'raw_edges_vol')
#         assert hasattr(self.sl, 'nodes_vol')
#         assert hasattr(self.sl, 'edges_vol')
#         assert hasattr(self.sl, 'raw_load')
#         assert hasattr(self.sl, 'raw_concentration')
#         assert hasattr(self.sl, 'concentration')
#         assert hasattr(self.sl, 'load')

#     def test_edges_vol(self):
#         pdtest.assert_frame_equal(
#             self.sl.edges_vol,
#             self.known_edges_vol
#         )

#     def test_load(self):
#         # currently the returned df has null values.
#         # is this right?
#         None

"""
class TestScenarioHydro(object):

    def setup(self):

        self.known_inp_path = data_path('test.inp')
        self.known_rpt_path = data_path('test.rpt')
        self.known_proxycol = 'water_lbs'
        self.known_vol_units_output = 'acre-ft'

        self.known_all_nodes = (
            pd.read_csv(data_path('all_nodes.csv'), index_col=[0])
            .pipe(_upper_case_index)
        )
        self.known_all_edges = (
            pd.read_csv(data_path('all_edges.csv'), index_col=[0])
            .pipe(_upper_case_index)
            .pipe(_upper_case_column, ['inlet_node', 'outlet_node'])
        )

        self.sh = ScenarioHydro(self.known_inp_path, self.known_rpt_path,
                                proxycol=self.known_proxycol,
                                vol_units_output=self.known_vol_units_output)

    def teardown(self):
        None

    def test_attributes(self):
        assert hasattr(self.sh, 'inp')
        assert hasattr(self.sh, 'rpt')
        assert hasattr(self.sh, 'proxycol')
        assert hasattr(self.sh, 'vol_units_output')
        assert hasattr(self.sh, 'converters')
        assert hasattr(self.sh, 'flow_unit')
        assert hasattr(self.sh, 'subcatchment_volcol')
        assert hasattr(self.sh, 'subcatchment_depthcol')
        assert hasattr(self.sh, 'subcatchment_areacol')
        assert hasattr(self.sh, 'node_volcol')
        assert hasattr(self.sh, 'outfall_volcol')
        assert hasattr(self.sh, 'vol_unit')
        assert hasattr(self.sh, 'depth_unit')
        assert hasattr(self.sh, 'area_unit')
        assert hasattr(self.sh, 'proxy_conc_unit')
        assert hasattr(self.sh, 'proxy_pollutant_conc')
        assert hasattr(self.sh, 'pollutant_to_vol')
        assert hasattr(self.sh, 'intermediate_link_volume')
        assert hasattr(self.sh, 'subcatchments')
        assert hasattr(self.sh, 'nodes')
        assert hasattr(self.sh, 'catchment_links')
        assert hasattr(self.sh, 'weirs')
        assert hasattr(self.sh, 'outlets')
        assert hasattr(self.sh, 'conduits')
        assert hasattr(self.sh, 'orifices')
        assert hasattr(self.sh, 'all_edges')
        assert hasattr(self.sh, 'all_nodes')

    def test_all_nodes(self):
        pdtest.assert_frame_equal(
            self.sh.all_nodes,
            self.known_all_nodes
        )

    def test_all_edges(self):
        pdtest.assert_frame_equal(
            self.sh.all_edges,
            self.known_all_edges
        )
"""
