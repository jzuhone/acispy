from astropy.io import ascii
import requests
from acispy.utils import get_time, state_units
import numpy as np
from Chandra.cmd_states import fetch_states
from astropy.units import Quantity
from acispy.time_series import TimeSeriesData

cmd_state_codes = {("states", "hetg"): {"RETR": 0, "INSR": 1},
                   ("states", "letg"): {"RETR": 0, "INSR": 1},
                   ("states", "dither"): {"DISA": 0, "ENAB": 1},
                   ("states", "pcad_mode"): {"STBY": 0, "NPNT": 1, "NMAN": 2, "NSUN": 3, "PWRF": 4, "RMAN": 5, "NULL": 6}}

class States(TimeSeriesData):

    def __init__(self, table):
        self.table = {}
        self.times = {}
        for k, v in table.items():
            if k in state_units:
                self.table[k] = Quantity(v, state_units[k])
            else:
                self.table[k] = v
            self.times[k] = Quantity(np.array([table["tstart"],
                                               table['tstop']]), 's')

    @classmethod
    def from_database(cls, tstart, tstop, states=None):
        t = fetch_states(tstart, tstop, vals=states)
        table = dict((k, t[k]) for k in t.dtype.names)
        return cls(table)

    @classmethod
    def from_load_page(cls, load):
        url = "http://cxc.cfa.harvard.edu/acis/DPA_thermPredic/"
        url += "%s/ofls%s/states.dat" % (load[:-1].upper(), load[-1].lower())
        u = requests.get(url)
        t = ascii.read(u.text)
        table = dict((k, t[k].data) for k in t.keys())
        # hack
        if 'T_pin1at' in table:
            table.pop("T_pin1at")
        return cls(table)

    @classmethod
    def from_load_file(cls, states_file):
        t = ascii.read(states_file)
        table = dict((k, t[k].data) for k in t.keys())
        # hack
        if 'T_pin1at' in table:
            table.pop("T_pin1at")
        return cls(table)

    def get_states(self, time):
        time = get_time(time).secs
        self[self.keys()[0]]
        # We have this if we need it
        err = "The time %s is not within the selected time frame!" % time
        if time < self.times[self.keys()[0]][0][0].value:
            raise RuntimeError(err)
        idx = np.searchsorted(self.times[self.keys()[0]][0].value, time)-1
        try:
            self.times[self.keys()[0]][0][idx]
        except IndexError:
            raise RuntimeError(err)
        state = {}
        for key in self.keys():
            state[key] = self[key][idx]
        return state

    @property
    def current_states(self):
        return self.get_states("now")
