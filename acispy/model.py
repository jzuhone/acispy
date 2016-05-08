import requests
from astropy.io import ascii
import Ska.Numpy
from acispy.utils import get_time
from astropy.units import Quantity
from acispy.utils import msid_units
from acispy.time_series import TimeSeriesData

comp_map = {"1deamzt": "dea",
            "1dpamzt": "dpa",
            "1pdeaat": "psmc",
            "fptemp_11": "fp"}

class Model(TimeSeriesData):
    def __init__(self, table, times):
        self.table = table
        self.times = times

    @classmethod
    def from_xija(cls, model, components):
        table = dict((k, Quantity(model.comp[k].mvals, msid_units[k])) for k in components)
        times = dict((k, Quantity(model.times, 's')) for k in components)
        return cls(table, times)

    @classmethod
    def from_load(cls, load, components):
        if not isinstance(components, list):
            components = [components]
        data = {}
        times = {}
        for comp in components:
            c = comp_map[comp].upper()
            table_key = "fptemp" if comp == "fptemp_11" else comp
            url = "http://cxc.cfa.harvard.edu/acis/%s_thermPredic/" % c
            url += "%s/ofls%s/temperatures.dat" % (load[:-1].upper(), load[-1].lower())
            u = requests.get(url)
            table = ascii.read(u.text)
            data[comp] = Quantity(table[table_key].data, msid_units[comp])
            times[comp] = Quantity(table["time"], 's')
        return cls(data, times)

    def get_values(self, time):
        time = get_time(time).secs
        values = {}
        for key in self.keys():
            values[key] = Quantity(Ska.Numpy.interpolate(self[key], 
                                                         self.times[key].value, [time],
                                                         method='linear'), msid_units[key])
        return values


