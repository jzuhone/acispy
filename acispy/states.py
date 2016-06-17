from astropy.io import ascii
import requests
from acispy.utils import get_time, calc_off_nom_rolls, state_units
import numpy as np
from Chandra.cmd_states import fetch_states
from astropy.units import Quantity
from acispy.time_series import TimeSeriesData

class States(TimeSeriesData):

    def __init__(self, table):
        self.table = {}
        self.times = {}
        for k, v in table.items():
            if k not in ["tstart","tstop","datestart","datestop"]:
                if k in state_units:
                    self.table[k] = Quantity(v, state_units[k])
                else:
                    self.table[k] = v
                self.times[k] = Quantity(np.array([table["tstart"],
                                                   table['tstop']]), 's')
        if set(["q1","q2","q3","q4"]) < set(self.table.keys()):
            self.table["off_nominal_roll"] = Quantity(calc_off_nom_rolls(table), 'deg')
            self.times["off_nominal_roll"] = Quantity(np.array([table["tstart"],
                                                                table['tstop']]), 's')

    @classmethod
    def from_database(cls, states, tstart, tstop):
        if states is "default":
            states = ["q1","q2","q3","q4","pitch","ccd_count","clocking","ra",
                      "dec","roll","fep_count","simpos","vid_board"]
        st = states[:]
        if "off_nominal_roll" in states:
            st.remove("off_nominal_roll")
            st += ["q1", "q2", "q3", "q4"]
        t = fetch_states(tstart, tstop, vals=st)
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
