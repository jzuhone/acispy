import astropy.units as u
from acis.utils import get_time
import numpy as np
from dateutil.relativedelta import relativedelta
from six.moves.urllib import request
from astropy.time import Time, TimeDelta
from astropy.io import ascii
from astropy.table import vstack
from scipy.interpolate import InterpolatedUnivariateSpline

base_url = "ftp://ftp.swpc.noaa.gov/pub/lists/%s/%s_ace_%s_%s.txt"
excludes = ["year","month","day","time","index"]
noindex = ["mjd","jds","status","status_e","status_p"]

class ACE(object):
    units = {}
    cols = []
    realtime_url = ""
    def __init__(self, dtype, times, cadence):
        self.dtype = dtype
        if times == "realtime":
            tables = [self._get_table(self.realtime_url)]
        else:
            start_time = get_time(times[0])
            end_time = get_time(times[1])
            tables = []
            if cadence == "1h":
                dt = relativedelta(months=1)
                which_dir = "ace2"
            else:
                dt = relativedelta(days=1)
                which_dir = "ace"
            time = start_time.to_datetime()
            etime = end_time.to_datetime()
            while time <= etime:
                datestr = "%s%02d" % (time.year, time.month)
                if cadence != "1h":
                    datestr += "%02d" % time.day
                url = base_url % (which_dir, datestr, self.dtype, cadence)
                tables.append(self._get_table(url))
                time += dt
        self.table = vstack(tables)
        self._time = (Time(self.table["mjd"].data, format="mjd") + 
                      TimeDelta(self.table["jds"].data, format='sec')).copy("yday")
        if times == "recent":
            self.mask = True
        else:
            self.mask = self._time >= start_time
            self.mask = np.logical_and(self.mask, self._time <= end_time)
        self.data = {}

    def _get_table(self, url):
        u = request.urlopen(url).read().decode("utf8").split("\n")[2:]
        table = ascii.read(u, format='fast_no_header', data_start=0, comment="#",
                           guess=False, names=self.cols, exclude_names=excludes)
        return table

    def _setup_interp(self):
        self.interp = {}
        for k in self.units.keys():
            self.interp[k] = InterpolatedUnivariateSpline(self["time"].decimalyear,
                                                          self[k].value)

    def __getitem__(self, item):
        if item not in self.data:
            if item == "time":
                self.data[item] = self._time[self.mask]
            elif item in self.table.keys() and item not in noindex:
                self.data[item] = self.table[item][self.mask]*self.units[item]
            else:
                raise KeyError
        return self.data[item]

    def get_data(self, time):
        time = get_time(time).decimalyear
        return dict((k,float(self.interp[k](time))*self.units[k]) 
                    for k in self.units.keys())

class ACEParticles(ACE):
    cols = ["year","month","day","time","mjd","jds","status_e","e_38-53_keV",
            "e_175-315_keV","status_p","p_47-68_keV","p_115-195_keV",
            "p_310-580_keV","p_795-1193_keV","p_1060-1900_keV","index"]
    realtime_url = "http://services.swpc.noaa.gov/text/ace-epam.txt"
    def __init__(self, times, cadence="1m"):
        super(ACEParticles, self).__init__("epam", times, cadence=cadence)
        self.mask = np.logical_and(self.mask, self.table["status_p"] == 0)
        self.mask = np.logical_and(self.mask, self.table["status_e"] == 0)
        flux_units = 1./(u.cm**2*u.s*u.steradian*u.MeV)
        self.units = dict((k,flux_units) for k in self.cols if k.endswith("keV"))
        self._setup_interp()

class ACESolarWind(ACE):
    cols = ["year","month","day","time","mjd","jds",
            "status","density","speed","temperature"]
    units = {"density":u.cm**-3, "speed":u.km/u.s, "temperature":u.K}
    realtime_url = "http://services.swpc.noaa.gov/text/ace-swepam.txt"
    def __init__(self, times, cadence="1m"):
        super(ACESolarWind, self).__init__("swepam", times, cadence=cadence)
        self.mask = np.logical_and(self.mask, self.table["status"] == 0)
        self._setup_interp()

class ACEMagneticField(ACE):
    cols = ["year","month","day","time","mjd","jds",
            "status","Bx","By","Bz","Bt","lat","lon"]
    units = {"Bx":u.nT, "By":u.nT, "Bz":u.nT, "Bt":u.nT, "lat":u.deg, "lon":u.deg}
    realtime_url = "http://services.swpc.noaa.gov/text/ace-magnetometer.txt"
    def __init__(self, times, cadence="1m"):
        super(ACEMagneticField, self).__init__("mag", times, cadence=cadence)
        self.mask = np.logical_and(self.mask, self.table["status"] == 0)
        self._setup_interp()