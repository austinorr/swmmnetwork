from __future__ import division

import warnings

import pandas
import networkx as nx

from .util import _safe_divide, _to_list, validate_swmmnetwork


def _sum_edge_attr(G, node, attr, method='edges', filter_key=None, split_on='-',
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


def solve_node(G, node_name, edge_name_col='id', split_on='-',
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

    node_obj = G.node[node_name]

    load_cols = _to_list(load_cols)
    tmnt_flags = _to_list(tmnt_flags)
    vol_reduced_flags = _to_list(vol_reduced_flags)

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
    node_vol = node_obj.get(vol_col, 0)

    edge_vol_in = _sum_edge_attr(
        G, node_name, vol_col, method='in_edges', split_on=split_on)

    edge_vol_out = edge_vol_in
    vol_eff = edge_vol_out
    vol_treated = 0

    out_edges = G.out_edges(node_name, data=True)
    if out_edges:
        edge_vol_out = _sum_edge_attr(
            G, node_name, vol_col, method='out_edges', split_on=split_on)

        vol_eff = edge_vol_out
        if vol_reduced_flags:
            vol_eff = _sum_edge_attr(G, node_name, vol_col, method='out_edges', split_on=split_on,
                                     filter_key=edge_name_col, exclude_filter_flags=vol_reduced_flags)

        if tmnt_flags:
            vol_treated = _sum_edge_attr(G, node_name, vol_col, method='out_edges', split_on=split_on,
                                         filter_key=edge_name_col, include_filter_flags=tmnt_flags)

    if ck_vol_col is not None:
        vol_diff_ck_col = vol_col + "_diff_ck"
        ck_vol = node_obj.get(ck_vol_col, node_vol)
        vol_diff_ck = vol_in - ck_vol
        node_obj[vol_diff_ck_col] = vol_diff_ck

    vol_in = node_vol + edge_vol_in

    node_obj[vol_in_col] = vol_in
    node_obj[vol_out_col] = edge_vol_out
    node_obj[vol_gain_col] = edge_vol_out - edge_vol_in
    # Negative values in this field
    # indicate internal node losses. There should
    # be a load reduction here if there is load in the inflow.

    vol_reduced = vol_in - vol_eff
    vol_captured = vol_treated + vol_reduced

    # assign node vol attributes
    node_obj[vol_eff_col] = vol_eff

    node_obj[vol_red_col] = vol_reduced
    node_obj[pct_vol_red_col] = 100 * \
        _safe_divide(vol_reduced, vol_in)

    node_obj[vol_tmnt_col] = vol_treated
    node_obj[pct_vol_tmnt_col] = 100 * \
        _safe_divide(vol_treated, vol_in)

    node_obj[vol_cap_col] = vol_captured
    node_obj[pct_vol_cap_col] = 100 * \
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

        # all nodes except pollutant sources (typically subcatchments)
        # should return zero here.
        node_load = node_obj.get(load_col, 0)

        node_load_in = _sum_edge_attr(G, node_name, load_eff_col,
                                      method='in_edges', split_on=split_on) + node_load

        node_obj[load_in_col] = node_load_in

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
                            # checks to see if there is a function for treating this
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

                                if data.get('_bmp_tmnt_flag') is None:
                                    data['_bmp_tmnt_flag'] = {}
                                if data['_bmp_tmnt_flag'].get(flag) is None:
                                    data['_bmp_tmnt_flag'].update({flag: []})
                                data['_bmp_tmnt_flag'][flag].append(load_col)

                                link_conc_eff = fxn(node_conc_in)

                    data[conc_eff_col] = link_conc_eff
                    data[pct_conc_red_col] = 100 * \
                        (node_conc_in - link_conc_eff) / node_conc_in

                    data[load_eff_col] = link_conc_eff * data[vol_col]
                    data[load_red_col] = data[load_in_col] - data[load_eff_col]
                    data[pct_load_red_col] = 100 * \
                        data[load_red_col] / node_load_in

                node_load_eff = _sum_edge_attr(
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
        node_obj[conc_in_col] = node_conc_in
        node_obj[conc_eff_col] = node_conc_eff
        node_obj[pct_conc_red_col] = 100 * \
            _safe_divide((node_conc_in - node_conc_eff), node_conc_in)

        node_load_reduced = node_load_in - node_load_eff

        node_obj[load_eff_col] = node_load_eff
        node_obj[load_red_col] = node_load_reduced
        node_obj[pct_load_red_col] = 100 * \
            _safe_divide(node_load_reduced, node_load_in)

    return


def solve_network(G, edge_name_col='id', split_on='-',
                  vol_col='volume', tmnt_flags=['TR'],
                  vol_reduced_flags=['INF'], ck_vol_col=None,
                  load_cols=None, bmp_performance_mapping_conc=None):

    validate_swmmnetwork(G)

    load_cols = _to_list(load_cols)
    tmnt_flags = _to_list(tmnt_flags)
    vol_reduced_flags = _to_list(vol_reduced_flags)

    if bmp_performance_mapping_conc is None:
        bmp_performance_mapping_conc = {}

    for node in nx.topological_sort(G):
        solve_node(G, node,
                   edge_name_col=edge_name_col,
                   split_on=split_on,
                   vol_col=vol_col,
                   tmnt_flags=tmnt_flags,
                   vol_reduced_flags=vol_reduced_flags,
                   ck_vol_col=ck_vol_col,
                   load_cols=load_cols,
                   bmp_performance_mapping_conc=bmp_performance_mapping_conc,
                   )

    return
