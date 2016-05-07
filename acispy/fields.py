import numpy as np
import Ska.Numpy
from acispy.utils import moving_average, \
    get_display_name, unit_table
from astropy.units import Quantity

derived_fields = {}

def make_time_func(dep):
    def _time_func(dc):
        return dc.times(*dep)
    return _time_func

class DerivedField(object):
    def __init__(self, type, name, function, deps, units, time_func=None,
                 display_name=None):
        self.type = type
        self.name = name
        self.function = function
        self.deps = deps
        self.units = units
        if time_func is None and len(deps) > 0:
            self.time_func = make_time_func(deps[0])
        else:
            self.time_func = time_func
        if display_name is None:
            self.display_name = name.upper()
        else:
            self.display_name = display_name

    def __call__(self, dc):
        return self.function(dc)

    def get_deps(self):
        return self.deps

def add_derived_field(type, name, function, deps, units, time_func=None,
                      display_name=None):
    df = DerivedField(type, name, function, deps, units, time_func=time_func,
                      display_name=display_name)
    derived_fields[type, name] = df

def add_averaged_field(type, name, n=5):
    def _avg(dc):
        return moving_average(dc[type, name], n=n)
    def _avg_times(dc):
        return dc.times(type, name)[(n-1)/2:(-n+1)/2]
    display_name = "Average %s" % get_display_name(type, name)
    units = unit_table[type].get(name, '')
    add_derived_field(type, "avg_%s" % name, _avg, [(type, name)], units,
                      time_func=_avg_times, display_name=display_name)

def add_interpolated_field(type, name, times):
    times_out = np.array(times)
    units = unit_table[type].get(name, '')
    def _interp(dc):
        times_in = dc.times(type, name).value
        return Quantity(Ska.Numpy.interpolate(dc[type, name], 
                                              times_in, times_out,
                                              method='linear'), units)
    def _interp_times(dc):
        return Quantity(times_out, 's')
    add_derived_field(type, "interp_%s" % name, _interp, [(type, name)],
                      units, time_func=_interp_times,
                      display_name=get_display_name(type, name))

def create_derived_fields():

    # Telemetry format 
    def _tel_fmt(dc):
        fmt_str = dc['msids','ccsdstmf']
        return np.char.strip(fmt_str, 'FMT').astype("int")

    add_derived_field("msids", "fmt", _tel_fmt, [("msids", "ccsdstmf")],
                      "")

    # DPA, DEA powers

    def _dpaa_power(dc):
        return (dc["msids", "1dp28avo"]*dc["msids", "1dpicacu"]).to("W")

    add_derived_field("msids", "dpa_a_power", _dpaa_power, 
                      [("msids", "1dp28avo"), ("msids", "1dpicacu")],
                      "W", display_name="DPA-A Power")

    def _dpab_power(dc):
        return (dc["msids", "1dp28bvo"]*dc["msids", "1dpicbcu"]).to("W")

    add_derived_field("msids", "dpa_b_power", _dpab_power, 
                      [("msids", "1dp28bvo"), ("msids", "1dpicbcu")],
                      "W", display_name="DPA-B Power")

    def _deaa_power(dc):
        return (dc["msids", "1de28avo"]*dc["msids", "1deicacu"]).to("W")

    add_derived_field("msids", "dea_a_power", _deaa_power, 
                      [("msids", "1de28avo"), ("msids", "1deicacu")],
                      "W", display_name="DEA-A Power")

    def _deab_power(dc):
        return (dc["msids", "1de28bvo"]*dc["msids", "1deicbcu"]).to("W")

    add_derived_field("msids", "dea_b_power", _deab_power, 
                      [("msids", "1de28bvo"), ("msids", "1deicbcu")],
                      "W", display_name="DEA-B Power")
