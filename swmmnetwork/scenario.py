# -*- coding: utf-8 -*-

from __future__ import division

import numpy
import pandas

from hymo import SWMMInpFile, SWMMReportFile

from .unit_conversions import UnitConverter
from . import convert
from .util import (
    _upper_case_column,
    _validate_hymo_inp,
    _validate_hymo_rpt,
)


def load_rpt_link_flows(df, proxy_keyword, conc_val, conc_unit,
                        out_unit, unit_converter=None):
    if unit_converter is None:
        unit_converter = UnitConverter()

    proxy_cols = list(
        filter(lambda c: proxy_keyword.lower() in c.lower(), df.columns)
    )

    if len(proxy_cols) > 1 or 0:
        e = ("ERROR: The keyword '{}' is either missing or is not unique "
             "in SWMM Report File Link Pollutant Load Summary".format(
                 proxy_keyword)
             )
        raise ValueError(e)

    proxy_col = proxy_cols[0]
    in_unit = proxy_col.split('_')[-1]

    _in_unit, _conc_unit, _out_unit = [unit_converter.pint_alias.get(i, i)
                                       for i in [in_unit, conc_unit, out_unit]]

    conversion = (1 * unit_converter.ureg(_in_unit) /
                  (conc_val * unit_converter.ureg(_conc_unit))).to(_out_unit).m

    res = (
        df
        .pipe(_upper_case_column, include_index=True)
        .assign(volume=lambda df: df[proxy_col] * conversion)
        .assign(unit=out_unit)
    )

    return res


def load_rpt_subcatchment_vol(df, area_col, area_unit, depth_col,
                              depth_unit, out_unit, unit_converter=None):
    if unit_converter is None:
        unit_converter = UnitConverter()

    _area_unit, _depth_unit, _out_unit = [unit_converter.pint_alias.get(i, i)
                                          for i in [area_unit, depth_unit, out_unit]]

    conversion = (1 * unit_converter.ureg(_area_unit) *
                  unit_converter.ureg(_depth_unit)).to(_out_unit).m

    res = (
        df
        .pipe(_upper_case_column, include_index=True)
        .assign(volume=lambda df:
                df[area_col].astype(float) * df[depth_col].astype(float) * conversion)
        .assign(unit=out_unit)
    )

    return res


def load_rpt_node_inflow_vol(df, vol_value_col, vol_unit,
                             out_unit, unit_converter=None):
    if unit_converter is None:
        unit_converter = UnitConverter()

    _vol_unit, _out_unit = [unit_converter.pint_alias.get(i, i)
                            for i in [vol_unit, out_unit]]

    conversion = (1 * unit_converter.ureg(_vol_unit)).to(_out_unit).m

    res = (
        df
        .pipe(_upper_case_column, include_index=True)
        .assign(volume=lambda df: df[vol_value_col] * conversion)
        .assign(unit=out_unit)
    )

    return res


class ScenarioBase(object):

    def __init__(self, swmm_inp_path=None,
                 swmm_rpt_path=None, proxy_keyword=None,
                 unit_converter=None):

        self.swmm_inp_path = swmm_inp_path
        self.swmm_rpt_path = swmm_rpt_path
        self.proxy_keyword = proxy_keyword

        if self.swmm_inp_path is not None:
            self.inp = _validate_hymo_inp(swmm_inp_path)
            self.flow_unit = self.inp.options.loc['FLOW_UNITS'].values[0]

            # import link volume tracking proxy pollutant
            self.proxy_conc_unit = self.inp.pollutants.Units.values[0]
            self.proxy_pollutant_conc = float(
                self.inp.pollutants.Crain.values[0])

            self.swmm_edges = convert.pandas_edgelist_from_swmm_inp(self.inp)
            self.swmm_node_attrs = convert.pandas_node_attrs_from_swmm_inp(
                self.inp)

        else:
            self.flow_unit = None

        if self.swmm_rpt_path is not None:
            self.rpt = _validate_hymo_rpt(swmm_rpt_path)

            if self.rpt.unit != self.flow_unit:
                e = "Input file units do not match report file units"
                raise(ValueError(e))

        if self.proxy_keyword is None:
            self.proxy_keyword = 'water'

        # Need to kick this can for now
        if (self.flow_unit == 'CFS') or (self.flow_unit is None):
            self.vol_unit = 'acre-ft'
            self._proxy_load_unit = 'lbs'
            self._subcatchment_depth_col = 'Total_Runoff_in'
            self._depth_unit = 'in'
            self._subcatchment_area_col = 'Area'
            self._area_unit = 'acre'
            self._node_vol_col = 'Total_Inflow_Volume_mgals'
            self._node_vol_unit = 'mgal'

        elif self.flow_unit == 'LPS':  # pragma: no cover
            # TODO: check these for accuracy, add tests and unit aliases
            # self.vol_unit = 'liters'
            # self._proxy_load_unit = 'kg'
            # self._subcatchment_depth_col = 'Total_Runoff_cm'
            # self._depth_unit = 'cm'
            # self._subcatchment_area_col = 'Hectares'
            # self._area_unit = 'hectare'
            # self._node_vol_col = 'Total_Inflow_Volume_--'
            # self._node_vol_unit = '--'
            e = 'Only CFS flow units supported.'
            raise(ValueError(e))
        else:
            e = 'Unknown unit system in SWMM files.'
            raise(ValueError(e))

        if unit_converter is None:
            self.unit_converter = UnitConverter()

        # Properties
        self._subcatchment_volume = None
        self._node_inflow_volume = None
        self._edges_df = None
        self._nodes_df = None

    @property
    def subcatchment_volume(self):
        if self._subcatchment_volume is None:
            subcatchment_runoff_results = (
                # need to join the runoff depth with the subcatchment area
                # before converting to volume units.
                self.rpt.subcatchment_runoff_results.pipe(
                    _upper_case_column, include_index=True)
                .join(
                    self.inp.subcatchments.pipe(
                        _upper_case_column, include_index=True),
                    how='left')
            )

            self._subcatchment_volume = (
                load_rpt_subcatchment_vol(
                    subcatchment_runoff_results,
                    self._subcatchment_area_col,
                    self._area_unit,
                    self._subcatchment_depth_col,
                    self._depth_unit,
                    self.vol_unit,
                    self.unit_converter,
                )
            )

        return self._subcatchment_volume

    @property
    def node_inflow_volume(self):
        if self._node_inflow_volume is None:
            self._node_inflow_volume = (
                load_rpt_node_inflow_vol(
                    self.rpt.node_inflow_results,
                    self._node_vol_col,
                    self._node_vol_unit,
                    self.vol_unit,
                    self.unit_converter,
                )
            )

        return self._node_inflow_volume

    @property
    def edges_df(self):
        """
        This is a ScenarioLoading endpoint.
        """

        if self._edges_df is None:
            edges = (
                self.swmm_edges
                .query("xtype != 'dt'")
                .set_index('id')
            )
            subcatchment_edges = (
                self.swmm_edges
                .query("xtype == 'dt'")
                .set_index('id')
            )

            if self.swmm_rpt_path is not None:

                standard_links_df = load_rpt_link_flows(
                    self.rpt.link_pollutant_load_results,
                    self.proxy_keyword,
                    self.proxy_pollutant_conc,
                    self.proxy_conc_unit,
                    self.vol_unit,
                    self.unit_converter,
                )

                edges = edges.join(standard_links_df, how='left')

                subcatchment_links_df = (
                    self.subcatchment_volume
                    .reindex(columns=['volume', 'unit'])
                    .assign(id=lambda df: df.index.map(lambda s: '^' + s))
                    .set_index('id')
                )

                subcatchment_edges = (
                    subcatchment_edges
                    .join(subcatchment_links_df, how='left')
                )

            self._edges_df = (
                pandas.concat([edges, subcatchment_edges])
                .fillna(0)
                .reindex(columns=['inlet_node', 'outlet_node', 'xtype', 'volume', 'unit'])
            )

        return self._edges_df

    @property
    def edge_list(self):
        return convert.pandas_edgelist_to_edgelist(
            self.edges_df.reset_index(), source='inlet_node', target='outlet_node')

    @property
    def nodes_df(self):
        """
        This is a ScenarioLoading endpoint.
        """
        if self._nodes_df is None:

            nodes_inp = self.swmm_node_attrs.reindex(columns=['xtype'])

            if self.swmm_rpt_path is not None:

                nodes_inp = (
                    nodes_inp.join(
                        pandas.concat([
                            self.subcatchment_volume.reindex(
                                columns=['volume', 'unit']),
                            self.node_inflow_volume.reindex(
                                columns=['volume', 'unit'])
                        ])
                        .fillna(0)
                        .rename_axis('id'),
                        how='left'
                    )
                )

                missing_report_node_records = nodes_inp[
                    nodes_inp.volume.isnull()].reset_index().to_dict(orient='records')

                if len(missing_report_node_records) > 0:
                    e = (
                        "SWMM Report file is missing nodes. "
                        "Review 'Subcatchment Runoff Results' and 'Node Inflow "
                        "Results' for the following nodes:\n"
                        "{}".format("\n".join(["Node xtype: {:12}  Node name: {:}".format(
                            i['xtype'], i['Name']) for i in missing_report_node_records])
                        )
                    )
                    raise ValueError(e)

            self._nodes_df = nodes_inp

        return self._nodes_df

    @property
    def node_list(self):

        return convert.pandas_nodelist_to_nodelist(
            self.nodes_df.query('xtype == "subcatchment"')
        )

    @property
    def check_node_list(self):

        return convert.pandas_nodelist_to_nodelist(
            self.nodes_df.query('xtype != "subcatchment"')
            .rename(columns={'volume': '_ck_volume'})
        )

    @property
    def plot_positions(self):
        return convert.swmm_inp_layout_to_pos(self.inp)


class Scenario(ScenarioBase):

    def __init__(self,
                 swmm_inp_path=None,
                 swmm_rpt_path=None,
                 proxy_keyword=None,
                 unit_converter=None,
                 load_df=None,
                 concentration_df=None,
                 pollutant_value_col=None,
                 node_name_col=None,  # 'subcatchemnt'
                 pocs=None,  # 'all'
                 pollutant_name_col=None,  # 'pollutant',
                 pollutant_unit_col=None,  # 'unit',
                 ):

        ScenarioBase.__init__(self, swmm_inp_path,
                              swmm_rpt_path, proxy_keyword, unit_converter)

        if load_df is not None and concentration_df is not None:
            # Can't load as both concentration and as load
            e = 'Please specify either load or concentration, not both.'
            raise ValueError(e)

        elif (load_df is not None or concentration_df is not None) and pollutant_value_col is None:
            e = ('Please specify which column in the pollutant dataframe is '
                 'contains the values of either concentration of load.'
                 )
            raise ValueError(e)

        self.raw_load_df = load_df
        self.raw_concentration_df = concentration_df
        self.pollutant_value_col = pollutant_value_col

        self._node_name_col = node_name_col
        if self._node_name_col is None:
            self._node_name_col = 'subcatchment'

        self._pocs = pocs
        if self._pocs is None:
            self._pocs = 'all'

        self._pollutant_name_col = pollutant_name_col
        if self._pollutant_name_col is None:
            self._pollutant_name_col = 'pollutant'

        self._pollutant_unit_col = pollutant_unit_col
        if self._pollutant_unit_col is None:
            self._pollutant_unit_col = 'unit'

        self._concentration = None
        self._load = None
        self._wide_load = None

        # initialize
        if self.raw_load_df is not None:
            if self._pocs in ['all', ['all'], None]:
                self.pocs = (
                    self.raw_load_df
                    .loc[:, self._pollutant_name_col]
                    .unique()
                    .tolist()
                )

            self.load
            self.wide_load

        elif self.raw_concentration_df is not None:
            if self._pocs in ['all', ['all'], None]:
                self.pocs = (
                    self.raw_concentration_df
                    .loc[:, self._pollutant_name_col]
                    .unique()
                    .tolist()
                )
            self.concentration
            self.load
            self.wide_load
            self.check_units()

    def check_missing_subcatchments(self):
        pass

    def check_units(self):
        load_units = [_.split('/')[-1]
                      for _ in self.load.unit.dropna().unique()]
        vol_units = (self.nodes_df.unit.unique().tolist() +
                     self.edges_df.unit.unique().tolist())

        unique_load_units = (
            self.load
            .drop_duplicates(subset=['pollutant', 'unit'])
            .groupby('pollutant')
            .count()
            .unit
            .max()
        )

        if len(set(load_units)) > 1:
            e = 'Only one load volume unit supported.'
            raise ValueError(e)
        elif len(set(vol_units)) > 1:
            # TODO make this fail so that we see missing subcatchments
            e = 'Only one volume unit supported.'
            raise ValueError(e)
        elif load_units[0] != vol_units[0]:
            e = 'Volume unit from load must match unit of volume.'
            raise ValueError(e)
        elif unique_load_units > 1:
            e = 'Pollutants must have unique units.'
            raise ValueError(e)
        else:
            pass

    # tidy vs wide data not hymo
    def calculate_loading(self):
        if self._load is None:
            self._load = (
                self.concentration
                .join(self.nodes_df, on='subcatchment',
                      how='outer', lsuffix='', rsuffix='_vol')
                .assign(load=lambda df: df.concentration * df.volume)
                .assign(unit_load=lambda df: df.unit + "*" + df.unit_vol)
            )

        elif self._concentration is None:
            self._concentration = (
                self.load
                .join(self.nodes_df, on='subcatchment',
                      how='outer', lsuffix='', rsuffix='_vol')
                .assign(concentration=lambda df: df.load / df.volume)
                .assign(unit_conc=lambda df: df.unit + "/" + df.unit_vol)
            )

    @property
    def load(self):
        if self._load is None:
            load = (
                self.raw_load_df
                .pipe(_upper_case_column, cols=self._node_name_col)
                .rename(columns={
                    self.pollutant_value_col: 'load',
                    self._node_name_col: 'subcatchment',
                    self._pollutant_name_col: 'pollutant',
                    self._pollutant_unit_col: 'unit'})
                .query('pollutant in @self.pocs')
            )
            self._load = load
            self.calculate_loading()

        return self._load

    @property
    def concentration(self):
        if self._concentration is None:
            concentration = (
                self.raw_concentration_df
                .pipe(_upper_case_column, cols=self._node_name_col)
                .rename(columns={
                    self.pollutant_value_col: 'concentration',
                    self._node_name_col: 'subcatchment',
                    self._pollutant_name_col: 'pollutant',
                    self._pollutant_unit_col: 'unit'})
                .query('pollutant in @self.pocs')
            )
            self._concentration = concentration
            self.calculate_loading()
        return self._concentration

    @property
    def wide_load(self):
        if self._wide_load is None:
            load = (
                self.load
                .loc[:, ['subcatchment', 'pollutant', 'xtype',
                         'volume', 'unit_vol', 'load']]
                .set_index(['subcatchment', 'pollutant',
                            'xtype', 'volume', 'unit_vol'])
                .unstack('pollutant')
                .fillna(0)
                .loc[:, 'load']
                .loc[:, self.pocs]
                .reset_index()
                .set_index('subcatchment')
            )
            self._wide_load = load
        return self._wide_load

    @property
    def edge_list(self):

        edges = (
            self.edges_df
            .reset_index()
            .rename(columns={'unit': 'unit_vol'})
        )

        return convert.pandas_edgelist_to_edgelist(
            edges, source='inlet_node', target='outlet_node')

    @property
    def node_list(self):

        if self._wide_load is None:
            nodelist = self.nodes_df
        else:
            nodelist = self.wide_load

        return convert.pandas_nodelist_to_nodelist(
            nodelist
            .query('xtype == "subcatchment"')
        )

    @property
    def check_node_list(self):

        if self._wide_load is None:
            checknodelist = self.nodes_df
        else:
            checknodelist = self.wide_load

        return convert.pandas_nodelist_to_nodelist(
            checknodelist
            .query('xtype != "subcatchment"')
            .rename(columns={'volume': '_ck_volume'})
        )
