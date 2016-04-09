from acis_pytools.msids import MSIDs
from acis_pytools.states import States
from acis_pytools.model import Model
from Chandra.Time import secs2date

class DataSource(object):
    def __init__(self, msids, states, model):
        self.msids = msids
        self.states = states
        self.model = model

    def __getitem__(self, item):
        src = getattr(self, item[0])
        return src[item[1]]

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
            tstart = secs2date(msids.time[0])
            tstop = secs2date(msids.time[-1])
            states = States.from_database(state_keys, tstart, tstop)
        return cls(msids, states, None)

    @classmethod
    def fetch_from_load(cls, load, comps):
        model = Model.from_load(load, comps)
        states = States.from_load(load)
        return cls(None, states, model)