import requests
from astropy.io import ascii
import Ska.Numpy
from acispy.utils import get_time, mylog
from acispy.units import APQuantity, Quantity, get_units
from acispy.utils import ensure_list
from acispy.time_series import TimeSeriesData
import numpy as np

comp_map = {"1deamzt": "dea",
            "1dpamzt": "dpa",
            "1pdeaat": "psmc",
            "fptemp_11": "fp",
            "tmp_bep_pcb": "bep_pcb",
            "tmp_fep1_mong": "fep1_mong",
            "tmp_fep1_actel": "fep1_actel"}

class Model(TimeSeriesData):

    @classmethod
    def from_xija(cls, model, components, interp_times=None, masks=None):
        if masks is None:
            masks = {}
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
            unit = get_units("model", k)
            mask = masks.get(k, None)
            if interp_times is None:
                v = mvals
            else:
                v = Ska.Numpy.interpolate(mvals, model.times, interp_times)
            times = Quantity(t, "s")
            table[k] = APQuantity(v, times, unit, dtype=v.dtype, mask=mask)
        return cls(table)

    @classmethod
    def from_load_page(cls, load, components, time_range=None):
        components = ensure_list(components)
        data = {}
        for comp in components:
            c = comp_map[comp].upper()
            table_key = "fptemp" if comp == "fptemp_11" else comp
            url = "http://cxc.cfa.harvard.edu/acis/%s_thermPredic/" % c
            url += "%s/ofls%s/temperatures.dat" % (load[:-1].upper(), load[-1].lower())
            u = requests.get(url)
            if not u.ok:
                mylog.warning("Could not find the model page for '%s'. Skipping." % comp)
                continue
            table = ascii.read(u.text)
            if time_range is None:
                idxs = np.ones(table["time"].size, dtype='bool')
            else:
                idxs = np.logical_and(table["time"] >= time_range[0],
                                      table["time"] <= time_range[1])
            times = Quantity(table["time"][idxs], 's')
            data[comp] = APQuantity(table[table_key].data[idxs], times,
                                    get_units("model", comp), 
                                    dtype=table[table_key].data.dtype)
        return cls(data)

    @classmethod
    def from_load_file(cls, temps_file):
        data = {}
        table = ascii.read(temps_file)
        comp = list(table.keys())[-1]
        key = "fptemp_11" if comp == "fptemp" else comp
        times = Quantity(table["time"], 's')
        data[key] = APQuantity(table[comp].data, times, 
                               get_units("model", key), 
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
            unit = get_units("model", key)
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
