from astropy.io import ascii
import astropy.units as u
from scipy.interpolate import InterpolatedUnivariateSpline
import requests
from acis.utils import get_time
import numpy as np

class ACISStates(object):

    state_keys = ["ccd_count","clocking","ra","dec","dither","fep_count",
                  "hetg","letg","obsid","pcad_mode","pitch","power_cmd",
                  "roll","si_mode","simfa_pos","simpos","q1","q2","q3","q4"]

    def __init__(self, table, component, date, rev):
        self.table = ascii.read(table)
        self.id = (date+rev).upper()
        self.component = component
        self.time_start = get_time(self.table["datestart"].data).decimalyear
        self.time_stop = get_time(self.table["datestop"].data).decimalyear

    @classmethod
    def from_webpage(cls, component, date, rev):
        url = "http://cxc.cfa.harvard.edu/acis/%s_thermPredic/" % component.upper()
        url += "%s/ofls%s/states.dat" % (date.upper(), rev.lower())
        u = requests.get(url)
        return cls(u.text, component, date, rev)

    def __getitem__(self, item):
        if item in ["datestart","datestop"]:
            return get_time(self.table[item].data)
        else:
            return self.table[item].data

    def get_states(self, time):
        """
        Get the state data at a particular time.
        :param time: The time to get the states at. Can be in 
            yday format, an AstroPy Time object, or "now".
        :return: A dictionary of the states.
        """
        time = get_time(time)
        # We have this if we need it
        err = "The time %s is not within the time frame for this load!" % time
        if time.decimalyear < self.time_start[0]:
            raise RuntimeError(err)
        idx = np.searchsorted(self.time_start, time.decimalyear)
        try:
            self.time_start[idx]
        except IndexError:
            raise RuntimeError(err)
        states = {}
        for key in self.state_keys:
            states[key] = self[key][idx]
        return states

    @property
    def get_current_states(self):
        return self.get_states("now")

class TemperatureModel(object):
    def __init__(self, table, component, date, rev):
        self.table = ascii.read(table)
        self.id = (date+rev).upper()
        self.component = component
        self.time_years = get_time(self.table["date"].data).decimalyear
        self.temp = self.table[self.component.lower()+"temp"].data
        self.Tfunc = InterpolatedUnivariateSpline(self.time_years, self.temp)

    @classmethod
    def from_webpage(cls, component, date, rev):
        url = "http://cxc.cfa.harvard.edu/acis/%s_thermPredic/" % component.upper()
        url += "%s/ofls%s/temperatures.dat" % (date.upper(), rev.lower())
        u = requests.get(url)
        return cls(u.text, component, date, rev)

    def __getitem__(self, item):
        if item == "date":
            return get_time(self.table["date"].data)
        elif item == "temp":
            return self.temp
        else:
            return self.table[item].data

    def get_temp_at_time(self, time):
        """
        Get the temperature of the component at a particular time.
        :param time: The time to get the temperature at. Can be in 
            yday format, an AstroPy Time object, or "now".
        :return: The temperature of the component as an AstroPy Quantity. 
        """
        t = get_time(time).decimalyear
        return self.Tfunc(t)*u.deg_C
