import numpy as np

derived_fields = {}

class DerivedField(object):
    def __init__(self, type, name, function):
        self.type = type
        self.name = name
        self.function = function
        derived_fields[self.type, self.name] = self

    def __call__(self, dc):
        return self.function(dc)

def create_derived_fields():

    def _tel_fmt(dc):
        fmt_str = dc['msids','ccsdstmf']
        return np.char.strip(fmt_str, 'FMT').astype("int")

    def _tel_fmt_times(dc):
        return dc['msids','ccsdstmf_times']

    DerivedField("msids", "fmt", _tel_fmt)
    DerivedField("msids", "fmt_times", _tel_fmt_times)