Loading Data in Python
======================

ACISpy can work with ACIS-related data from the commanded states 
database, the engineering archive, or thermal models produced by Xija. 
The first thing that must be done before any data can be worked with or 
plotted is to ingest the data in a ``DataContainer`` object. ``DataContainer`` 
objects can be created by a number of methods, which are documented here.

Fetching Data from the Online Database
--------------------------------------

Often, one will want to fetch data directly from the Chandra engineering
archive and the commanded states database within a particular date and time 
range. The method ``fetch_from_database`` enables this functionality. The 
MSIDs and states you want to extract must be specified:

.. code-block:: python

    from acispy import DataContainer
    tstart = "2016:091:01:00:00.000" 
    tstop = "2016:097:03:30:57.231"
    msids = ["1deamzt", "1dpamzt"]
    states = ["pitch", "off_nominal_roll"]
    dc = DataContainer.fetch_from_database(tstart, tstop, msid_keys=msids,
                                           state_keys=states)
                                           
Additional options are provided for filtering out bad data and choosing the
time cadence for MSIDs; for details see the API doc entry. 

Reading MSID Data From a Tracelog File
--------------------------------------

If you have a real-time tracelog file or one that has been extracted from a 
dump, you can also read MSID data from this file. In this case, the state 
data corresponding to the times spanned by the tracelog file will be extracted
from the commanded states database. 

.. code-block:: python

    from acispy import DataContainer
    states = ["pitch", "ccd_count"]
    dc = DataContainer.fetch_from_tracelog("acisENG10d_00985114479.70.tl",
                                           state_keys=states)
    
In this case, all of the MSIDs in the tracelog are ingested into the 
``DataContainer``, whereas the states that you want must be specified.

Reading Model Data from a Load
------------------------------

You can also fill a ``DataContainer`` with predicted model data for a 
particular temperature model or multiple models corresponding to a particular
load review:

.. code-block:: python

    from acispy import DataContainer
    comps = ["1deamzt","1dpamzt","fptemp_11"]
    dc = DataContainer.fetch_model_from_load("APR0416C")

To get the corresponding MSIDs from the engineering archive during the same 
time frame, pass to ``fetch_model_from_load`` the keyword argument ``get_msids=True``.

Directly Accessing Data from the Container
------------------------------------------

The ``DataContainer`` object has dictionary-like access so that the data
may be accessed directly. Data can be accessed by querying the ``DataContainer``
object with a tuple giving the type of data desired and its name, for example:

.. code-block:: python

    # "dc" is a DataContainer object
    dc["states", "pitch"] # gives you the "pitch" state
    dc["msids", "fptemp_11"] # gives you the "fptemp_11" pseudo-MSID
    dc["model", "1deamzt"] # gives you the "1deamzt" model component

We'll use our example from before to fill up a ``DataContainer``:

.. code-block:: python

    from acispy import DataContainer
    tstart = "2016:091:01:00:00.000" 
    tstop = "2016:097:03:30:57.231"
    msids = ["1deamzt", "1dpamzt"]
    states = ["pitch", "off_nominal_roll", "ccd_count"]
    dc = DataContainer.fetch_from_database(tstart, tstop, msid_keys=msids,
                                           state_keys=states)

Data are returned as NumPy arrays or AstroPy Quantities (which are just NumPy 
arrays with units attached). The following print statements:

.. code-block:: python

    print dc["states", "ccd_count"]
    print dc["states", "pitch"]
    print dc["msids", "1deamzt"]

result in the following output (or something similar):

.. code-block:: pycon

    [6  6  6 ...,  4  4  4] # ccd_count

    [ 155.78252178  155.94230537  155.95272431  ...,  142.85889318
      148.43712545  149.54367736] deg # pitch

    [ 22.14923096  22.14923096  22.14923096 ...,  20.17999268  
      20.17999268  20.17999268] deg_C # 1deamzt
