# -*- coding: utf-8 -*-

"""Main module."""

import warnings

import numpy
import pandas

import networkx as nx


def nodes_to_df(G, index_col=None):
    ls = []
    for node in G.nodes(data=True):
        df = {}
        n, data = node
        if index_col is not None:
            df[index_col] = str(n)
        df['from'] = str(n)
        df['to'] = str(G.successors(n))
        df['type'] = 'node'
        df.update(data)
        ls.append(df)
    return pandas.DataFrame(ls)


def edges_to_df(G):
    ls = []
    for edge in G.edges(data=True):
        df = {}
        _from, _to, data = edge
        df['from'] = str(_from)
        df['to'] = str(_to)
        df['type'] = 'link'
        df.update(data)
        ls.append(df)
    return pandas.DataFrame(ls)


def network_to_df(G, index_col=None):
    df = (
        pandas.concat([nodes_to_df(G, index_col), edges_to_df(G)])
        .reset_index(drop=True)
    )
    if index_col is not None:
        df = df.set_index(index_col)
        df.index = df.index.map(str)
        return (df.sort_index())
    return df


def sum_edge_attr(G, node, attr, method='edges', filter_key=None, split_on='-',
                  include_filter_flags=None, exclude_filter_flags=None):
    """accumulate attributes for one node_id in network G

    Parameters
    ----------
    G : networkx.Graph or networkx.MultiGraph
        a graph network to sum edge attributes at a given node.
        NOTE: For Directed graphs (DiGraph and MultiDiGraph) the
        'edges' method is equivalent to the 'out_edges' method.
    node : string or int
        the networkx node at which to query edge attributes
    attr : string
        an edge attribute key that maps to an int or float. Strings
        will not throw an error, but string concatenation is not the
        purpose of this function.
    method : string, optional (default='edges')
        a method name to select edges for the summation. Valid
        options include 'edges' (default), 'in_edges' and 'out_edges'.
         NOTE: For Directed graphs (DiGraph and MultiDiGraph) the
        'edges' method is equivalent to the 'out_edges' method.
    filter_key : string, optional (default=None)
        edge attribute key that will be searched by the filter flags kwargs
    split_on : string, optional (default='-')
        filter_key string will be split by this character to form a list
        of flags.
    include_filter_flags : list, optional (default=None)
    exclude_filter_flags : list, optional (default=None)

    Returns
    -------
    float
        the sum of the values associated with the `attr`

    """

    edges = getattr(G, method)(node, data=True)
    if not edges:
        return 0

    includes = edges
    if include_filter_flags is not None:
        includes = [edge for edge in edges
                    if any([i in str(edge[2][filter_key]).split(split_on)
                            for i in include_filter_flags])]

    excludes = []
    if exclude_filter_flags is not None:
        excludes = [edge for edge in edges
                    if any([i in str(edge[2][filter_key]).split(split_on)
                            for i in exclude_filter_flags])]

    edges = [i for i in includes if i not in excludes]

    return sum([data.get(attr, 0) for _from, _to, data in edges])


def _safe_divide(x, y):
    """This returns zero if the denominator is zero"""
    if y == 0:
        return 0
    return x / y


def _solve_node(G, node_name, edge_name_col='id', split_on='-',
                vol_col='volume', ck_vol_col=None, tmnt_flags=None,
                vol_reduced_flags=None, load_cols=None,
                bmp_performance_mapping_conc=None):
    '''
    Parameters
    ----------
    G : networkx.MultiDiGraph
        the graph containing the node whose io is to be solved
    node_name : string ##or int?
        name or id of the node to be solved
    edge_name_col : string, optional (default='id')
        the key in the edge attributes corresponding to the field containing
        the treatment or volume reduction flags
    split_on : string, optional (default='-')
        the char that separates flags
    vol_col : string, optional (default='volume')
        the name of the key which relates to the volume value for the edge
        and node. this must be the same for both the edges and the nodes.
    ck_vol_col : string, optional (default=None)
        the key with a preknown node volume with which to do a check on the
        network solution vs the known solution. This is useful when the
        network comes from a SWMM5 network since volume values are provided by
        SWMM for each node.
    tmnt_flags : list of strings, optional (default=None)
        the strings to find in the `edge_name_col` that indicate that the
        edge is treated. this will be used as a key for the
        `bmp_performance_mapping` dictionary to find the appropriate
        function to apply
    vol_reduced_flags : list of strings, optional (default=None)
        the strings to find in the `edge_name_col` that indicate that the
        edge performs treatment by eliminating volume from the network.
    load_cols : list of strings, optional (default=None)
        this is the list of pocs that will be calculated.
    bmp_performance_mapping_conc : dict mapping, optional (default=None)
        lookup table to find the function for performing load reductions at
        a treatment edge. the required format is:
            {
                'tmnt_flag' : {
                    'load_col' : fxn(inf_conc) #function returns eff_conc
                }
            }

    Returns
    -------
    None
        The operation occurs inplace, assigning new variables to the node
        and edge attribute dictionaries as needed. User must introspect
        on the `G` graph object to retrieve results.
    '''

    if load_cols is None:
        load_cols = []
    if tmnt_flags is None:
        tmnt_flags = []
    if vol_reduced_flags is None:
        vol_reduced_flags = []
    if bmp_performance_mapping_conc is None:
        bmp_performance_mapping_conc = {}

    #-----solve water balance-------#
    vol_col = vol_col
    vol_in_col = vol_col + "_in"
    vol_out_col = vol_col + "_out"
    vol_eff_col = vol_col + "_eff"  # total effluent
    vol_red_col = vol_col + "_reduced"  # inf-total eff
    vol_tmnt_col = vol_col + "_treated"  # treated eff
    pct_vol_tmnt_col = vol_col + "_pct_treated"
    pct_vol_red_col = vol_col + "_pct_reduced"
    vol_cap_col = vol_col + "_capture"
    pct_vol_cap_col = vol_col + "_pct_capture"
    vol_gain_col = 'node_vol_gain'

    # subcatchments have no volume from in_edges, but they do have a
    # node_vol.
    node_vol = G.node[node_name].get(vol_col, 0)

    edge_vol_in = sum_edge_attr(
        G, node_name, vol_col, method='in_edges', split_on=split_on)

    edge_vol_out = edge_vol_in
    vol_eff = edge_vol_out
    vol_treated = 0

    out_edges = G.out_edges(node_name, data=True)
    if out_edges:
        edge_vol_out = sum_edge_attr(
            G, node_name, vol_col, method='out_edges', split_on=split_on)

        vol_eff = edge_vol_out
        if vol_reduced_flags:
            vol_eff = sum_edge_attr(G, node_name, vol_col, method='out_edges', split_on=split_on,
                                    filter_key=edge_name_col, exclude_filter_flags=vol_reduced_flags)

        if tmnt_flags:
            vol_treated = sum_edge_attr(G, node_name, vol_col, method='out_edges', split_on=split_on,
                                        filter_key=edge_name_col, include_filter_flags=tmnt_flags)

    if ck_vol_col is not None:
        vol_diff_ck_col = vol_col + "_diff_ck"
        ck_vol = G.node[node_name].get(ck_vol_col, node_vol)
        vol_diff_ck = vol_in - ck_vol
        G.node[node_name][vol_diff_ck_col] = vol_diff_ck

    vol_in = node_vol + edge_vol_in

    G.node[node_name][vol_in_col] = vol_in
    G.node[node_name][vol_out_col] = edge_vol_out
    G.node[node_name][vol_gain_col] = edge_vol_out - edge_vol_in
    # Negative values in this field
    # indicate internal node losses. There should
    # be a load reduction here if there is load in the inflow.

    vol_reduced = vol_in - vol_eff
    vol_captured = vol_treated + vol_reduced

    # assign node vol attributes
    G.node[node_name][vol_eff_col] = vol_eff

    G.node[node_name][vol_red_col] = vol_reduced
    G.node[node_name][pct_vol_red_col] = 100 * \
        _safe_divide(vol_reduced, vol_in)

    G.node[node_name][vol_tmnt_col] = vol_treated
    G.node[node_name][pct_vol_tmnt_col] = 100 * \
        _safe_divide(vol_treated, vol_in)

    G.node[node_name][vol_cap_col] = vol_captured
    G.node[node_name][pct_vol_cap_col] = 100 * \
        _safe_divide(vol_captured, vol_in)

    #-----solve volume weighted loads-----#
    for load_col in load_cols:

        load_in_col = load_col + '_load_in'
        load_eff_col = load_col + '_load_eff'
        load_red_col = load_col + '_load_reduced'
        pct_load_red_col = load_col + '_load_pct_reduced'

        conc_in_col = load_col + '_conc_in'
        conc_eff_col = load_col + '_conc_eff'
        pct_conc_red_col = load_col + '_conc_pct_reduced'

        # all nodes except subcatchments should return zero here.
        node_load = G.node[node_name].get(load_col, 0)

        node_load_in = sum_edge_attr(G, node_name, load_eff_col,
                                     method='in_edges', split_on=split_on) + node_load

        G.node[node_name][load_in_col] = node_load_in

        if vol_in > 0 and node_load_in > 0:  # skip the math if it's unnecessary

            node_conc_in = node_load_in / vol_in  # this shouldn't need safe_division

            if out_edges:  # this means it's not an outfall

                for edge in out_edges:
                    _from, _to, data = edge

                    data[conc_in_col] = node_conc_in
                    data[load_in_col] = node_conc_in * data[vol_col]

                    # assume no treatment base-case
                    link_conc_eff = node_conc_in

                    # apply treatment to link via treatment function
                    link_name_flags = str(data[
                        edge_name_col]).split(split_on)

                    if any([i in link_name_flags for i in vol_reduced_flags]):
                        # if the link eliminates volume, then the load is
                        # eliminated too.
                        link_conc_eff = 0

                    # checks to see if we will apply treatment
                    elif any([i in link_name_flags for i in tmnt_flags]):

                        for flag in link_name_flags:
                            # checks to see if there is a function for treatmenting this
                            # type of bmp and this type of load. if multiple flags are
                            # present in the link name, then the last one will be the
                            # one that has an effect on the concentration.
                            if flag in bmp_performance_mapping_conc:
                                # note: an error like this should likely be
                                # logged in a log file.
                                try:
                                    fxn = bmp_performance_mapping_conc[
                                        flag][load_col]
                                except:
                                    fxn = lambda x: x
                                    warnings.warn(
                                        'No performance function provided for bmp type: '
                                        '{} for pollutant: {}. No reduction was applied.'.format(flag, load_col))
                                    flag = '_no_tmnt_fxn'
                                data['_bmp_tmnt_flag'] = flag

                                link_conc_eff = fxn(node_conc_in)

                    data[conc_eff_col] = link_conc_eff
                    data[pct_conc_red_col] = 100 * \
                        (node_conc_in - link_conc_eff) / node_conc_in

                    data[load_eff_col] = link_conc_eff * data[vol_col]
                    data[load_red_col] = data[load_in_col] - data[load_eff_col]
                    data[pct_load_red_col] = 100 * \
                        data[load_red_col] / node_load_in

                node_load_eff = sum_edge_attr(
                    G, node_name, load_eff_col, method='out_edges', split_on=split_on)

                node_conc_eff = _safe_divide(node_load_eff, vol_eff)

            else:  # this means the node is an outfall. outfalls get
                   # no load reduction credit, so out = in
                node_load_eff = node_load_in
                node_conc_eff = node_conc_in

        else:  # this means there was no influent or no influent loading.
               # in either case, effluent must be zero.
            node_load_eff = 0
            node_conc_in = 0
            node_conc_eff = 0

        # assign node load and concentration attributes
        G.node[node_name][conc_in_col] = node_conc_in
        G.node[node_name][conc_eff_col] = node_conc_eff
        G.node[node_name][pct_conc_red_col] = 100 * \
            _safe_divide((node_conc_in - node_conc_eff), node_conc_in)

        node_load_reduced = node_load_in - node_load_eff

        G.node[node_name][load_eff_col] = node_load_eff
        G.node[node_name][load_red_col] = node_load_reduced
        G.node[node_name][pct_load_red_col] = 100 * \
            _safe_divide(node_load_reduced, node_load_in)

    return


class SwmmNetwork(nx.MultiDiGraph):
    """The SwmmNetwork is initialized by the 'cards' given
    by the SWMM.INP file. This file separates the
    """

    def __init__(self,
                 edge_name_col='id',
                 split_on="-",
                 vol_col='volume',
                 ck_vol_col=None,
                 load_cols=None,
                 tmnt_flags=None,
                 vol_reduced_flags=None,
                 bmp_performance_mapping_conc=None,
                 scenario=None,
                 **kwargs):
        nx.MultiDiGraph.__init__(self, **kwargs)

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

        self.edge_name_col = edge_name_col
        self.split_on = split_on
        self.vol_col = vol_col
        self.ck_vol_col = ck_vol_col

        # coerce inputs to iterables
        for name, val in zip(['load_cols', 'tmnt_flags', 'vol_reduced_flags'],
                             [load_cols, tmnt_flags, vol_reduced_flags]):
            if val is None:
                setattr(self, name, [])
            elif isinstance(val, str):
                setattr(self, name, [val])
            else:
                setattr(self, name, val)
            try:
                assert isinstance(getattr(self, name), list)
            except:
                raise TypeError('Pass {} as a list.'.format(name))

        if bmp_performance_mapping_conc is None:
            bmp_performance_mapping_conc = {}

        self.bmp_performance_mapping_conc = bmp_performance_mapping_conc
        if scenario is not None:
            self.scenario = scenario
            self.add_edges_from(scenario.edge_list)
            self.add_nodes_from(scenario.node_list)
            self.add_nodes_from(scenario.check_node_list)

        # properties
        self._results = None

    @property
    def results(self):
        if self._results is None:
            self.solve_network()
            self._results = network_to_df(self, index_col=self.edge_name_col)
        return self._results

    def solve_network(self):

        for node in nx.topological_sort(self):

            _solve_node(self, node,
                        edge_name_col=self.edge_name_col,
                        vol_col=self.vol_col,
                        ck_vol_col=self.ck_vol_col,
                        tmnt_flags=self.tmnt_flags,
                        vol_reduced_flags=self.vol_reduced_flags,
                        load_cols=self.load_cols,
                        bmp_performance_mapping_conc=self.bmp_performance_mapping_conc,
                        split_on=self.split_on
                        )
        return
