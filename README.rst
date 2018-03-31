==========================
SWMM Network Water Quality
==========================

.. image:: https://api.travis-ci.org/austinorr/swmmnetwork.svg?branch=master
        :target: https://travis-ci.org/austinorr/swmmnetwork

.. image:: https://codecov.io/gh/austinorr/swmmnetwork/branch/master/graphs/badge.svg?
        :target: https://codecov.io/gh/austinorr/swmmnetwork



SWMMNetwork helps users of EPA SWMM 5.1 perform water quality and load reduction calculations.


API
---

via classmethod:

.. code:: python

	inp_path = 'test.inp'
	G = SwmmNetwork.from_swmm_inp(inp_path)

or via add_edges_from method

.. code:: python

	G = SwmmNetwork()
	G.add_edges_from_swmm_inp(inp_path)

or via ``Scenario`` constructors which help combine input and report files from SWMM 5.1, and which help append subcatchment-based pollutant data from a dataframe.

.. code:: python
	
	rpt_path = 'test.rpt'
	sub_conc = pandas.read_csv('subcatchment_concentrations.csv', index_col=[0])
	sh = Scenario(inp_path, rpt_path)
	sl = ScenarioLoading(sh.all_nodes, sh.all_edges,
	                     conc=sub_conc, wq_value_col='concentration')
	G = SwmmNetwork(scenario=sl)
	G.add_edges_from_swmm_inp(inp_path)

then to solve the network:

.. code:: python

	G.solve_network(
	    load_cols='POC1',
	    tmnt_flags=['TR'],
	    vol_reduced_flags=['INF'],
	    bmp_performance_mapping_conc={
	        "BR": { # in this example "BR" is meant to indicate a bioretention BMP
	            "POC1": lambda x: .3 * x  # 70% reduced
	        }
	    )

	results = G.to_dataframe(index_col='id')


.. raw:: html

   :file: docs/img/swmmnetwork.html

