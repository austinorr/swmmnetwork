import numpy
import pandas


def networkxify(df, xtype, loadcols=None, volcol=None):
    if df.shape[0] > 0:
        if xtype == 'subcatchments':
            return (df.assign(val=lambda df: df.apply(
                                lambda x: (str(x.name),
                               {
                                   **{_: x[_] for _ in loadcols},
                                   **{'volume': x[volcol],
                                      'type': xtype}
                                }
                              ), axis=1))
                      .assign(xtype=xtype)
                      .rename(columns={volcol: 'volume'})
                   )
        elif xtype == 'dt':
            return (df.assign(val=lambda df: df.apply(lambda x:(
                            str(x.name),
                            str(x.Outlet),
                            {'id': '^{}'.format(x.name),
                             'type': xtype}), axis=1))
                      .assign(xtype=xtype)
                   )
        elif xtype in ['weirs', 'outlets', 'conduits']:
            return (df.assign(val=lambda df: df.apply(lambda x:(
                            str(x.Inlet_Node),
                            str(x.Outlet_Node),
                            {'id': x.name,
                             'type': xtype,
                             'volume': x.converted_vol}), axis=1))
                      .assign(xtype=xtype)
                      .rename(columns={'volume': volcol})
                   )
        else:
            raise(ValueError)
    else:
        return df.assign(val=[])


class Scenario(object):
    def __init__(self, inp, rpt, load=None, conc=None, pocs='all'):
        """
        inp: swmmreport.InpFile().
        rpt: swmmreport.ReportFile().
        load: pandas.DataFrame, loading dataset with the index set to subcatchments.
        conc: pandas.DataFrame, concentration dataset with the index set to subcatchments.
        pocs: list like, pollutants of concern.
        """
        if (load is not None) and (conc is not None):
            # If a loading is given we need to know if it is
            # a load or concentration.
            e = 'Please specify only load or concentration, not both.'
            raise ValueError(e)

        # import hydrology
        self.inp = inp
        self.rpt = rpt

        # import loading
        self.raw_load = load
        self.raw_concentration = conc
        self._concentration = None
        self._load = None

        if self.raw_load is not None:
            if pocs == 'all':
                self.pocs = self.raw_load.columns.tolist()
            self._load = self.raw_load.loc[:, self.pocs]


        elif self.raw_concentration is not None:
            if pocs == 'all':
                self.pocs = self.raw_concentration.columns.tolist()
            self._concentration = self.raw_concentration.loc[:, self.pocs]


        self.flow_unit = (rpt.orig_file[rpt._find_line('Flow Units')]
                             .split('.')
                             .pop(-1)
                             .strip()
        )

        # import link volume tracking proxy pollutant
        self.proxy_conc_unit = inp.pollutants.Units.values[0]
        self.proxy_pollutant_conc = float(inp.pollutants.Crain.values[0])

        if self.flow_unit != 'CFS':
            e = 'Only standard units supported.'
            raise(ValueError(e))

        # initialize properties 
        self._pollutant_to_vol = None
        self._intermediate_link_volume = None
        self._subcatchments = None
        self._catchment_links = None
        self._weirs = None
        self._outlets = None
        self._conduits = None

        self._merged_results = None

    def calculate_loading(self):
        if self._load is None:
            # TODO: WIP 
            self._load = self.raw_concentration.mul(self.rpt
                                               .subcatchment_runoff_results
                                               .Total_Runoff_mgal, axis='index')

        elif self._concentration is None:
            # TODO: WIP 
            self._concentration = self.raw_load.div(self.rpt
                                               .subcatchment_runoff_results
                                               .Total_Runoff_mgal, axis='index')

    def conversion_factor(self, flowunit, concunit):
        ug_to_mg = 1/1000
        mg_to_lbs = 1/453592
        l_to_gal = 1/3.78541

        if concunit == 'MG/L':
            conc_conversion = 1
        elif concunit == 'UG/L':
            conc_conversion = ug_to_mg
        elif concunit == '#/L':
            raise(ValueError)

        if self.flow_unit == 'CFS':
            mgL_to_lbsgal = l_to_gal / mg_to_lbs * conc_conversion
            return mgL_to_lbsgal
        else:
            raise(ValueError)

    @property
    def load(self):
        if self._load is None:
            self.calculate_loading()
        return self._load

    @property
    def concentration(self):
        if self._concentration is None:
            self.calculate_loading()
        return self._concentration

    @property
    def pollutant_to_vol(self):
        if self._pollutant_to_vol is None:
            conversion = self.conversion_factor(self.flow_unit, self.proxy_conc_unit)
            self._pollutant_to_vol = (conversion/self.proxy_pollutant_conc)
        return self._pollutant_to_vol


    @property
    def intermediate_link_volume(self):
        if self._intermediate_link_volume is None:
            self._intermediate_link_volume = (self.rpt.link_pollutant_load_results
                                                 .mul(self.pollutant_to_vol)
                                                 .join(self.rpt.link_flow_results.Type)
                                                 .rename(columns={'Pollutant_lbs': 'converted_vol'})
            )
        return self._intermediate_link_volume


    @property
    def subcatchments(self):
        if self._subcatchments is None:
            subcatchments = (self.rpt.subcatchment_runoff_results
                                 # where we would join lspc results
                                 .join(self.load)
                                 .pipe(networkxify, 'subcatchments', self.pocs, 'Total_Runoff_mgal')
                                 .loc[:, ['xtype', 'volume', 'val'] + self.pocs]
            )
            self._subcatchments = subcatchments

        return self._subcatchments

    @property
    def catchment_links(self):
        if self._catchment_links is None:
            _dt = self.inp.subcatchments.pipe(networkxify, 'dt', self.pocs, 'Total_Runoff_mgal')

            dt = [
                (i, o, dict(data, volume=dct))
                for (i, o, data), dct in
                zip(
                    _dt.val.values, [j[1]['volume']
                    for j in self.subcatchments.val.values])
            ]

            self._catchment_links = (self.subcatchments.loc[:, self.pocs]
                                        .assign(xtype='catchment_link')
                                        .assign(val1=dt)
                                        .assign(val=lambda df: df.apply(
                                            lambda x: (x.val1[0], x.val1[1],
                                            {**{_: x[_] for _ in self.pocs},
                                            **x.val1[2]}), axis=1))
                                        .assign(volume=lambda df: df.val.apply(lambda x: x[2]['volume']))
                                        .loc[:, ['xtype', 'volume', 'val'] + self.pocs]
            )

        return self._catchment_links


    @property
    def weirs(self):
        if self._weirs is None:
            self._weirs = (self.inp
                               .weirs
                               .loc[:,['From_Node', 'To_Node']]
                               .rename(columns={'From_Node': 'Inlet_Node', 'To_Node': 'Outlet_Node'})
                               .join(self.intermediate_link_volume, how='left')
                               .pipe(networkxify, 'weirs')
                               .loc[:, ['xtype', 'volume', 'val'] + self.pocs]
            )
        return self._weirs

    @property
    def outlets(self):
        if self._outlets is None:
            self._outlets = (self.inp
                                 .outlets
                                 .loc[:,['Inlet_Node', 'Outlet_Node']]
                                 .join(self.intermediate_link_volume, how='left')
                                 .pipe(networkxify, 'outlets')
                                 .loc[:, ['xtype', 'volume', 'val'] + self.pocs]
            )
        return self._outlets

    @property
    def conduits(self):
        if self._conduits is None:
            self._conduits = (self.inp
                                  .conduits
                                  .loc[:,['Inlet_Node', 'Outlet_Node']]
                                  .join(self.intermediate_link_volume, how='left')
                                  .pipe(networkxify, 'conduits')
                                  .loc[:, ['xtype', 'volume', 'val'] + self.pocs]
            )
        return self._conduits

    @property
    def merged_results(self):
        if self._merged_results is None:
            self._merged_results = (self.subcatchments
                                        .append(self.catchment_links)
                                        .append(self.weirs)
                                        .append(self.outlets)
                                        .append(self.conduits)
            )
        return self._merged_results

    @property
    def edge_list(self):
        return (self.merged_results
                   .query('xtype != "subcatchments"')
                   .val
                   .values
                   .tolist()
        )
    @property
    def node_list(self):
        return (self.merged_results
                   .query('xtype == "subcatchments"')
                   .val
                   .values
                   .tolist()
        )

    @property
    def plot_positions(self):
        return (self.inp
                    .coordinates.astype(float)
                    .append(inp.polygons.astype(float)
                               .groupby(inp.polygons.index)
                               .mean())
                    .T
                    .to_dict('list')
        )