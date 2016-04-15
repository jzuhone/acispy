from acispy.msids import MSIDs
from acispy.states import States
from acispy.model import Model
from Chandra.Time import secs2date
from acispy.utils import msid_units, state_units
import astropy.units as apu

class DataContainer(object):
    def __init__(self, msids, states, model):
        self.msids = msids
        self.states = states
        self.model = model
        self._keys = []
        for k in ["msids", "states", "model"]:
            obj = getattr(self, k)
            if obj is not None:
                self._keys += [(k, f) for f in obj.keys()]

    def __getitem__(self, item):
        src = getattr(self, item[0])
        if item[1] in msid_units:
            arr = src[item[1]]*getattr(apu, msid_units[item[1]])
        elif item[1] in state_units:
            arr = src[item[1]]*getattr(apu, state_units[item[1]])
        else:
            arr = src[item[1]]
        return arr

    @classmethod
    def fetch_from_database(cls, tstart, tstop, msid_keys=None, state_keys=None, 
                            filter_bad=True, stat=None):
        """
        Fetch MSIDs from the engineering archive and states from the commanded
        states database. 

        Parameters
        ----------
        tstart : string
            The start time in YYYY:DOY:HH:MM:SS format
        tstop : string
            The stop time in YYYY:DOY:HH:MM:SS format
        msid_keys : list of strings, optional
            List of MSIDs to pull from the engineering archive.
        state_keys : list of strings, optional
            List of commanded states to pull from the commanded states database.
        filter_bad : boolean, optional
            Whether or not to filter out bad values of MSIDs. Default: True.
        stat : string, optional
            return 5-minute or daily statistics ('5min' or 'daily') Default: '5min'
                    
        Examples
        --------
        >>> from acispy import DataContainer
        >>> tstart = "2016:091:12:05:00.100"
        >>> tstop = "2016:100:13:07:45.234"
        >>> states = ["pitch", "off_nominal_roll"]
        >>> dc = DataContainer.fetch_from_database(tstart, tstop, msid_keys=msids,
        ...                                        state_keys=states)
        """
        msids = None
        states = None
        if msid_keys is not None:
            msids = MSIDs.from_database(msid_keys, tstart, tstop=tstop, 
                                       filter_bad=filter_bad, stat=stat)
        if state_keys is not None:
            states = States.from_database(state_keys, tstart, tstop)
        return cls(msids, states, None)

    @classmethod
    def fetch_from_tracelog(cls, filename, state_keys=None):
        """
        Fetch MSIDs from a tracelog file and states from the commanded
        states database.

        Parameters
        ----------
        filename : string
            The path to the tracelog file
        state_keys : list of strings, optional
            List of commanded states to pull from the commanded states database.

        Examples
        --------
        >>> from acispy import DataContainer
        >>> states = ["ccd_count", "roll"]
        >>> dc = DataContainer.fetch_from_tracelog("acisENG10d_00985114479.70.tl",
        ...                                        state_keys=states)
        """
        states = None
        msids = MSIDs.from_tracelog(filename)
        if state_keys is not None:
            tstart = secs2date(msids.times[msids.keys()[1]][0])
            tstop = secs2date(msids.times[msids.keys()[1]][-1])
            states = States.from_database(state_keys, tstart, tstop)
        return cls(msids, states, None)

    @classmethod
    def fetch_model_from_load(cls, load, comps, get_msids=False):
        """
        Fetch a temperature model and its associated commanded states
        from a load review. Optionally get MSIDs for the same time period.

        Parameters
        ----------
        load : string
            The load review to get the model from, i.e. "JAN2516A"
        comps : list of strings
            List of temperature components to get from the load models.
        get_msids : boolean, optional
            Whether or not to load the MSIDs corresponding to the 
            temperature models for the same time period from the 
            engineering archive. Default: False.

        Examples
        --------
        >>> from acispy import DataContainer
        >>> comps = ["1deamzt", "1pdeaat", "fptemp_11"]
        >>> dc = DataContainer.fetch_model_from_load("APR0416C", comps, get_msids=True)
        """
        model = Model.from_load(load, comps)
        states = States.from_load(load)
        if get_msids:
            tstart = states["datestart"][0]
            tstop = states["datestop"][-1]
            msids = MSIDs.from_database(comps, tstart, tstop=tstop,
                                        filter_bad=True)
        else:
            msids = None
        return cls(msids, states, model)

    def keys(self):
        return self._keys