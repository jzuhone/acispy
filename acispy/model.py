import requests
from astropy.io import ascii
import Ska.Numpy
from acispy.utils import get_time
import astropy.units as apu
from acispy.utils import msid_units

comp_map = {"1deamzt": "dea",
            "1dpamzt": "dpa",
            "1pdeaat": "psmc",
            "fptemp_11": "fp"}

class Model(object):
    def __init__(self, table):
        self.table = dict((k, v*getattr(apu, msid_units[k])) for k, v in table.items())

    @classmethod
    def from_xija(cls, model, components):
        table = dict((k,  model.comp[k].mvals) for k in components)
        table["times"] = model.times
        return cls(table)

    @classmethod
    def from_load(cls, load, components):
        if not isinstance(components, list):
            components = [components]
        data = {}
        for comp in components:
            c = comp_map[comp].upper()
            table_key = "fptemp" if comp == "fptemp_11" else comp
            url = "http://cxc.cfa.harvard.edu/acis/%s_thermPredic/" % c
            url += "%s/ofls%s/temperatures.dat" % (load[:-1].upper(), load[-1].lower())
            u = requests.get(url)
            table = ascii.read(u.text)
            data[comp] = table[table_key].data
        data["times"] = table["time"].data
        return cls(data)

    def __getitem__(self, item):
        return self.table[item]

    def keys(self):
        return list(self.table.keys())

    def get_values(self, time):
        time = get_time(time).secs
        values = {}
        for key in self.keys():
            values[key] = Ska.Numpy.interpolate(self[key], self["times"].value, [time])
        return values


