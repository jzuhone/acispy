Plotting Data in Python
=======================

To make plots appear in an interactive IPython session, do one of the following:

* In an IPython console: start as ``ipython --matplotlib``
* In an IPython Qt console or notebook: start the first cell with ``%matplotlib inline``

Creating Plots of Data vs. Time
-------------------------------

The :class:`~acispy.plots.DatePlot` object can be used to make a single-panel plot of one
or more quantities versus the date and time. 

Creating Multi-Panel Plots
--------------------------

Creating Phase Plots
--------------------

A ``PhasePlot`` shows one quantity plotted versus another. This can be helpful when trying to
determine the behavior of one MSID versus another, or the dependence of an MSID on a 
particular commanded state. 

.. code-block:: python

    msids = ["1dpamzt", "1deamzt"]
    states = ["pitch", "off_nominal_roll", "ccd_count"]
    dc = acispy.DataContainer.fetch_from_database("2015:001", "2016:001", 
                                                  msid_keys=msids,
                                                  state_keys=states)

.. note::

    It is not possible to plot an MSID or model component (such as 1DEAMZT) on the
    x-axis vs. state (such as pitch angle) on the y-axis. Place states on the x-axis
    instead.
    
Important Plotting Methods
--------------------------

The various plotting classes have methods to control the limits of the plots,
change plot labels, and save plots to disk. 

