import requests
from astropy.io import ascii
import Ska.Numpy
from acispy.utils import get_time
from acispy.units import APQuantity, Quantity
from acispy.utils import msid_units, ensure_list
from acispy.time_series import TimeSeriesData

comp_map = {"1deamzt": "dea",
            "1dpamzt": "dpa",
            "1pdeaat": "psmc",
            "fptemp_11": "fp"}

class Model(TimeSeriesData):

    @classmethod
    def from_xija(cls, model, components, interp_times=None, masks={}):
        if interp_times is None:
            t = model.times
        else:
            t = interp_times
        table = {}
        for k in components:
            if k == "dpa_power":
                mvals = model.comp[k].mvals*100. / model.comp[k].mult
                mvals += model.comp[k].bias
            else:
                mvals = model.comp[k].mvals
            unit = msid_units.get(k, None)
            mask = masks.get(k, None)
            if interp_times is None:
                v = mvals
            else:
                v = Ska.Numpy.interpolate(mvals, model.times, interp_times)
            times = Quantity(t, "s")
            table[k] = APQuantity(v, times, unit, dtype=v.dtype, mask=mask)
        return cls(table)

    @classmethod
    def from_load_page(cls, load, components):
        components = ensure_list(components)
        data = {}
        for comp in components:
            c = comp_map[comp].upper()
            table_key = "fptemp" if comp == "fptemp_11" else comp
            url = "http://cxc.cfa.harvard.edu/acis/%s_thermPredic/" % c
            url += "%s/ofls%s/temperatures.dat" % (load[:-1].upper(), load[-1].lower())
            u = requests.get(url)
            table = ascii.read(u.text)
            times = Quantity(table["time"], 's')
            data[comp] = APQuantity(table[table_key].data, times,
                                    msid_units[comp], dtype=table[table_key].data.dtype)
        return cls(data)

    @classmethod
    def from_load_file(cls, temps_file):
        data = {}
        table = ascii.read(temps_file)
        comp = list(table.keys())[-1]
        key = "fptemp_11" if comp == "fptemp" else comp
        times = Quantity(table["time"], 's')
        data[key] = APQuantity(table[comp].data, times, msid_units[key], 
                                 dtype=table[comp].data.dtype)
        return cls(data)

    def get_values(self, time):
        time = get_time(time).secs
        t = Quantity(time, "s")
        values = {}
        for key in self.keys():
            v = Ska.Numpy.interpolate(self[key].value, 
                                      self[key].times.value,
                                      [time], method='linear')[0]
            unit = msid_units.get(key, None)
            values[key] = APQuantity(v, t, unit=unit, dtype=v.dtype)
        return values

    def keys(self):
        return self.table.keys()

    @classmethod
    def join_models(cls, model_list):
        table = {}
        for model in model_list:
            table.update(model.table)
        return cls(table)
