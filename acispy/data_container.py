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
                            filter_bad=False, stat=None):
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
        states = None
        msids = MSIDs.from_tracelog(filename)
        if state_keys is not None:
            tstart = secs2date(msids.times[msids.keys()[1]][0])
            tstop = secs2date(msids.times[msids.keys()[1]][-1])
            states = States.from_database(state_keys, tstart, tstop)
        return cls(msids, states, None)

    @classmethod
    def fetch_from_load(cls, load, comps, get_msids=False):
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