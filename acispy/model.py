import requests
from astropy.io import ascii
import Ska.Numpy
from acispy.utils import get_time
from acispy.units import MSIDQuantity
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
    def from_xija(cls, model, components, interp_times=None, masks={}):
        table = {}
        times = {}
        for k in components:
            if k == "dpa_power":
                mvals = model.comp[k].mvals*100. / model.comp[k].mult
                mvals += model.comp[k].bias
            else:
                mvals = model.comp[k].mvals
            unit = msid_units.get(k, None)
            mask = masks.get(k, None)
            if interp_times is None:
                t = model.times
                v = mvals
            else:
                t = interp_times
                v = Ska.Numpy.interpolate(mvals, model.times, interp_times)
            times[k] = MSIDQuantity(t, 's', mask=mask)
            table[k] = MSIDQuantity(v, unit, mask=mask)
        return cls(table, times)

    @classmethod
    def from_load_page(cls, load, components):
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
            data[comp] = MSIDQuantity(table[table_key].data, msid_units[comp])
            times[comp] = MSIDQuantity(table["time"], 's')
        return cls(data, times)

    @classmethod
    def from_load_file(cls, temps_file):
        data = {}
        times = {}
        table = ascii.read(temps_file)
        comp = list(table.keys())[-1]
        key = "fptemp_11" if comp == "fptemp" else comp
        data[key] = MSIDQuantity(table[comp].data, msid_units[key])
        times[key] = MSIDQuantity(table["time"], 's')
        return cls(data, times)

    def get_values(self, time):
        time = get_time(time).secs
        values = {}
        for key in self.keys():
            v = Ska.Numpy.interpolate(self[key], self.times[key].value,
                                      [time], method='linear')
            unit = msid_units.get(key, None)
            values[key] = MSIDQuantity(v, unit=unit)
        return values

    def keys(self):
        return self.table.keys()

    @classmethod
    def join_models(cls, model_list):
        table = {}
        times = {}
        for model in model_list:
            table.update(model.table)
            times.update(model.times)
        return cls(table, times)
