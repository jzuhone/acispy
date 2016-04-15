from astropy.io import ascii
import requests
from acispy.utils import get_time, calc_off_nom_rolls
import numpy as np
from Chandra.cmd_states import fetch_states
from astropy.table import Table

class States(object):

    def __init__(self, table):
        self.table = table
        if set(["q1","q2","q3","q4"]) < set(self.table.keys()):
            self.table["off_nominal_roll"] = calc_off_nom_rolls(table)

    @classmethod
    def from_database(cls, states, tstart, tstop):
        st = states[:]
        if "off_nominal_roll" in states:
            st.remove("off_nominal_roll")
            st += ["q1", "q2", "q3", "q4"]
        t = fetch_states(tstart, tstop, vals=st)
        table = dict((k, t[k]) for k in t.dtype.names)
        return cls(table)

    @classmethod
    def from_load(cls, load):
        url = "http://cxc.cfa.harvard.edu/acis/DPA_thermPredic/"
        url += "%s/ofls%s/states.dat" % (load[:-1].upper(), load[-1].lower())
        u = requests.get(url)
        t = ascii.read(u.text)
        table = dict((k, t[k].data) for k in t.keys())
        return cls(table)

    def __getitem__(self, item):
        return self.table[item]

    def keys(self):
        return self.table.keys()

    def get_states(self, time):
        time = get_time(time).secs
        # We have this if we need it
        err = "The time %s is not within the selected time frame!" % time
        if time < self["tstart"][0]:
            raise RuntimeError(err)
        idx = np.searchsorted(self["tstart"], time)-1
        try:
            self["tstart"][idx]
        except IndexError:
            raise RuntimeError(err)
        state = {}
        for key in self.keys():
            state[key] = self[key][idx]
        return state

    @property
    def current_states(self):
        return self.get_states("now")

    def write_ascii(self, filename):
        Table(self.table).write(filename, format='ascii')