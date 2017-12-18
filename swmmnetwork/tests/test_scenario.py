import os
import pytest
import warnings
warnings.filterwarnings("ignore")

import pytest
import pandas as pd
import pandas.util.testing as pdtest

from swmmnetwork.scenario import ScenarioHydro, ScenarioLoading
from .utils import data_path


class TestScenarioHydro(object):

    def setup(self):

        self.known_inp_path = data_path('test.inp')
        self.known_rpt_path = data_path('test.rpt')
        self.known_proxycol = 'water_lbs'
        self.known_vol_units_output = 'acre-ft'

        self.known_all_nodes = (
            pd.read_csv(data_path('all_nodes.csv'), index_col=[0])
            .pipe(ScenarioHydro._upper_case_index)
        )
        self.known_all_edges = (
            pd.read_csv(data_path('all_edges.csv'), index_col=[0])
            .pipe(ScenarioHydro._upper_case_index)
            .pipe(ScenarioHydro._upper_case_column, ['inlet_node', 'outlet_node'])
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


class TestScenarioLoading(object):

    def setup(self):
        self.known_all_nodes = pd.read_csv(
            data_path('all_nodes.csv'), index_col=[0])
        self.known_all_edges = pd.read_csv(
            data_path('all_edges.csv'), index_col=[0])
        self.known_edges_vol = pd.read_csv(
            data_path('edges_vol.csv'), index_col=[0])
        self.known_conc = pd.read_csv(data_path('conc.csv'))

        self.sl = ScenarioLoading(self.known_all_nodes, self.known_all_edges,
                                  conc=self.known_conc, wq_value_col='concentration'
                                  )

    def teardown(self):
        None

    def test_attributes(self):
        assert hasattr(self.sl, '_wq_value_col')
        assert hasattr(self.sl, '_subcatchment_col')
        assert hasattr(self.sl, '_pollutant_col')
        assert hasattr(self.sl, '_wq_unit_col')
        assert hasattr(self.sl, '_xtype_col')
        assert hasattr(self.sl, '_volume_val_col')
        assert hasattr(self.sl, '_vol_unit_col')
        assert hasattr(self.sl, '_inlet_col')
        assert hasattr(self.sl, '_outlet_col')
        assert hasattr(self.sl, 'raw_nodes_vol')
        assert hasattr(self.sl, 'raw_edges_vol')
        assert hasattr(self.sl, 'nodes_vol')
        assert hasattr(self.sl, 'edges_vol')
        assert hasattr(self.sl, 'raw_load')
        assert hasattr(self.sl, 'raw_concentration')
        assert hasattr(self.sl, 'concentration')
        assert hasattr(self.sl, 'load')

    def test_edges_vol(self):
        pdtest.assert_frame_equal(
            self.sl.edges_vol,
            self.known_edges_vol
        )

    def test_load(self):
        # currently the returned df has null values.
        # is this right?
        None
