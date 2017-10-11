import numpy
import pandas
from .unit_conversions import convert_units, KNOWN_CONVERSIONS

from hymo import SWMMInpFile, SWMMReportFile

class ScenarioHydro(object):

    def __init__(self, swmm_inp_path, swmm_rpt_path, proxycol='Pollutant_lbs',
                 vol_units_output=None, converters=None):
        """
        Parameters
        ----------
        inp : string
            SWMM5.1 input filepath
        rpt : string
            SWMM5.1 status report filepath
        proxycol : string, optional (default='Pollutant_lbs')
        vol_units_output : string, optional (default=None)
            specify desired output units for volume. Default is `None`
            which will produce output in the same units as the SWMM5.1 files.
        converters : tuple or list of tuples, optional (default=None)
            specify list of tuples ordered 'from', 'to', 'factor', like
            [("mgal", "acre-ft", 1 / 0.325851),]. each conversion is
            performed as follows: from * factor = to

        Attributes
        ----------
        allnodes :
        alledges :
        """

        # import hydrology
        self.inp = SWMMInpFile(swmm_inp_path)
        self.rpt = SWMMReportFile(swmm_rpt_path)
        self.proxycol = proxycol
        self.vol_units_output = vol_units_output
        self.converters = converters

        self._convert = False
        if self.vol_units_output is not None:
            self._convert = True
            if self.converters is None:
                self.converters = KNOWN_CONVERSIONS
            elif isinstance(self.converters, tuple):
                self.converters = list(self.converters)

        self.flow_unit = (
            self.rpt.orig_file[self.rpt.find_line_num('Flow Units')]
            .split('.')
            .pop(-1)
            .strip()
        )

        # Need to kick this can for now
        if self.flow_unit == 'CFS':
            self.subcatchment_volcol = 'Total_Runoff_mgal'
            self.subcatchment_depthcol = 'Total_Runoff_in'
            self.subcatchment_areacol = 'Area'
            self.node_volcol = 'Total_Inflow_Volume_mgals'
            self.outfall_volcol = 'Total_Volume_10_6_gal'
            self.vol_unit = 'mgal'
            self.depth_unit = 'in'
            self.area_unit = 'acre'
        elif self.flow_unit == 'LPS':
            e = 'Only standard units supported.'
            raise(ValueError(e))
        else:
            e = 'Only standard units supported.'
            raise(ValueError(e))

        # import link volume tracking proxy pollutant
        self.proxy_conc_unit = self.inp.pollutants.Units.values[0]
        self.proxy_pollutant_conc = float(self.inp.pollutants.Crain.values[0])

        # initialize properties
        self._pollutant_to_vol = None
        self._intermediate_link_volume = None

        self._subcatchments = None
        self._nodes = None

        self._catchment_links = None
        self._weirs = None
        self._outlets = None
        self._conduits = None
        self._orifices = None

        self._all_edges = None
        self._all_nodes = None

    def proxy_conc_conversion_factor(self, flowunit, concunit):
        ug_to_mg = 1 / 1000
        mg_to_lbs = 1 / 453592
        l_to_gal = 1 / 3.78541
        gal_to_mgal = 1 / 1000000

        if concunit == 'MG/L':
            conc_conversion = 1
        elif concunit == 'UG/L':
            conc_conversion = ug_to_mg
        elif concunit == '#/L':
            raise(ValueError)

        if self.flow_unit == 'CFS':
            mgL_to_lbsgal = l_to_gal / mg_to_lbs * conc_conversion
            return mgL_to_lbsgal * gal_to_mgal
        else:
            raise(ValueError)

    @property
    def pollutant_to_vol(self):
        if self._pollutant_to_vol is None:
            conversion = self.proxy_conc_conversion_factor(
                self.flow_unit, self.proxy_conc_unit)
            self._pollutant_to_vol = (conversion / self.proxy_pollutant_conc)
        return self._pollutant_to_vol

    @property
    def intermediate_link_volume(self):
        if self._intermediate_link_volume is None:
            self._intermediate_link_volume = (
                self.rpt.link_pollutant_load_results
                .mul(self.pollutant_to_vol)
                .join(self.rpt.link_flow_results.Type)
                .rename(columns={self.proxycol: 'converted_vol'})
            )
        return self._intermediate_link_volume

    @staticmethod
    def assign_xtype_volcol(df, xtype, volcol):
        return df.assign(xtype=xtype).rename(columns={volcol: 'volume'})

    @property
    def subcatchments(self):
        if self._subcatchments is None:
            subcatchments = (
                self.rpt.subcatchment_runoff_results
                .join(self.inp.subcatchments)
                .assign(volume=lambda df: df[self.subcatchment_areacol].astype(numpy.float64) * df[self.subcatchment_depthcol])
                .assign(unit='acre-in')
                .pipe(convert_units, 'unit', 'volume', *('acre-in', 'mgal', .32585058 / 12))
                .pipe(self.assign_xtype_volcol, 'subcatchments', 'volume')
                .loc[:, ['xtype', 'volume']]
            )
            self._subcatchments = subcatchments

        return self._subcatchments

    @property
    def catchment_links(self):
        if self._catchment_links is None:
            self._catchment_links = (
                self.subcatchments
                .pipe(self.assign_xtype_volcol, 'dt', 'volume')
                .assign(Inlet_Node=lambda df: df.index)
                .assign(id=lambda df: df.index.map(lambda s: '^' + s))
                .join(self.inp.subcatchments.Outlet)
                .set_index('id')
                .rename(columns={'Outlet': 'Outlet_Node'})
                .loc[:, ['Inlet_Node', 'Outlet_Node', 'xtype', 'volume']]
                .rename(columns=lambda s: s.lower())
            )

        return self._catchment_links

    @property
    def nodes(self):
        if self._nodes is None:
            # if we want to carry forward the types of nodes, we can fix it
            # here.
            nodes = (self.rpt.node_inflow_results
                     .pipe(self.assign_xtype_volcol, 'nodes', self.node_volcol)
                     .loc[:, ['xtype', 'volume']]
                     )
            self._nodes = nodes
        return self._nodes

    @property
    def weirs(self):
        if self._weirs is None:
            self._weirs = (
                self.inp
                .weirs
                .loc[:, ['From_Node', 'To_Node']]
                .rename(columns={'From_Node': 'Inlet_Node', 'To_Node': 'Outlet_Node'})
                .join(self.intermediate_link_volume, how='left')
                .pipe(self.assign_xtype_volcol, 'weirs', 'converted_vol')
                .loc[:, ['Inlet_Node', 'Outlet_Node', 'xtype', 'volume']]
                .rename(columns=lambda s: s.lower())
            )
        return self._weirs

    @property
    def orifices(self):
        if self._orifices is None:
            self._orifices = (
                self.inp
                .orifices
                .loc[:, ['From_Node', 'To_Node']]
                .rename(columns={'From_Node': 'Inlet_Node', 'To_Node': 'Outlet_Node'})
                .join(self.intermediate_link_volume, how='left')
                .pipe(self.assign_xtype_volcol, 'orifices', 'converted_vol')
                .loc[:, ['Inlet_Node', 'Outlet_Node', 'xtype', 'volume']]
                .rename(columns=lambda s: s.lower())
            )
        return self._orifices

    @property
    def outlets(self):
        if self._outlets is None:
            self._outlets = (
                self.inp
                .outlets
                .loc[:, ['Inlet_Node', 'Outlet_Node']]
                .join(self.intermediate_link_volume, how='left')
                .pipe(self.assign_xtype_volcol, 'outlets', 'converted_vol')
                .loc[:, ['Inlet_Node', 'Outlet_Node', 'xtype', 'volume']]
                .rename(columns=lambda s: s.lower())
            )
        return self._outlets

    @property
    def conduits(self):
        if self._conduits is None:
            self._conduits = (
                self.inp
                .conduits
                .loc[:, ['Inlet_Node', 'Outlet_Node']]
                .join(self.intermediate_link_volume, how='left')
                .pipe(self.assign_xtype_volcol, 'conduits', 'converted_vol')
                .loc[:, ['Inlet_Node', 'Outlet_Node', 'xtype', 'volume']]
                .rename(columns=lambda s: s.lower())
            )
        return self._conduits

    def _convert_volumes(self, df):
        if self._convert:
            found = False
            for from_unit, to_unit, factor in self.converters:
                if from_unit == self.vol_unit and to_unit == self.vol_units_output:
                    found = True
                    df = convert_units(df, 'unit', 'volume',
                                       from_unit, to_unit, factor)
            if not found:
                raise ValueError('No conversion found for units '
                                 'of {} to {}'.format(self.vol_unit, self.vol_units_output))
            return df
        else:
            return df

    @property
    def all_edges(self):
        """
        This is a ScenarioLoading endpoint.
        """
        if self._all_edges is None:
            self._all_edges = (
                self.catchment_links
                .append(self.weirs)
                .append(self.outlets)
                .append(self.conduits)
                .append(self.orifices)
                .assign(unit=self.vol_unit)
                .pipe(self._convert_volumes)
                .rename(columns=lambda s: s.lower())
                .assign(outlet_node=lambda df: df.outlet_node.astype(str))
                .assign(inlet_node=lambda df: df.inlet_node.astype(str))
            )
        return self._all_edges

    @property
    def all_nodes(self):
        """
        This is a ScenarioLoading endpoint.
        """
        if self._all_nodes is None:
            self._all_nodes = (
                self.subcatchments
                .append(self.nodes)
                .assign(unit=self.vol_unit)
                .pipe(self._convert_volumes)
                .rename(columns=lambda s: s.lower())
            )
        return self._all_nodes

    @property
    def plot_positions(self):
        """
        This is a SwmmNetwork plotting endpoint.
        """
        pos = (
            self.inp
            .coordinates.astype(float)
            .append(
                self.inp.polygons.astype(float)
                .groupby(self.inp.polygons.index)
                .mean())
            .T
            .to_dict('list')
        )
        return pos


class ScenarioLoading(object):

    def __init__(self, nodes_df, edges_df, load=None, conc=None, pocs='all',
                 wq_value_col=None, subcatchment_col='subcatchment',
                 pollutant_col='pollutant', wq_unit_col='unit', xtype_col='xtype',
                 volume_val_col='volume', vol_unit_col='unit',
                 inlet_col='inlet_node', outlet_col='outlet_node'):
        """
        Parameters
        ----------
        nodes_df : pandas.DataFrame
            contains 'xtype_col', 'volume_val_col', 'vol_unit_col',
            and an 'index' containing the node names.
        edges_df : pandas.DataFrame
            contains 'xtype_col', 'volume_val_col', 'vol_unit_col',
            'inlet_col', 'outlet_col', and an index containing the link names.
        load: pandas.DataFrame, optional (default=None)
            containing 'wq_value_col', 'subcatchment_col', 'pollutant_col',
            and 'wq_unit_col'.
        conc: pandas.DataFrame, optional (default=None)
            containing 'wq_value_col', 'subcatchment_col', 'pollutant_col',
            and 'wq_unit_col'.
        pocs: list like or string, optional (default='all')
            names of the pollutants of concern.
        wq_value_col: string, optional (default=None)
            column that contains the wq values in load/conc.
        subcatchment_col: string, optional (default='subcatchment')
            column that contains the subcatchment names in load/conc.
        pollutant_col: string, optional (default='pollutant')
            column that contains the pollutant names in load/conc.
        wq_unit_col: string, optional (default='unit')
            column that contains the units of pollutants in load/conc.
        xtype_col: string, optional (default='xtype')
            column that contains the node/link type in the nodes_df/edges_df.
        volume_val_col: string, optional (default='volume')
            column that contains the volume values in the nodes_df/edges_df.
        vol_unit_col: string, optional (default='unit')
            column that contains the volume units in the nodes_df/edges_df.
        inlet_col: string, optional (default='inlet_node')
            column that contains the inlet in edges_df.
        outlet_col: string, optional (default='outlet_node')
            column that contains the outlet in edges_df.

        """

        if (load is not None) and (conc is not None):
            # If a loading is given we need to know if it is
            # a load or concentration.
            e = 'Please specify only load or concentration, not both.'
            raise ValueError(e)

        self._wq_value_col = wq_value_col
        self._subcatchment_col = subcatchment_col
        self._pollutant_col = pollutant_col
        self._wq_unit_col = wq_unit_col
        self._xtype_col = xtype_col
        self._volume_val_col = volume_val_col
        self._vol_unit_col = vol_unit_col
        self._inlet_col = inlet_col
        self._outlet_col = outlet_col

        self.raw_nodes_vol = nodes_df
        self.raw_edges_vol = edges_df

        self._nodes_vol = None
        self._edges_vol = None

        # import loading
        self.pocs = pocs
        self.raw_load = load
        self.raw_concentration = conc
        self._concentration = None
        self._load = None

        if self.raw_load is not None:
            if self.pocs in ['all', ['all'], None]:
                self.pocs = (
                    self.raw_load
                    .loc[:, self._pollutant_col]
                    .unique()
                    .tolist()
                )
            # initialize
            self.load

        elif self.raw_concentration is not None:
            if self.pocs in ['all', ['all'], None]:
                self.pocs = (
                    self.raw_concentration
                    .loc[:, self._pollutant_col]
                    .unique()
                    .tolist()
                )
            # initialize
            self.concentration

        # self.check_units()

    def check_units(self):
        load_units = [_.split('/')[-1]
                      for _ in self.load.dropna().unit.unique()]
        vol_units = (self.nodes_vol.unit.unique().tolist() +
                     self.edges_vol.unit.unique().tolist())

        unique_load_units = (
            self.load.dropna()
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

    # these are here if we need to do something with the vol in the future
    @property
    def nodes_vol(self):
        if self._nodes_vol is None:
            self._nodes_vol = (
                self.raw_nodes_vol
                .rename(columns={
                    self._xtype_col: 'xtype',
                    self._volume_val_col: 'volume',
                    self._vol_unit_col: 'unit'
                })
            )
        return self._nodes_vol

    # these are here if we need to do something with the vol in the future
    @property
    def edges_vol(self):
        if self._edges_vol is None:
            self._edges_vol = (
                self.raw_edges_vol
                .rename(columns={
                    self._xtype_col: 'xtype',
                    self._volume_val_col: 'volume',
                    self._vol_unit_col: 'unit',
                    self._inlet_col: 'inlet_node',
                    self._outlet_col: 'outlet_node'
                })
            )
        return self._edges_vol

    # tidy vs wide data not hymo
    def calculate_loading(self):
        if self._load is None:
            self._load = (
                self.concentration
                .join(self.nodes_vol, on='subcatchment',
                      how='outer', lsuffix='', rsuffix='_vol')
                .assign(load=lambda df: df.concentration * df.volume)
            )
        elif self._concentration is None:
            self._concentration = (
                self.load
                .join(self.nodes_vol, on='subcatchment',
                      how='outer', lsuffix='', rsuffix='_vol')
                .assign(concentration=lambda df: df.load / df.volume)
            )

    @property
    def load(self):
        if self._load is None:
            load = (
                self.raw_load
                .rename(columns={
                    self._wq_value_col: 'load',
                    self._subcatchment_col: 'subcatchment',
                    self._pollutant_col: 'pollutant',
                    self._wq_unit_col: 'unit'})
                .query('pollutant in @self.pocs')
            )
            self._load = load
            self.calculate_loading()
        return self._load

    @property
    def concentration(self):
        if self._concentration is None:
            concentration = (
                self.raw_concentration
                .rename(columns={
                    self._wq_value_col: 'concentration',
                    self._subcatchment_col: 'subcatchment',
                    self._pollutant_col: 'pollutant',
                    self._wq_unit_col: 'unit'})
                .query('pollutant in @self.pocs')
            )
            self._concentration = concentration
            self.calculate_loading()
        return self._concentration

    @property
    def edge_list(self):
        edges = self.edges_vol.copy()
        edges.index = edges.index.set_names('id')
        edges = (
            edges
            .reset_index()
            .fillna(0)
            .set_index(['inlet_node', 'outlet_node'])
            .loc[:, ['id', 'xtype', 'volume']]
        )
        edge_list = []
        for dtype in edges.xtype.unique():
            _list = edges.query('xtype == @dtype').to_dict('index')
            edge_list.extend(list((str(k[0]), str(k[1]), v)
                                  for k, v in _list.items()))
        return edge_list

    @property
    def node_list(self):
        node = (
            self.load
            .query('xtype == "subcatchments"')
            .drop('unit', axis='columns')
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
            .to_dict('index')
        )

        return list(node.items())

    @property
    def check_node_list(self):
        node = (
            self.load
            .query('xtype == "nodes"')
            .drop('unit', axis='columns')
            .loc[:, ['subcatchment',  'xtype',
                     'volume', 'unit_vol', ]]
            .fillna(0)
            .rename(columns={'volume': "_ck_volume"})
            .set_index('subcatchment')
            .to_dict('index')
        )

        return list(node.items())
