from astropy.io import ascii
import requests
from acis.utils import get_time, calc_off_nom_rolls
import numpy as np
from Chandra.cmd_states import fetch_states
from astropy.table import Table

class States(object):

    def __init__(self, table, keys):
        self.time = 0.5*(table["tstart"]+table["tstop"])
        self.table = table
        self._time_start = self.table["tstart"]
        self._off_nominal_roll = calc_off_nom_rolls(table)
        self._keys = list(keys)

    @classmethod
    def from_database(cls, states, tstart, tstop):
        t = fetch_states(tstart, tstop, vals=states)
        return cls(t, t.dtype.names)

    @classmethod
    def from_file(cls, filename):
        t = ascii.read(filename)
        return cls(t.as_array(), t.keys())

    @classmethod
    def from_webpage(cls, component, load):
        """
        Get the states table for a particular component and load from the web.
        :param component: The component to get the states for, e.g. "FP" for focal plane.
        :param load: The identifier for the load, e.g. "JAN1116A"
        :return: The States instance.
        """
        url = "http://cxc.cfa.harvard.edu/acis/%s_thermPredic/" % component.upper()
        url += "%s/ofls%s/states.dat" % (load[:-1].upper(), load[-1].lower())
        u = requests.get(url)
        return cls.from_file(u.text)

    def __getitem__(self, item):
        if item == "off_nominal_roll":
            return self._off_nominal_roll
        else:
            return self.table[item]

    def keys(self):
        return self._keys

    def get_state(self, time):
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
    def current_state(self):
        return self.get_state("now")

    def write_ascii(self, filename):
        Table(self.table).write(filename, format='ascii')

class MSIDs(object):
    def __init__(self, time, table, keys):
        self.time = time
        self.table = table
        self._keys = list(keys)

    @classmethod
    def from_tracelog(cls, filename):
        data = ascii.read(filename, format='csv', delimiter="\t", guess=False)
        return cls(data["TIME"]-410227200., data.as_array(), data.keys())

    @classmethod
    def from_archive(cls, msids, tstart, tstop=None, filter_bad=False,
                     stat=None):
        data = fetch.MSIDset(msids, tstart, stop=tstop, filter_bad=filter_bad,
                             stat=None)
        table = dict((k, data[k].vals) for k in data.keys())
        return cls(get_time(data[msids[0]].times).secs, table, data.keys())

    @classmethod
    def from_file(cls, filename):
        table = ascii.read(filename)
        return cls(table["time"].data, {table.colnames[-1]: table.columns[-1].data},
                   [table.colnames[-1]])

    @classmethod
    def from_webpage(cls, component, load):
        """
        Get the temperature model for a particular component and load from the web.
        :param component: The component to get the temperature for, e.g. "FP" for focal plane.
        :param load: The identifier for the load, e.g. "JAN1116A"
        :return: The TemperatureModel instance. 
        """
        url = "http://cxc.cfa.harvard.edu/acis/%s_thermPredic/" % component.upper()
        url += "%s/ofls%s/temperatures.dat" % (load[:-1].upper(), load[-1].lower())
        u = requests.get(url)
        return cls.from_file(u.text)

    @classmethod
    def from_model(cls, model, comps):
        table = dict((k,  model.comp[k].mvals) for k in comps)
        return cls(model.times, table)

    def __getitem__(self, item):
        return self.table[item]

    def keys(self):
        return self._keys

    def write_ascii(self, filename):
        Table(self.table).write(filename, format='ascii')
