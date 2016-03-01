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
import matplotlib.pyplot as plt

fontProperties = font_manager.FontProperties(family="serif", size=18)
state_labels = {"ccd_count": "CCD Count",
                "clocking": "Clocking",
                "ra": "RA (deg)",
                "dec": "Dec (deg)",
                "dither": None,
                "fep_count": "FEP Count",
                "hetg": None,
                "letg": None,
                "obsid": "ObsID",
                "pcad_mode": None, 
                "pitch": "Pitch (deg)",
                "power_cmd": None,
                "roll": "Roll (deg)",
                "si_mode": None,
                "simfa_pos": None,
                "simpos": "SIM-Z (steps)",
                "q1": "q1",
                "q2": "q2",
                "q3": "q3",
                "q4": "q4",
                "trans_keys": None,
                "vid_board": None}

state_keys = list(state_labels.keys())

class States(object):

    def __init__(self, table):
        self.table = table
        self._time_start = self.table["tstart"]
        self._time_stop = self.table["tstop"]
        self._time = 0.5*(self._time_start+self._time_stop)
        self._off_nominal_roll = calc_off_nom_rolls(table)

    @classmethod
    def from_db(cls, tstart, tstop):
        return cls(fetch_states(tstart, tstop, vals=state_keys))

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
        idx = np.searchsorted(self._time_start, time)-1
        try:
            self._time_start[idx]
        except IndexError:
            raise RuntimeError(err)
        states = {}
        for key in state_keys:
            states[key] = self[key][idx]
        states["off_nominal_roll"] = self._off_nominal_roll[idx]
        return states

    @property
    def get_current_state(self):
        return self.get_state("now")

    def write_ascii(self, filename):
        Table(self.table).write(filename, format='ascii')

    def plot(self, y, fig=None, ax=None, lw=2, **kwargs):
        if state_labels[y] is None:
            raise RuntimeError("Cannot plot state %s!" % y)
        cp = CXCPlot(fig, ax, self._time, self[y], lw=lw, **kwargs)
        if y == "off_nominal_roll":
            ylabel = "Off-Nominal Roll (deg)"
        else:
            ylabel = state_labels[y]
        cp.set_ylabel(ylabel)
        return cp

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

    def plot(self, fig=None, ax=None, lw=2, **kwargs):
        cp = CXCPlot(fig, ax, self.time, self.temp, lw=lw, **kwargs)
        cp.set_ylabel(r"$\mathrm{Temperature\ ({^\circ}C)}$")
        return cp

class CXCPlot(object):
    def __init__(self, fig, ax, x, y, lw=2, **kwargs):
        if fig is None:
            fig = plt.figure(figsize=(10,8))
        ticklocs, fig, ax = plot_cxctime(x, y, fig=fig, ax=ax, lw=lw, **kwargs)
        self.ticklocs = ticklocs
        self.fig = fig
        self.ax = ax
        self.ax.set_xlabel(r"$\mathrm{Date}$", fontdict={"size":18, "family":"serif"})
        for label in self.ax.get_xticklabels():
            label.set_fontproperties(fontProperties)
        for label in self.ax.get_yticklabels():
            label.set_fontproperties(fontProperties)

    def set_xlim(self, xmin, xmax):
        self.ax.set_xlim(get_time(xmin).to_datetime(),
                         get_time(xmax).to_datetime())

    def set_ylim(self, ymin, ymax):
        self.ax.set_ylim(ymin, ymax)

    def set_ylabel(self, ylabel, fontdict=None, **kwargs):
        if fontdict is None:
            fontdict = {"size": 18, "family": "serif"}
        self.ax.set_ylabel(ylabel, fontdict=fontdict, **kwargs)

    def savefig(self, filename, **kwargs):
        self.fig.savefig(filename, **kwargs)
