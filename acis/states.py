from astropy.io import ascii
import astropy.units as u
from scipy.interpolate import InterpolatedUnivariateSpline
import requests
from acis.utils import get_time
import numpy as np

class States(object):

    state_keys = ["ccd_count","clocking","ra","dec","dither","fep_count",
                  "hetg","letg","obsid","pcad_mode","pitch","power_cmd",
                  "roll","si_mode","simfa_pos","simpos","q1","q2","q3","q4"]

    """
    Get the states table for a particular component and load.
    :param table: The file which contains the states table.
    :param component: The component to get the states for, e.g. "FP" for focal plane.
    :param load: The identifier for the load, e.g. "JAN1116A"
    :return: The States instance.
    """
    def __init__(self, table, component, load):
        self.table = ascii.read(table)
        self.id = load.upper()
        self.component = component
        self._time_start = get_time(self.table["datestart"].data).decimalyear
        self._time_stop = get_time(self.table["datestop"].data).decimalyear

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
        return cls(u.text, component, load)

    def __getitem__(self, item):
        if item in ["datestart","datestop"]:
            return get_time(self.table[item].data)
        else:
            return self.table[item].data

    def get_state(self, time):
        """
        Get the state data at a particular time.
        :param time: The time to get the states at. Can be in 
            yday format, an AstroPy Time object, or "now".
        :return: A dictionary of the states.
        """
        time = get_time(time)
        # We have this if we need it
        err = "The time %s is not within the time frame for this load!" % time
        if time.decimalyear < self._time_start[0]:
            raise RuntimeError(err)
        idx = np.searchsorted(self._time_start, time.decimalyear)
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

class TemperatureModel(object):
    """
    Get the temperature model for a particular component and load.
    :param table: The file which contains the temperature model table.
    :param component: The component to get the temperature for, e.g. "FP" for focal plane.
    :param load: The identifier for the load, e.g. "JAN1116A"
    :return: The TemperatureModel instance. 
    """
    def __init__(self, table, component, load):
        self.table = ascii.read(table)
        self.id = load.upper()
        self.component = component
        self.time_years = get_time(self.table["date"].data).decimalyear
        self.temp = self.table[self.component.lower()+"temp"].data
        self.Tfunc = InterpolatedUnivariateSpline(self.time_years, self.temp)

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
        return cls(u.text, component, load)

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
