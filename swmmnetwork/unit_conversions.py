
KNOWN_CONVERSIONS = [
    # from, to, factor usage: from * factor = to
    ('mgal', 'acre-ft', 1 / 0.32585058),
    ('acre-ft', 'mgal', .32585058),
    ('acre-in', 'mgal', .32585058 / 12),
]


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
