import numpy as np
from astropy.units import Quantity

class OutputFieldFunction(object):
    def __init__(self, ftype, fname):
        self.ftype = ftype
        self.fname = fname

    def __call__(self, dc):
        obj = getattr(dc, self.ftype)
        return obj[self.fname]

class OutputTimeFunction(object):
    def __init__(self, ftype, fname):
        self.ftype = ftype
        self.fname = fname

    def __call__(self, dc):
        obj = getattr(dc, self.ftype)
        return obj.times[self.fname]

def dummy_time_function(times):
    def _tfunc(dc):
        return Quantity(times, 's')
    return _tfunc

class DerivedField(object):
    def __init__(self, ftype, fname, function, units, time_func, display_name=None):
        self.ftype = ftype
        self.fname = fname
        self.function = function
        self.units = units
        self.time_func = time_func
        if display_name is None:
            self.display_name = fname.upper()
        else:
            self.display_name = display_name

    def __call__(self, dc):
        return self.function(dc)

class FieldContainer(object):
    def __init__(self):
        self.output_fields = {}
        self.derived_fields = {}

    def __getitem__(self, item):
        if item in self.derived_fields:
            return self.derived_fields[item]
        elif item in self.output_fields:
            return self.output_fields[item]
        else:
            raise KeyError(item)

    def __contains__(self, item):
        return item in self.output_fields or item in self.derived_fields

def create_derived_fields(dcont):

    # Telemetry format 
    def _tel_fmt(dc):
        fmt_str = dc['msids','ccsdstmf']
        return np.char.strip(fmt_str, 'FMT').astype("int")

    dcont.add_derived_field("msids", "fmt", _tel_fmt, "",
                            ('msids','ccsdstmf'))

    # DPA, DEA powers

    def _dpaa_power(dc):
        return (dc["msids", "1dp28avo"]*dc["msids", "1dpicacu"]).to("W")

    dcont.add_derived_field("msids", "dpa_a_power", _dpaa_power, 
                            "W", ("msids", "1dp28avo"), 
                            display_name="DPA-A Power")

    def _dpab_power(dc):
        return (dc["msids", "1dp28bvo"]*dc["msids", "1dpicbcu"]).to("W")

    dcont.add_derived_field("msids", "dpa_b_power", _dpab_power, 
                            "W", ("msids", "1dp28bvo"), 
                            display_name="DPA-B Power")

    def _deaa_power(dc):
        return (dc["msids", "1de28avo"]*dc["msids", "1deicacu"]).to("W")

    dcont.add_derived_field("msids", "dea_a_power", _deaa_power, 
                            "W", ("msids", "1de28avo"),
                            display_name="DEA-A Power")

    def _deab_power(dc):
        return (dc["msids", "1de28bvo"]*dc["msids", "1deicbcu"]).to("W")

    dcont.add_derived_field("msids", "dea_b_power", _deab_power, 
                            "W", ("msids", "1de28bvo"),
                            display_name="DEA-B Power")
