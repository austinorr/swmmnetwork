# -*- coding: utf-8 -*-

from __future__ import division

import pint


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


class UnitConverter(object):

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
