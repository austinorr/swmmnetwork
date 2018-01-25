
import networkx as nx


if nx.__version__ >= '2':
    from_pandas_edgelist = nx.from_pandas_edgelist
    set_node_attributes = nx.set_node_attributes

else:  # pragma: no cover
    from networkx.convert import _prep_create_using

    # this code is slightly modified from the source code for NetworkX version
    # 2.0

    def from_pandas_edgelist(df, source='source', target='target',
                             edge_attr=None, create_using=None):
        """Return a graph from Pandas DataFrame containing an edge list.

        The Pandas DataFrame should contain at least two columns of node names and
        zero or more columns of node attributes. Each row will be processed as one
        edge instance.

        Note: This function iterates over DataFrame.values, which is not
        guaranteed to retain the data type across columns in the row. This is only
        a problem if your row is entirely numeric and a mix of ints and floats. In
        that case, all values will be returned as floats. See the
        DataFrame.iterrows documentation for an example.

        Parameters
        ----------
        df : Pandas DataFrame
            An edge list representation of a graph

        source : str or int
            A valid column name (string or iteger) for the source nodes (for the
            directed case).

        target : str or int
            A valid column name (string or iteger) for the target nodes (for the
            directed case).

        edge_attr : str or int, iterable, True
            A valid column name (str or integer) or list of column names that will
            be used to retrieve items from the row and add them to the graph as edge
            attributes. If `True`, all of the remaining columns will be added.

        create_using : NetworkX graph
            Use specified graph for result.  The default is Graph()

        See Also
        --------
        to_pandas_edgelist

        Examples
        --------
        Simple integer weights on edges:

        >>> import pandas as pd
        >>> import numpy as np
        >>> r = np.random.RandomState(seed=5)
        >>> ints = r.random_integers(1, 10, size=(3,2))
        >>> a = ['A', 'B', 'C']
        >>> b = ['D', 'A', 'E']
        >>> df = pd.DataFrame(ints, columns=['weight', 'cost'])
        >>> df[0] = a
        >>> df['b'] = b
        >>> df
           weight  cost  0  b
        0       4     7  A  D
        1       7     1  B  A
        2      10     9  C  E
        >>> G = nx.from_pandas_edgelist(df, 0, 'b', ['weight', 'cost'])
        >>> G['E']['C']['weight']
        10
        >>> G['E']['C']['cost']
        9
        >>> edges = pd.DataFrame({'source': [0, 1, 2],
        ...                       'target': [2, 2, 3],
        ...                       'weight': [3, 4, 5],
        ...                       'color': ['red', 'blue', 'blue']})
        >>> G = nx.from_pandas_edgelist(edges, edge_attr=True)
        >>> G[0][2]['color']
        'red'

        """

        g = _prep_create_using(create_using)

        # Index of source and target
        src_i = df.columns.get_loc(source)
        tar_i = df.columns.get_loc(target)
        if edge_attr:
            # If all additional columns requested, build up a list of tuples
            # [(name, index),...]
            if edge_attr is True:
                # Create a list of all columns indices, ignore nodes
                edge_i = []
                for i, col in enumerate(df.columns):
                    if col is not source and col is not target:
                        edge_i.append((col, i))
            # If a list or tuple of name is requested
            elif isinstance(edge_attr, (list, tuple)):
                edge_i = [(i, df.columns.get_loc(i)) for i in edge_attr]
            # If a string or int is passed
            else:
                edge_i = [(edge_attr, df.columns.get_loc(edge_attr)), ]

            # Iteration on values returns the rows as Numpy arrays
            for row in df.values:
                s, t = row[src_i], row[tar_i]
                if g.is_multigraph():
                    g.add_edge(s, t)
                    # default keys just count, so max is most recent
                    key = max(g[s][t])
                    g[s][t][key].update((i, row[j]) for i, j in edge_i)
                else:
                    g.add_edge(s, t)
                    g[s][t].update((i, row[j]) for i, j in edge_i)

        # If no column names are given, then just return the edges.
        else:
            for row in df.values:
                g.add_edge(row[src_i], row[tar_i])

        return g

    def set_node_attributes(G, values, name=None):
        """Sets node attributes from a given value or dictionary of values.

        # AMO: modified to use the patched G.node[] accessor rather than G.nodes[]
        # which works only if version >= 2

        Parameters
        ----------
        G : NetworkX Graph

        values : scalar value, dict-like
            What the node attribute should be set to.  If `values` is
            not a dictionary, then it is treated as a single attribute value
            that is then applied to every node in `G`.  This means that if
            you provide a mutable object, like a list, updates to that object
            will be reflected in the node attribute for each edge.  The attribute
            name will be `name`.

            If `values` is a dict or a dict of dict, the corresponding node's
            attributes will be updated to `values`.

        name : string (optional, default=None)
            Name of the node attribute to set if values is a scalar.

        Examples
        --------
        After computing some property of the nodes of a graph, you may want
        to assign a node attribute to store the value of that property for
        each node::

            >>> G = nx.path_graph(3)
            >>> bb = nx.betweenness_centrality(G)
            >>> isinstance(bb, dict)
            True
            >>> nx.set_node_attributes(G, bb, 'betweenness')
            >>> G.nodes[1]['betweenness']
            1.0

        If you provide a list as the second argument, updates to the list
        will be reflected in the node attribute for each node::

            >>> G = nx.path_graph(3)
            >>> labels = []
            >>> nx.set_node_attributes(G, labels, 'labels')
            >>> labels.append('foo')
            >>> G.nodes[0]['labels']
            ['foo']
            >>> G.nodes[1]['labels']
            ['foo']
            >>> G.nodes[2]['labels']
            ['foo']

        If you provide a dictionary of dictionaries as the second argument,
        the entire dictionary will be used to update node attributes::

            >>> G = nx.path_graph(3)
            >>> attrs = {0: {'attr1': 20, 'attr2': 'nothing'}, 1: {'attr2': 3}}
            >>> nx.set_node_attributes(G, attrs)
            >>> G.nodes[0]['attr1']
            20
            >>> G.nodes[0]['attr2']
            'nothing'
            >>> G.nodes[1]['attr2']
            3
            >>> G.nodes[2]
            {}

        """
        # Set node attributes based on type of `values`
        if name is not None:  # `values` must not be a dict of dict
            try:  # `values` is a dict
                for n, v in values.items():
                    try:
                        G.node[n][name] = values[n]
                    except KeyError:
                        pass
            except AttributeError:  # `values` is a constant
                for n in G:
                    G.node[n][name] = values
        else:  # `values` must be dict of dict
            for n, d in values.items():
                try:
                    G.node[n].update(d)
                except KeyError:
                    pass
