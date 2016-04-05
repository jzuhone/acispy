from astropy.io import ascii
import requests
from acis.utils import get_time, calc_off_nom_rolls
import numpy as np
from Chandra.cmd_states import fetch_states
from astropy.table import Table

class States(object):

    def __init__(self, table, keys):
        self.table = table
        self._time_start = self.table["tstart"]
        self._off_nominal_roll = calc_off_nom_rolls(table)
        self._keys = list(keys)

    @classmethod
    def from_database(cls, states, tstart, tstop):
        st = states[:]
        if "off_nominal_roll" in states:
            st.remove("off_nominal_roll")
            st += ["q1", "q2", "q3", "q4"]
        t = fetch_states(tstart, tstop, vals=st)
        return cls(t, t.dtype.names)

    @classmethod
    def from_load(cls, load):
        """
        Get the states table for a particular component and load from the web.
        :param component: The component to get the states for, e.g. "FP" for focal plane.
        :param load: The identifier for the load, e.g. "JAN1116A"
        :return: The States instance.
        """
        url = "http://cxc.cfa.harvard.edu/acis/DPA_thermPredic/"
        url += "%s/ofls%s/states.dat" % (load[:-1].upper(), load[-1].lower())
        u = requests.get(url)
        t = ascii.read(u.text)
        return cls(t.as_array(), t.keys())

    def __getitem__(self, item):
        if item == "off_nominal_roll":
            return self._off_nominal_roll
        else:
            return self.table[item]

    def keys(self):
        return self._keys

    def get_states(self, time):
        """
        Get the state data at a particular time.
        :param time: The time to get the states at. Can be in 
            yday format, an AstroPy Time object, or "now".
        :return: A dictionary of the states.
        """
        time = get_time(time).secs
        # We have this if we need it
        err = "The time %s is not within the selected time frame!" % time
        if time < self._time_start[0]:
            raise RuntimeError(err)
        idx = np.searchsorted(self._time_start, time)-1
        try:
            self._time_start[idx]
        except IndexError:
            raise RuntimeError(err)
        state = {}
        for key in self.keys():
            state[key] = self[key][idx]
        if self._off_nominal_roll is not None:
            state["off_nominal_roll"] = self._off_nominal_roll[idx]
        return state

    @property
    def current_states(self):
        return self.get_state("now")

    def write_ascii(self, filename):
        Table(self.table).write(filename, format='ascii')