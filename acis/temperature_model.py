from astropy.io import ascii
import astropy.units as u
from scipy.interpolate import InterpolatedUnivariateSpline
import requests
from acis.utils import get_time

class TemperatureModel(object):
    def __init__(self, table, component, date, rev):
        self.table = ascii.read(table)
        self.id = (date+rev).upper()
        self.component = component
        self.time_years = get_time(self.table["date"].data).decimalyear
        self.temp = self.table[self.component.lower()+"temp"].data
        self.Tfunc = InterpolatedUnivariateSpline(self.time_years, self.temp)

    @classmethod
    def from_webpage(cls, component, date, rev):
        url = "http://cxc.cfa.harvard.edu/acis/%s_thermPredic/" % component.upper()
        url += "%s/ofls%s/temperatures.dat" % (date.upper(), rev.lower())
        u = requests.get(url)
        return cls(u.text, component, date, rev)

    def __getitem__(self, item):
        if item == "date":
            return get_time(self.table["date"].data)
        elif item == "temp":
            return self.temp
        else:
            return self.table[item].data

    def get_temp_at_time(self, time):
        t = get_time(time).decimalyear
        return self.Tfunc(t)*u.deg_C