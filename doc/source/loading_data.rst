.. _loading-data:

Loading Data in Python
======================

ACISpy can work with ACIS-related data from the commanded states 
database, the engineering archive, or thermal models produced by Xija. 
The first thing that must be done before any data can be worked with or 
plotted is to ingest the data in a :class:`~acispy.dataset.Dataset`
object. :class:`~acispy.dataset.Dataset` objects can be created by a
number of methods, which are documented here.

Fetching Data from the Online Database
--------------------------------------

Often, one will want to fetch data directly from the Chandra engineering
archive and the commanded states database within a particular date and time 
range. The :class:`~acispy.dataset.ArchiveData` class enables this
functionality. The MSIDs you want to extract must be specified. You may
either specify a set of states using the ``state_keys`` keyword argument;
otherwise the full default set will be loaded.

.. code-block:: python

    from acispy import ArchiveData
    tstart = "2016:091:01:00:00.000" 
    tstop = "2016:097:03:30:57.231"
    msids = ["1deamzt", "1dpamzt"]
    states = ["pitch", "ccd_count"]
    ds = ArchiveData(tstart, tstop, msid_keys=msids, state_keys=states)

By default, the MSIDs are not at identical time values. You can enforce that
the MSID data is interpolated to a common set of times by passing in the keyword
argument ``interpolate_msids=True``:

.. code-block:: python

    ds = ArchiveData(tstart, tstop, msid_keys=msids, interpolate_msids=True)

Additional options are provided for filtering out bad data and choosing the
time cadence for MSIDs; for details see the API doc entry for 
:class:`~acispy.dataset.ArchiveData.

Reading MSID Data From a Tracelog File
--------------------------------------

If you have a real-time tracelog file or one that has been extracted from a 
dump, you can also read MSID data from this file, using the
:meth:`~acispy.data_container.Dataset.fetch_from_tracelog` method. In
this case, the state data corresponding to the times spanned by the tracelog
file will be extracted from the commanded states database. 

.. code-block:: python

    from acispy import Dataset
    states = ["pitch", "ccd_count"]
    ds = Dataset.fetch_from_tracelog("acisENG10d_00985114479.70.tl",
                                           state_keys=states)
    
In this case, all of the MSIDs in the tracelog are ingested into the 
:class:`~acispy.data_container.Dataset`. You may either specify
a set of states using the ``state_keys`` keyword argument; otherwise 
the full default set will be loaded.

Reading Model Data from a Load
------------------------------

You can also fill a :class:`~acispy.data_container.Dataset` with predicted
model data for a particular temperature model or multiple models corresponding to 
a particular load review using :meth:`~acispy.data_container.Dataset.fetch_model_from_load`:

.. code-block:: python

    from acispy import Dataset
    comps = ["1deamzt","1dpamzt","fptemp_11"]
    ds = Dataset.fetch_model_from_load("APR0416C", comps)

To get the corresponding MSIDs from the engineering archive during the same 
time frame, pass to :meth:`~acispy.data_container.Dataset.fetch_model_from_load`
the keyword argument ``get_msids=True``. To interpolate the MSID data to a common
set of times as the model data, use ``interpolate_msids=True``.

Reading Model Data from Files
-----------------------------

The model validation tools (such as `dea_check <http://github.com/acisops/dea_check>`_)
output ASCII table files ``"temperatures.dat"`` and ``"states.dat"`` that contain the 
temperature and commanded state information as a function of time. If you have these
files and would like to load them in, this can be done using the
:meth:`~acispy.data_container.Dataset.fetch_models_from_files` method:

.. code-block:: python

    from acispy import Dataset
    model_files = ["dea_model/temperatures.dat", "dpa_model/temperatures.dat",
                   "fp_model/temperatures.dat"]
    ds = Dataset.fetch_models_from_files(model_files, "dea_model/states.dat",
                                               get_msids=True)
                                               
Like the previous method, this one takes the ``get_msids`` keyword argument to 
obtain the corresponding MSIDs from the archive if desired. To interpolate the 
MSID data to a common set of times as the model data, use ``interpolate_msids=True``.
However, this only really works if the all of the model fields are also at the same
times. 

This method can also be used to import model data for the same MSID for different
model runs:

.. code-block:: python

    from acispy import Dataset
    model_files = ["old_model/temperatures.dat", "new_model/temperatures.dat"]
    ds = Dataset.fetch_models_from_files(model_files, "old_model/states.dat",
                                               get_msids=True)

Directly Accessing Times Series Data from the Container
-------------------------------------------------------

The :class:`~acispy.data_container.Dataset` object has dictionary-like
access so that the data may be accessed directly. Data can be accessed by querying 
the :class:`~acispy.data_container.Dataset` object with a tuple giving the
type of data desired and its name, for example:

.. code-block:: python

    # "ds" is a Dataset object
    ds["states", "pitch"] # gives you the "pitch" state
    ds["msids", "fptemp_11"] # gives you the "fptemp_11" pseudo-MSID
    ds["model", "1deamzt"] # gives you the "1deamzt" model component

A ``(type, name)`` pairing and its associated data are referred to as a "field". We'll
encounter examples of :ref:`derived-fields` later, which are derivations of new fields from
existing ones. For now, we'll use our example from before to fill up a 
:class:`~acispy.data_container.Dataset`:

.. code-block:: python

    from acispy import Dataset
    tstart = "2016:091:01:00:00.000" 
    tstop = "2016:097:03:30:57.231"
    msids = ["1deamzt", "1dpamzt"]
    states = ["pitch", "ccd_count"]
    ds = Dataset.fetch_from_database(tstart, tstop, msid_keys=msids,
                                           state_keys=states)

To see what fields are available from the :class:`~acispy.data_container.Dataset`,
check the `field_list` attribute:

.. code-block:: python

    print ds.field_list

.. code-block:: pycon

    [('msids', '1deamzt'),
     ('msids', '1dpamzt'),
     ('states', 'datestart'),
     ('states', 'datestop'),
     ('states', 'tstart'),
     ('states', 'tstop'),
     ('states', 'q1'),
     ('states', 'q3'),
     ('states', 'q2'),
     ('states', 'q4'),
     ('states', 'pitch'),
     ('states', 'ccd_count')]

If you have loaded data for the same model component from more than one model, then
these will appear in the :class:`~acispy.data_container.Dataset` with field types
of the form ``"model[n]"``, where ``n`` is a a zero-based integer:

.. code-block:: python

    from acispy import Dataset
    model_files = ["old_model/temperatures.dat", "new_model/temperatures.dat"]
    ds = Dataset.fetch_models_from_files(model_files, "old_model/states.dat",
                                               get_msids=True)
    print ds.field_list

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
The following print statements illustrate how units are attached to various
types of arrays:

.. code-block:: python

    print ds["states", "ccd_count"]
    print ds["states", "pitch"]
    print ds["msids", "1deamzt"]

.. code-block:: pycon

    [6  6  6 ...,  4  4  4]

    [ 155.78252178  155.94230537  155.95272431  ...,  142.85889318
      148.43712545  149.54367736] deg

    [ 22.14923096  22.14923096  22.14923096 ...,  20.17999268  
      20.17999268  20.17999268] deg_C

Note that some arrays (like ``ccd_count'') do not have units. 

Masks
+++++

Model data may include "bad times" where the model does not agree well with
the actual telemetry, most likely because there was an unexpected event such
as a safing action. All ACISpy arrays include a ``mask`` attribute, which is
a boolean NumPy array the same shape as the array, which is ``True`` if the 
array is well-defined at that time and ``False`` if it is not. Currently, 
masks only have ``False`` values for model arrays:

.. code-block:: python
    
    print ds["model", "1dpamzt"].mask

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

    print ds["states", "pitch"].times
    print ds["msids", "1deamzt"].times

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

    print ds["states", "pitch"].dates
    print ds["msids", "1deamzt"].dates

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

    ds["msids", "1pdeaat"][1]
    ds["states", "ccd_count"][2:100]
    
However, it is also possible to index and slice arrays with timing information, 
whether with floating-point numbers (corresponding to seconds from the beginning
of the mission) or date-time strings:

.. code-block:: python

    ds["states", "pitch"][5.762e8] # indexing with a single time value
    
    ds["msids", "1deicacu"][5.5e8:5.6e8] # slicing between two time values
    
    ds["states", "fep_count"]["2016:091:03:25:40.500"] # indexing with a single date-time string
    
    ds["msids", "1pin1at"]["2017:050:00:00:00":"2017:060:00:00:00"] # slicing between two date-time strings

Timing Information
------------------

The timing data for each model component, MSID, and state can also be easily
accessed from the :meth:`~acispy.data_container.Dataset.times` and
:meth:`~acispy.data_container.Dataset.dates` methods:

.. code-block:: python

    print ds.times('msids', '1deamzt')

.. code-block:: pycon

    [  5.75773267e+08   5.75773300e+08   5.75773333e+08 ...,   5.76300659e+08   5.76300691e+08   5.76300724e+08] s

.. code-block:: python

    times = ds.times('states', 'pitch')
    times[0] # Gives you the start times
    times[1] # Gives you the stop times

.. code-block:: python

    print ds.dates('msids', '1deamzt')

.. code-block:: pycon

    ['2016:091:01:00:00.222', '2016:091:01:00:33.022',
     '2016:091:01:01:05.822', ..., '2016:097:03:29:51.452',
     '2016:097:03:30:24.252', '2016:097:03:30:57.052']
