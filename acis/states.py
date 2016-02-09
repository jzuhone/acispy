from astropy.io import ascii
import astropy.units as u
from scipy.interpolate import InterpolatedUnivariateSpline
import requests
from acis.utils import get_time, calc_off_nom_rolls
import numpy as np
from Chandra.cmd_states import fetch_states
import Ska.engarchive.fetch_sci as fetch
from Chandra.Time import DateTime, date2secs
from Ska.Matplotlib import plot_cxctime
from astropy.table import Table
from matplotlib import font_manager

fontProperties = font_manager.FontProperties(family="serif", size=18)

class States(object):

    state_keys = ["ccd_count","clocking","ra","dec","dither","fep_count",
                  "hetg","letg","obsid","pcad_mode","pitch","power_cmd",
                  "roll","si_mode","simfa_pos","simpos","q1","q2","q3","q4",
                  "trans_keys","vid_board"]

    def __init__(self, table):
        self.table = table
        self._time_start = self.table["tstart"]
        self._time_stop = self.table["tstop"]
        self._time = 0.5*(self._time_start+self._time_stop)
        self._off_nominal_roll = calc_off_nom_rolls(table)

    @classmethod
    def from_db(cls, tstart, tstop):
        return cls(fetch_states(tstart, tstop, vals=cls.state_keys))

    @classmethod
    def from_file(cls, filename):
        return cls(ascii.read(filename).as_array())

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
        if item in ["datestart","datestop"]:
            return get_time(self.table[item])
        elif item == "off_nominal_roll":
            return self._off_nominal_roll
        else:
            return self.table[item]

    def get_state(self, time):
        """
        Get the state data at a particular time.
        :param time: The time to get the states at. Can be in 
            yday format, an AstroPy Time object, or "now".
        :return: A dictionary of the states.
        """
        time = DateTime(get_time(time)).secs
        # We have this if we need it
        err = "The time %s is not within the selected time frame!" % time
        if time < self._time_start[0]:
            raise RuntimeError(err)
        idx = np.searchsorted(self._time_start, time)
        try:
            self._time_start[idx]
        except IndexError:
            raise RuntimeError(err)
        states = {}
        for key in self.state_keys:
            states[key] = self[key][idx]
        return states

    @property
    def get_current_state(self):
        return self.get_state("now")

    def write_ascii(self, filename):
        Table(self.table).write(filename, format='ascii')

    def plot(self, y, fig=None, ax=None, **kwargs):
        ticklocs, fig, ax = plot_cxctime(self._time, self[y],
                                         fig=fig, ax=ax, **kwargs)
        ax.set_xlabel(r"$\mathrm{Date}$", fontsize=18)
        for label in ax.get_xticklabels():
            label.set_fontproperties(fontProperties)
        for label in ax.get_yticklabels():
            label.set_fontproperties(fontProperties)

class Temperatures(object):
    """
    Get the temperatures for a particular component and load.
    :param table: The file which contains the temperature model table.
    :return: The TemperatureModel instance. 
    """
    def __init__(self, time, temp, id):
        self.time = time
        self.temp = temp
        self.id = id
        self.Tfunc = InterpolatedUnivariateSpline(self.time, self.temp)

    @classmethod
    def from_db(cls, tstart, tstop, msid, filter_bad=False):
        data = fetch.MSID(msid, tstart, tstop, filter_bad=filter_bad)
        return cls(DateTime(data.times).secs, data.vals, msid)

    @classmethod
    def from_file(cls, filename):
        table = ascii.read(filename)
        return cls(table["time"].data, table.columns[-1].data, table.colnames[-1])

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
    def from_model(cls, model, comp):
        return cls(model.times, model.comp[comp].mvals, comp)

    def get_temperature(self, time):
        """
        Get the temperature of the component at a particular time.
        :param time: The time to get the temperature at. Can be in 
            yday format, an AstroPy Time object, or "now".
        :return: The temperature of the component as an AstroPy Quantity. 
        """
        t = date2secs(get_time(time).yday)
        return self.Tfunc(t)*u.deg_C

    def write_ascii(self, filename):
        Table(self.table).write(filename, format='ascii')

    def plot(self, fig=None, ax=None, **kwargs):
        ticklocs, fig, ax = plot_cxctime(self.time, self.temp, 
                                         fig=fig, ax=ax, **kwargs)
        ax.set_xlabel(r"$\mathrm{Date}$", fontsize=18)
        ax.set_ylabel(r"$\mathrm{Temperature\ ({^\circ}C)}$", fontsize=18)
        for label in ax.get_xticklabels():
            label.set_fontproperties(fontProperties)
        for label in ax.get_yticklabels():
            label.set_fontproperties(fontProperties)

