import requests
from astropy.io import ascii
from astropy.table import Table
import Ska.Numpy
from acispy.utils import get_time

comp_map = {"1deamzt": "dea",
            "1dpamzt": "dpa",
            "1pdeaat": "psmc",
            "fptemp": "fp"}

class Model(object):
    def __init__(self, times, table, keys):
        self.times = times
        self.table = table
        self._keys = list(keys)

    @classmethod
    def from_xija(cls, model, components):
        table = dict((k,  model.comp[k].mvals) for k in components)
        return cls(model.times, table, components)

    @classmethod
    def from_load(cls, load, components):
        """
        Get the temperature model for a particular component and load from the web.
        :param component: The component to get the temperature for, e.g. "FP" for focal plane.
        :param load: The identifier for the load, e.g. "JAN1116A"
        :return: The TemperatureModel instance. 
        """
        if not isinstance(components, list):
            components = [components]
        data = {}
        for comp in components:
            c = comp_map[comp].upper()
            url = "http://cxc.cfa.harvard.edu/acis/%s_thermPredic/" % c
            url += "%s/ofls%s/temperatures.dat" % (load[:-1].upper(), load[-1].lower())
            u = requests.get(url)
            table = ascii.read(u.text)
            data[comp] = table[comp].data
        return cls(table["time"].data, data, data.keys())

    def __getitem__(self, item):
        return self.table[item]

    def keys(self):
        return self._keys

    def get_values(self, time):
        time = get_time(time).secs
        values = {}
        for key in self.keys():
            values[key] = Ska.Numpy.interpolate(self[key], self.times, [time])
        return values

    def write_ascii(self, filename):
        Table(self.table).write(filename, format='ascii')


