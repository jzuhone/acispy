import numpy as np
from acispy.utils import moving_average

derived_fields = {}

class DerivedField(object):
    def __init__(self, type, name, function, deps):
        self.type = type
        self.name = name
        self.function = function
        self.deps = deps
        derived_fields[self.type, self.name] = self

    def __call__(self, dc):
        return self.function(dc)

    def get_deps(self):
        return self.deps

def add_averaged_field(type, name, n=5):
    def _avg(dc):
        return moving_average(dc[type, name], n=n)*dc[type, name].unit
    DerivedField(type, "avg_%s" % name, _avg, [(type, name)])
    if type == "msids":
        def _avg_times(dc):
            return dc[type, "%s_times" % name][(n-1)/2:(-n+1)/2]
        DerivedField(type, "avg_%s_times" % name, _avg_times, [(type, name)])

def create_derived_fields():

    # Telemetry format 
    def _tel_fmt(dc):
        fmt_str = dc['msids','ccsdstmf']
        return np.char.strip(fmt_str, 'FMT').astype("int")

    def _tel_fmt_times(dc):
        return dc['msids','ccsdstmf_times']

    DerivedField("msids", "fmt", _tel_fmt, [("msids", "ccsdstmf")])
    DerivedField("msids", "fmt_times", _tel_fmt_times, [("msids", "ccsdstmf")])

    # DPA, DEA powers

    def _dpaa_power(dc):
        return (dc["msids", "1dp28avo"]*dc["msids", "1dpicacu"]).to("W")

    def _dpaa_power_times(dc):
        return dc["msids", "1dp28avo_times"]

    DerivedField("msids", "dpa_a_power", _dpaa_power, [("msids", "1dp28avo"), ("msids", "1dpicacu")])
    DerivedField("msids", "dpa_a_power_times", _dpaa_power_times, [("msids","1dp28avo")])

    def _dpab_power(dc):
        return (dc["msids", "1dp28bvo"]*dc["msids", "1dpicbcu"]).to("W")

    def _dpab_power_times(dc):
        return dc["msids", "1dp28bvo_times"]

    DerivedField("msids", "dpa_b_power", _dpab_power, [("msids", "1dp28bvo"), ("msids", "1dpicbcu")])
    DerivedField("msids", "dpa_b_power_times", _dpab_power_times, [("msids","1dp28bvo")])

    def _deaa_power(dc):
        return (dc["msids", "1de28avo"]*dc["msids", "1deicacu"]).to("W")

    def _deaa_power_times(dc):
        return dc["msids", "1de28avo_times"]

    DerivedField("msids", "dea_a_power", _deaa_power, [("msids", "1de28avo"), ("msids", "1deicacu")])
    DerivedField("msids", "dea_a_power_times", _deaa_power_times, [("msids","1de28avo")])

    def _deab_power(dc):
        return (dc["msids", "1de28bvo"]*dc["msids", "1deicbcu"]).to("W")

    def _deab_power_times(dc):
        return dc["msids", "1de28bvo_times"]

    DerivedField("msids", "dea_b_power", _deab_power, [("msids", "1de28bvo"), ("msids", "1deicbcu")])
    DerivedField("msids", "dea_b_power_times", _deab_power_times, [("msids","1de28bvo")])
