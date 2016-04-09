Command-Line Utilities
----------------------

For making quick plots and getting quick summaries of important information, the 
following command-line utilities are provided. For finer-grained control over plots
and data, it is recommended to use the Python interface.

``plot_msid``
++++++++++++++

.. code::

    usage: plot_msid [-h] [--y2_axis Y2_AXIS] tstart tstop y_axis
    
    Plot a single MSID with another MSID or state
    
    positional arguments:
      tstart             The start time in YYYY:DOY:HH:MM:SS format
      tstop              The stop time in YYYY:DOY:HH:MM:SS format
      y_axis             The MSID to be plotted on the left y-axis
    
    optional arguments:
      -h, --help         show this help message and exit
      --y2_axis Y2_AXIS  The MSID or state to be plotted on the right y-axis
                         (default: none)

Example:

.. code-block:: bash

    [~]$ plot_msid 2016:091 2016:095 1pin1at --y2_axis=pitch

Returns:

.. image:: _images/plot_msid.png

``plot_model``
++++++++++++++

.. code::

    usage: plot_model [-h] [--y2_axis Y2_AXIS] load y_axis
    
    Plot a single model component with another component or state
    
    positional arguments:
      load               The load to take the model from
      y_axis             The model component to plot on the left y-axis
    
    optional arguments:
      -h, --help         show this help message and exit
      --y2_axis Y2_AXIS  The model component or state to plot on the right y-axis
                         (default: none)

Example:

.. code-block:: bash

    [~]$ plot_model MAR0716A 1dpamzt --y2_axis=off_nominal_roll
    
Returns:

.. image:: _images/plot_model.png

``multiplot_archive``
+++++++++++++++++++++

.. code::

    usage: multiplot_archive [-h] [--one-panel] tstart tstop plots

    Make plots of MSIDs and commanded states from the engineering archive

    positional arguments:
      tstart      The start time in YYYY:DOY:HH:MM:SS format
      tstop       The stop time in YYYY:DOY:HH:MM:SS format
      plots       The MSIDs and states to plot, comma-separated

    optional arguments:
      -h, --help  show this help message and exit
      --one-panel  Whether to make a multi-panel plot or a single-panel plot. The
                   latter is only valid if the quantities have the same units.

Example 1:

.. code-block:: bash

    [~]$ multiplot_archive 2016:089 2016:091 1deamzt,1dpamzt,ccd_count
    
Returns:

.. image:: _images/multiplot_archive.png

Example 2:

.. code-block:: bash

    [~]$ multiplot_archive 2016:091 2016:097 1pdeaat,1pdeabt,1pin1at --one-panel

.. image:: _images/one_panel_multi_archive.png

``multiplot_tracelog``
++++++++++++++++++++++

.. code::

    usage: multiplot_tracelog [-h] [--one-panel] tracelog plots
    
    Make plots of MSIDs from a tracelog file. Commanded states will be loaded from
    the commanded states database.
    
    positional arguments:
      tracelog    The tracelog file to load the MSIDs from
      plots       The MSIDs and states to plot, comma-separated
    
    optional arguments:
      -h, --help  show this help message and exit
      --one-panel  Whether to make a multi-panel plot or a single-panel plot. The
                   latter is only valid if the quantities have the same units.

Example 1:

.. code-block:: bash
    
    [~]$ multiplot_tracelog acisENG10d_00985114479.70.tl 1pin1at,1dp28avo,simpos
    
Returns:

.. image:: _images/multiplot_tracelog.png

Example 2:

.. code-block:: bash
    
    [~]$ multiplot_tracelog acisENG10d_00985114479.70.tl 1dp28avo,1dp28bvo --one-panel
    
Returns:

.. image:: _images/one_panel_multi_tracelog.png

``get_expected_acis_status``
++++++++++++++++++++++++++++

.. code::

    usage: get_expected_acis_status [-h] [--time TIME] load

    Get a summary of the expected ACIS status given a load

    positional arguments:
      load         The load to get the status from

    optional arguments:
      -h, --help   show this help message and exit
      --time TIME  The time to check the status at (default: current time)

Example:

.. code-block:: bash

    [~]$ get_expected_acis_status APR0416C --time=2016:100:18:00:00
    
Returns:

.. code::

    off_nominal_roll: -0.573853195649
    pitch: 144.51
    obsid: 18430
    si_mode: TE_00458
    letg: RETR
    ra: 207.128211876
    roll: 164.982985296
    hetg: RETR
    simfa_pos: -536
    simpos: 91576
    ccd_count: 5
    dec: 26.629677143
    dither: ENAB
    fptemp: -117.006416098
    1deamzt: 22.3543356098
    1dpamzt: 24.9379195122
    1pdeaat: 28.2671678049



