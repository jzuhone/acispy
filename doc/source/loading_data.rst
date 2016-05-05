.. _loading-data:

Loading Data in Python
======================

ACISpy can work with ACIS-related data from the commanded states 
database, the engineering archive, or thermal models produced by Xija. 
The first thing that must be done before any data can be worked with or 
plotted is to ingest the data in a :class:`~acispy.data_container.DataContainer` 
object. :class:`~acispy.data_container.DataContainer` objects can be created by a 
number of methods, which are documented here.

Fetching Data from the Online Database
--------------------------------------

Often, one will want to fetch data directly from the Chandra engineering
archive and the commanded states database within a particular date and time 
range. The method :meth:`~acispy.data_container.DataContainer.fetch_from_database` 
enables this functionality. The MSIDs and states you want to extract must be 
specified:

.. code-block:: python

    from acispy import DataContainer
    tstart = "2016:091:01:00:00.000" 
    tstop = "2016:097:03:30:57.231"
    msids = ["1deamzt", "1dpamzt"]
    states = ["pitch", "off_nominal_roll"]
    dc = DataContainer.fetch_from_database(tstart, tstop, msid_keys=msids,
                                           state_keys=states)
                                           
Additional options are provided for filtering out bad data and choosing the
time cadence for MSIDs; for details see the API doc entry for 
:meth:`~acispy.data_container.DataContainer.fetch_from_database`. 

Reading MSID Data From a Tracelog File
--------------------------------------

If you have a real-time tracelog file or one that has been extracted from a 
dump, you can also read MSID data from this file, using the
:meth:`~acispy.data_container.DataContainer.fetch_from_tracelog` method. In 
this case, the state data corresponding to the times spanned by the tracelog
file will be extracted from the commanded states database. 

.. code-block:: python

    from acispy import DataContainer
    states = ["pitch", "ccd_count"]
    dc = DataContainer.fetch_from_tracelog("acisENG10d_00985114479.70.tl",
                                           state_keys=states)
    
In this case, all of the MSIDs in the tracelog are ingested into the 
:class:`~acispy.data_container.DataContainer`, whereas the states that you 
want must be specified.

Reading Model Data from a Load
------------------------------

You can also fill a :class:`~acispy.data_container.DataContainer` with predicted
model data for a particular temperature model or multiple models corresponding to 
a particular load review using :meth:`~acispy.data_container.DataContainer.fetch_model_from_load`:

.. code-block:: python

    from acispy import DataContainer
    comps = ["1deamzt","1dpamzt","fptemp_11"]
    dc = DataContainer.fetch_model_from_load("APR0416C", comps)

To get the corresponding MSIDs from the engineering archive during the same 
time frame, pass to :meth:`~acispy.data_container.DataContainer.fetch_model_from_load`
the keyword argument ``get_msids=True``.

Directly Accessing Data from the Container
------------------------------------------

The :class:`~acispy.data_container.DataContainer` object has dictionary-like 
access so that the data may be accessed directly. Data can be accessed by querying 
the :class:`~acispy.data_container.DataContainer` object with a tuple giving the 
type of data desired and its name, for example:

.. code-block:: python

    # "dc" is a DataContainer object
    dc["states", "pitch"] # gives you the "pitch" state
    dc["msids", "fptemp_11"] # gives you the "fptemp_11" pseudo-MSID
    dc["model", "1deamzt"] # gives you the "1deamzt" model component

A ``(type, name)`` pairing and its associated data are referred to as a "field". We'll
encounter examples of :ref:`derived-fields` later, which are derivations of new fields from
existing ones. For now, we'll use our example from before to fill up a :class:`~acispy.data_container.DataContainer`:

.. code-block:: python

    from acispy import DataContainer
    tstart = "2016:091:01:00:00.000" 
    tstop = "2016:097:03:30:57.231"
    msids = ["1deamzt", "1dpamzt"]
    states = ["pitch", "off_nominal_roll", "ccd_count"]
    dc = DataContainer.fetch_from_database(tstart, tstop, msid_keys=msids,
                                           state_keys=states)

Data are returned as NumPy arrays or 
`AstroPy Quantities <http://docs.astropy.org/en/stable/units/quantity.html>`_ 
(which are just NumPy arrays with units attached). The following print statements:

.. code-block:: python

    print dc["states", "ccd_count"]
    print dc["states", "pitch"]
    print dc["msids", "1deamzt"]

result in the following output (or something similar):

.. code-block:: pycon

    [6  6  6 ...,  4  4  4]

    [ 155.78252178  155.94230537  155.95272431  ...,  142.85889318
      148.43712545  149.54367736] deg

    [ 22.14923096  22.14923096  22.14923096 ...,  20.17999268  
      20.17999268  20.17999268] deg_C

To see what fields are available from the :class:`~acispy.data_container.DataContainer`,
check the `field_list` attribute:

.. code-block:: python

    print dc.field_list

.. code-block:: pycon

    [('msids', '1deamzt'),
     ('msids', '1dpamzt'),
     ('states', 'q1'),
     ('states', 'q3'),
     ('states', 'q2'),
     ('states', 'q4'),
     ('states', 'off_nominal_roll'),
     ('states', 'pitch'),
     ('states', 'ccd_count')]

Timing Information
------------------

The timing data for each model component, MSID, and state are stored in the
:class:`~acispy.data_container.DataContainer` as well. Times are in units of
seconds from the beginning of the mission. These can be obtained using the
:meth:`~acispy.data_container.DataContainer.times` method:

.. code-block:: python

    print dc.times('msids', '1deamzt')

.. code-block:: pycon

    [  5.75773267e+08   5.75773300e+08   5.75773333e+08 ...,   5.76300659e+08   5.76300691e+08   5.76300724e+08] s

Since commanded states have start times and stop times, a tuple of time arrays is
returned in this case:

.. code-block:: python

    times = dc.times('states', 'pitch')
    times[0] # Gives you the start times
    times[1] # Gives you the stop times

Similarly, calling the :meth:`~acispy.data_container.DataContainer.dates` method
will return the timing data as date/time strings:

.. code-block:: python

    print dc.dates('msids', '1deamzt')

.. code-block:: pycon

    array(['2016:091:01:00:00.222', '2016:091:01:00:33.022',
           '2016:091:01:01:05.822', ..., '2016:097:03:29:51.452',
           '2016:097:03:30:24.252', '2016:097:03:30:57.052'],
          dtype='|S21')
