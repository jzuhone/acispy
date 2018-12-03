.. _loading-data:

Loading Data in Python
======================

ACISpy can work with ACIS-related data from the commanded states 
database, the engineering archive, or thermal models produced by Xija. 
The first thing that must be done before any data can be worked with or 
plotted is to ingest the data in a :class:`~acispy.dataset.Dataset`
object. :class:`~acispy.dataset.Dataset` objects can be created by a
number of methods, which are documented here.

Fetching MSID Data from the Engineering Archive
-----------------------------------------------

Often, one will want to fetch data directly from the Chandra engineering
archive and the commanded states database within a particular date and time 
range. The :class:`~acispy.dataset.EngArchiveData` class enables this
functionality. The MSIDs you want to extract must be specified. The full set
of commanded states are also loaded. 

.. code-block:: python

    from acispy import EngArchiveData
    tstart = "2016:091:01:00:00.000" 
    tstop = "2016:097:03:30:57.231"
    msids = ["1deamzt", "1dpamzt"]
    ds = EngArchiveData(tstart, tstop, msids)

By default, the MSIDs are not at identical time values. You can enforce that
the MSID data is interpolated to a common set of times by passing in the keyword
argument ``interpolate_msids=True``:

.. code-block:: python

    ds = EngArchiveData(tstart, tstop, msids, interpolate_msids=True)

Additional options are provided for filtering out bad data and choosing the
time cadence for MSIDs; for details see the API doc entry for 
:class:`~acispy.dataset.EngArchiveData.

Fetching MSID Data From a Tracelog File
---------------------------------------

If you have a real-time tracelog file or one that has been extracted from a 
dump, you can also read MSID data from this file, using
:class:`~acispy.dataset.TracelogData`. In this case, the state data 
corresponding to the times spanned by the tracelog file will be extracted 
from the commanded states database. 

.. code-block:: python

    from acispy import TracelogData
    ds = TracelogData("acisENG10d_00985114479.70.tl")
    
In this case, all of the MSIDs in the tracelog are ingested into the 
:class:`~acispy.dataset.TracelogData` dataset. The full set of commanded 
states are also loaded. You can also specify a subset of the time range in 
the tracelog using the ``tbegin`` and ``tend`` arguments:

.. code-block:: python

    from acispy import TracelogData
    ds = TracelogData("some_data.tl", tbegin="2017:100", tend="2017:110:01:45:45")

Special Tracelog Files
++++++++++++++++++++++

There are three special classes for working with the 10-day tracelog file data,
which an be used to obtain the data from these tracelog files which are updated
every time there is a comm and have the last 10 days of data. They are:

* :class:`~acispy.dataset.EngineeringTracelogData`: The engineering data tracelog
* :class:`~acispy.dataset.DEAHousekeepingTracelogData`: The DEA housekeeping data tracelog
* :class:`~acispy.dataset.TenDayTracelogData`: Both tracelogs combined

You do not have to specify the tracelog file for these classes, but they will
accept any other arguments also accepted by :class:`~acispy.dataset.TracelogData`:

.. code-block:: python

    from acispy import EngineeringTracelogData
    ds = EngineeringTracelogData(tbegin="2018:060:00:00:00", tend="2018:061:02:30:00")

Fetching MSID Data from MAUDE
-----------------------------

ACISPy can also access data from the MAUDE telemetry server. You must set up authentication 
to OCCWEB, for which there is some documentation
`here <http://cxc.cfa.harvard.edu/mta/ASPECT/tool_doc/maude/#setup-for-authentication>`_.

To access data from MAUDE, simply use the :class:`~acispy.dataset.MaudeData` class and 
provide a starting time, stopping time, and the list of MSIDs that you want. State data
will be accessed using the commanded states database automatically. 

.. code-block:: python

    from acispy import MaudeData
    datestart = "2017:336:12:00:00"
    datestop = "2017:337:12:00:00"
    msids = ["1dpamzt", "1deamzt"]
    ds = MaudeData(datestart, datestop, msids)

Reading Model Data from a Load
------------------------------

You can also fill a :class:`~acispy.dataset.Dataset` with predicted
model data for a particular temperature model or multiple models corresponding to 
a particular load review using :class:`~acispy.thermal_models.ThermalModelFromLoad`:

.. code-block:: python

    from acispy import ThermalModelFromLoad
    comps = ["1deamzt","1dpamzt","fptemp_11"]
    ds = ThermalModelFromLoad("APR0416C", comps)

To get the corresponding MSIDs from the engineering archive during the same 
time frame, pass to :class:`~acispy.thermal_models.ThermalModelFromLoad` the keyword
argument ``get_msids=True``.

Reading Model Data from Files
-----------------------------

The model validation tools (such as `dea_check <http://github.com/acisops/dea_check>`_)
output ASCII table files ``"temperatures.dat"`` and ``"states.dat"`` that contain the 
temperature and commanded state information as a function of time. If you have these
files and would like to load them in, this can be done using
::class:`~acispy.thermal_models.ThermalModelFromFiles`:

.. code-block:: python

    from acispy import ThermalModelFromFiles
    model_files = ["dea_model/temperatures.dat", "dpa_model/temperatures.dat",
                   "fp_model/temperatures.dat"]
    ds = ThermalModelFromFiles(model_files, "dea_model/states.dat", get_msids=True)
                                               
Like the previous :class:`~acispy.dataset.Dataset` type, this one takes the 
``get_msids`` keyword argument to obtain the corresponding MSIDs from the archive 
if desired.

This :class:`~acispy.dataset.Dataset` type can also be used to import model data 
for the same MSID for different model runs:

.. code-block:: python

    from acispy import ThermalModelFromFiles
    model_files = ["old_model/temperatures.dat", "new_model/temperatures.dat"]
    ds = ThermalModelFromFiles(model_files, "old_model/states.dat", get_msids=True)

Directly Accessing Time Series Data from the Container
------------------------------------------------------

The :class:`~acispy.dataset.Dataset` object has dictionary-like
access so that the data may be accessed directly. Data can be accessed by querying 
the :class:`~acispy.dataset.Dataset` object with a tuple giving the
type of data desired and its name, for example:

.. code-block:: python

    # "ds" is a Dataset object
    ds["states", "pitch"] # gives you the "pitch" state
    ds["msids", "fptemp_11"] # gives you the "fptemp_11" pseudo-MSID
    ds["model", "1deamzt"] # gives you the "1deamzt" model component

A ``(type, name)`` pairing and its associated data are referred to as a "field". We'll
encounter examples of :ref:`derived-fields` later, which are derivations of new fields from
existing ones.

It is not strictly necessary to specify the ``(type, name)`` tuple if the ``name`` is 
unique in the :class:`~acispy.dataset.Dataset` object. So the fields in the last
block could also be accessed like this:

.. code-block:: python

    ds["pitch"] # gives you the "pitch" state
    ds["fptemp_11"] # gives you the "fptemp_11" pseudo-MSID
    ds["1deamzt"] # gives you the "1deamzt" model component

However, if the ``name`` is not unique (say it exists both as MSID data and a model 
component), then an error will be raised:

.. code-block:: python

    # "ds" is a Dataset object
    ds["pitch"] # gives you the "pitch" state
    ds["fptemp_11"] # gives you the "fptemp_11" pseudo-MSID
    ds["1deamzt"] # gives you the "1deamzt" model component


We'll use our example from before to fill up a :class:`~acispy.dataset.Dataset`:

.. code-block:: python

    from acispy import EngArchiveData
    tstart = "2016:091:01:00:00.000" 
    tstop = "2016:097:03:30:57.231"
    msids = ["1deamzt", "1dpamzt"]
    ds = EngArchiveData(tstart, tstop, msids)

To see what fields are available from the :class:`~acispy.dataset.Dataset`,
check the `field_list` attribute:

.. code-block:: python

    print(ds.field_list)

.. code-block:: pycon

    [('msids', '1deamzt'),
     ('msids', '1dpamzt'),
     ('states', 'datestart'),
     ('states', 'datestop'),
     ('states', 'tstart'),
     ('states', 'tstop'),
     ('states', 'q1'),
     ...
     ('states', 'q3'),
     ('states', 'q2'),
     ('states', 'q4'),
     ('states', 'pitch'),
     ('states', 'ccd_count')]

If you have loaded data for the same model component from more than one model, then
these will appear in the :class:`~acispy.dataset.Dataset` with field types
of the form ``"model[n]"``, where ``n`` is a a zero-based integer:

.. code-block:: python

    from acispy import ThermalModelFromFiles
    model_files = ["old_model/temperatures.dat", "new_model/temperatures.dat"]
    ds = ThermalModelFromFiles(model_files, "old_model/states.dat", get_msids=True)
    print(ds.field_list)

gives:

.. code-block:: pycon

    [('model0', '1pdeaat'),
     ('model1', '1pdeaat'),
     ('states', 'q1'),
     ('states', 'q3'),
     ('states', 'q2'),
     ('states', 'q4'),
     ...
     ('states', 'pitch'),
     ('states', 'ccd_count')]

ACISpy Arrays
-------------

Data are returned as "ACISpy arrays", which are simply NumPy arrays with a
number of important attributes included. 

Units
+++++

One such attribute is units, for those quantities which possess them. Units are
added to ACISpy arrays using 
`AstroPy Quantities <http://docs.astropy.org/en/stable/units/quantity.html>`_. 
The following ``print`` statements illustrate how units are attached to various
types of arrays:

.. code-block:: python

    print(ds["ccd_count"])
    print(ds["pitch"])
    print(ds["1deamzt"])

.. code-block:: pycon

    [6  6  6 ...,  4  4  4]

    [ 155.78252178  155.94230537  155.95272431  ...,  142.85889318
      148.43712545  149.54367736] deg

    [ 22.14923096  22.14923096  22.14923096 ...,  20.17999268  
      20.17999268  20.17999268] deg_C

Note that some arrays (like ``ccd_count``) do not have units.

Masks
+++++

Model data may include "bad times" where the model does not agree well with
the actual telemetry, most likely because there was an unexpected event such
as a safing action. All ACISpy arrays include a ``mask`` attribute, which is
a boolean NumPy array the same shape as the array, which is ``True`` if the 
array is well-defined at that time and ``False`` if it is not. Currently, 
masks only have ``False`` values for model arrays:

.. code-block:: python
    
    print(ds["1dpamzt"].mask)

.. code-block:: pycon

    [ True  False  False  False ...,  True  True  True]

In future versions, masks will be also included for MSID data which have known 
"bad" values at certain times.

Timing Information
++++++++++++++++++

Since the MSIDs and states are defined at given times, each ACISpy array has 
timing information associated with it. The ``times`` attribute for a given 
array gives the timing information in seconds from the beginning of the mission:

.. code-block:: python

    print(ds["pitch"].times)
    print(ds["1deamzt"].times)

prints something like:

.. code-block:: pycon

    [[  5.75763786e+08   5.75775250e+08   5.75775555e+08   5.75775860e+08
        5.75776165e+08   5.75776470e+08   5.75776775e+08   5.75777080e+08
        ...
        5.76285868e+08   5.76286168e+08   5.76286301e+08   5.76286325e+08
        5.76286469e+08   5.76286769e+08   5.76287070e+08   5.76287370e+08]
     [  5.75775250e+08   5.75775555e+08   5.75775860e+08   5.75776165e+08
        5.75776470e+08   5.75776775e+08   5.75777080e+08   5.75777385e+08
        ...
        5.76286168e+08   5.76286301e+08   5.76286325e+08   5.76286469e+08
        5.76286769e+08   5.76287070e+08   5.76287370e+08   5.76330630e+08]] s

     [  5.75773267e+08   5.75773300e+08   5.75773333e+08 ...,   5.76300659e+08
        5.76300691e+08   5.76300724e+08] s

Note that state times are two-dimensional arrays, of shape ``(2, n)``, since
each state spans a ``tstart`` and a ``tstop``. 

Similiarly, the ``dates`` attribute contains the same information in terms of
date-time strings:

.. code-block:: python

    print(ds["pitch"].dates)

.. code-block:: pycon

    [['2016:090:22:21:58.350' '2016:091:01:33:03.014' '2016:091:01:38:07.997'
      '2016:091:01:43:12.980' '2016:091:01:48:17.963' '2016:091:01:53:22.946'
      ...
      '2016:096:23:30:33.579' '2016:096:23:30:57.579' '2016:096:23:33:21.437'
      '2016:096:23:38:21.901' '2016:096:23:43:22.366' '2016:096:23:48:22.830']
     ['2016:091:01:33:03.014' '2016:091:01:38:07.997' '2016:091:01:43:12.980'
      '2016:091:01:48:17.963' '2016:091:01:53:22.946' '2016:091:01:58:27.929'
      ...
      '2016:096:23:30:57.579' '2016:096:23:33:21.437' '2016:096:23:38:21.901'
      '2016:096:23:43:22.366' '2016:096:23:48:22.830' '2016:097:11:49:22.579']]

Indexing and Slicing ACISpy Arrays
++++++++++++++++++++++++++++++++++

ACISpy arrays can be sliced and indexed using integers to access subsets of arrays
in the usual way:

.. code-block:: python

    ds["1pdeaat"][1]
    ds["ccd_count"][2:100]
    
However, it is also possible to index and slice arrays with timing information, 
whether with floating-point numbers (corresponding to seconds from the beginning
of the mission) or date-time strings:

.. code-block:: python

    ds["pitch"][5.762e8] # indexing with a single time value
    
    ds["1deicacu"][5.5e8:5.6e8] # slicing between two time values
    
    ds["fep_count"]["2016:091:03:25:40.500"] # indexing with a single date-time string
    
    ds["1pin1at"]["2017:050:00:00:00":"2017:060:00:00:00"] # slicing between two date-time strings

Timing Information
------------------

The timing data for each model component, MSID, and state can also be easily
accessed from the :meth:`~acispy.dataset.Dataset.times` and
:meth:`~acispy.dataset.Dataset.dates` methods:

.. code-block:: python

    print(ds.times('1deamzt'))

.. code-block:: pycon

    [  5.75773267e+08   5.75773300e+08   5.75773333e+08 ...,   5.76300659e+08   5.76300691e+08   5.76300724e+08] s

.. code-block:: python

    times = ds.times('pitch')
    times[0] # Gives you the start times
    times[1] # Gives you the stop times

.. code-block:: python

    print(ds.dates('1deamzt'))

.. code-block:: pycon

    ['2016:091:01:00:00.222', '2016:091:01:00:33.022',
     '2016:091:01:01:05.822', ..., '2016:097:03:29:51.452',
     '2016:097:03:30:24.252', '2016:097:03:30:57.052']
