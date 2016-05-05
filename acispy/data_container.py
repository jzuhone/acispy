from acispy.msids import MSIDs
from acispy.states import States
from acispy.model import Model
from Chandra.Time import secs2date
from acispy.fields import derived_fields, create_derived_fields
from acispy.data_collection import DataCollection

create_derived_fields()

class DataContainer(object):
    def __init__(self, msids, states, model):
        self.msids = msids
        self.states = states
        self.model = model
        self._field_list = []

    def __getitem__(self, item):
        if item in derived_fields:
            self._check_derived_field(item)
            return derived_fields[item](self)
        src = getattr(self, item[0])
        return src[item[1]]

    def __contains__(self, item):
        src = getattr(self, item[0])
        return item[1] in src

    def _check_derived_field(self, item):
        deps = derived_fields[item].get_deps()
        for dep in deps:
            if dep not in self:
                raise RuntimeError("Derived field %s needs field %s, but you didn't load it!" % (item, dep))

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
        if msid_keys is not None:
            msids = MSIDs.from_database(msid_keys, tstart, tstop=tstop, 
                                       filter_bad=filter_bad, stat=stat)
        else:
            msids = DataCollection({})
        if state_keys is not None:
            states = States.from_database(state_keys, tstart, tstop)
        else:
            states = DataCollection({})
        model = DataCollection({})
        return cls(msids, states, model)

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
        states = DataCollection({})
        # Figure out what kind of file this is
        f = open(filename, "r")
        line = f.readline()
        f.close()
        if line.startswith("TIME"):
            msids = MSIDs.from_tracelog(filename)
        elif line.startswith("YEAR"):
            msids = MSIDs.from_mit_file(filename)
        else:
            raise RuntimeError("I cannot parse this file!")
        if state_keys is not None:
            tmin = 1.0e55
            tmax = -1.0e55
            for k in msids.keys():
                if k.endswith("_times"):
                    tmin = min(msids[k][0], tmin)
                    tmax = max(msids[k][-1], tmax)
            states = States.from_database(state_keys, secs2date(tmin), secs2date(tmax))
        model = DataCollection({})
        return cls(msids, states, model)

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
            msids = DataCollection({})
        return cls(msids, states, model)

    @classmethod
    def fetch_model_from_xija(cls, xija_model, comps):
        model = Model.from_xija(xija_model, comps)
        msids = DataCollection({})
        states = DataCollection({})
        return cls(msids, states, model)

    @property
    def field_list(self):
        if len(self._field_list) == 0:
            for k in ["msids", "states", "model"]:
                obj = getattr(self, k)
                self._field_list += [(k, f) for f in obj.keys()]
        return self._field_list

