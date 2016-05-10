import numpy as np

def make_time_func(dep):
    def _time_func(dc):
        return dc.times(*dep)
    return _time_func

class DerivedField(object):
    def __init__(self, ftype, fname, function, deps, units, time_func=None,
                 display_name=None):
        self.ftype = ftype
        self.fname = fname
        self.function = function
        self.deps = deps
        self.units = units
        if time_func is None and len(deps) > 0:
            self.time_func = make_time_func(deps[0])
        else:
            self.time_func = time_func
        if display_name is None:
            self.display_name = fname.upper()
        else:
            self.display_name = display_name

    def __call__(self, dc):
        return self.function(dc)

    def get_deps(self):
        return self.deps

class FieldContainer(object):
    def __init__(self):
        self.output_fields = {}
        self.derived_fields = {}

    def __setitem__(self, item, value):
        self.output_fields[item] = value

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

    dcont.add_derived_field("msids", "fmt", _tel_fmt, [("msids", "ccsdstmf")],
                            "")

    # DPA, DEA powers

    def _dpaa_power(dc):
        return (dc["msids", "1dp28avo"]*dc["msids", "1dpicacu"]).to("W")

    dcont.add_derived_field("msids", "dpa_a_power", _dpaa_power, 
                            [("msids", "1dp28avo"), ("msids", "1dpicacu")],
                            "W", display_name="DPA-A Power")

    def _dpab_power(dc):
        return (dc["msids", "1dp28bvo"]*dc["msids", "1dpicbcu"]).to("W")

    dcont.add_derived_field("msids", "dpa_b_power", _dpab_power, 
                            [("msids", "1dp28bvo"), ("msids", "1dpicbcu")],
                            "W", display_name="DPA-B Power")

    def _deaa_power(dc):
        return (dc["msids", "1de28avo"]*dc["msids", "1deicacu"]).to("W")

    dcont.add_derived_field("msids", "dea_a_power", _deaa_power, 
                            [("msids", "1de28avo"), ("msids", "1deicacu")],
                            "W", display_name="DEA-A Power")

    def _deab_power(dc):
        return (dc["msids", "1de28bvo"]*dc["msids", "1deicbcu"]).to("W")

    dcont.add_derived_field("msids", "dea_b_power", _deab_power, 
                            [("msids", "1de28bvo"), ("msids", "1deicbcu")],
                            "W", display_name="DEA-B Power")
