# -*- coding: utf-8 -*-

from __future__ import division

import pint


KNOWN_CONVERSIONS = [
    # from, to, factor usage: from * factor = to
    ('mgal', 'acre-ft', 1 / 0.325851427),
    ('acre-ft', 'mgal', 0.325851427),
    ('acre-in', 'mgal', 0.325851427 / 12),
]

PINT_ALIAS = {
    # volume
    'mgal': 'Mgal',
    'mgals': 'Mgal',
    'acre-ft': 'acre*ft',
    'acre-feet': 'acre*ft',
    'acft': 'acre*ft',
    # concentration
    'MG/L': 'mg/l',
    'UG/L': 'ug/l',
}


class Converters(object):

    def __init__(self):

        self.ureg = pint.UnitRegistry()

        self._pint_alias = None

    @property
    def pint_alias(self):
        if self._pint_alias is None:
            self._pint_alias = PINT_ALIAS.copy()
        return self._pint_alias

    @pint_alias.setter
    def pint_alias(self, dct):
        self._pint_alias = dct.copy()
        return self._pint_alias

    def proxy_link_flow_conversion_factor(self, load_unit, conc_val, conc_unit, out_unit):

        load_unit, conc_unit, out_unit = [self.pint_alias.get(i, i)
                                          for i in [load_unit, conc_unit, out_unit]]
        ureg = self.ureg

        return (1 * ureg(load_unit) / (conc_val * ureg(conc_unit))).to(out_unit).m

    def subcatchment_flow_conversion_factor(self, area_unit, depth_unit, out_unit):
        area_unit, depth_unit, out_unit = [self.pint_alias.get(i, i)
                                           for i in [area_unit, depth_unit, out_unit]]
        ureg = self.ureg

        return (1 * ureg(area_unit) * ureg(depth_unit)).to(out_unit).m

    def node_volume_conversion_factor(self, vol_unit, out_unit):
        vol_unit, out_unit = [self.pint_alias.get(i, i)
                              for i in [vol_unit, out_unit]]
        ureg = self.ureg

        return (1 * ureg(vol_unit)).to(out_unit).m


def convert_units(df, unit_label_col, value_col, from_unit, to_unit, factor=1):
    """Convert between `from_unit` and `to_unit` using `factor`

    Parameters
    ----------
    df : pandas.Dataframe()
    unit_label_col : string
        column name for units column
    value_col : string
        column name for values column that will be converted
    from_unit : string
        string corresponding to the units that the value_col is presently in.
        This can be an entry in the `KNOWN_CONVERSIONS` list of tuples.
        In practice, the user can specify their own unit conversion table.
    to_unit :string
        string corresponting to the desired final units. This can be an
        entry in the `KNOWN_CONVERSIONS` list of tuples.
    factor : float, optional (default=1)
        multiply `from_unit` by `factor` to get to `to_unit`

    Returns
    -------
    df : pandas.DataFrame()

    """
    norm = df.copy()

    fxn_convert = lambda x: factor if x.strip() == from_unit else 1
    fxn_label = lambda x: to_unit if x.strip() == from_unit else x

    vals = norm[unit_label_col].map(fxn_convert) * norm[value_col]
    units = norm[unit_label_col].map(fxn_label)

    norm[value_col] = vals
    norm[unit_label_col] = units

    return norm
