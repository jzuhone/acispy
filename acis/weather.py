import astropy.units as u
from acis.utils import get_time
import numpy as np
from dateutil.relativedelta import relativedelta
from six.moves.urllib import request
from astropy.time import Time, TimeDelta
from astropy.io import ascii
from astropy.table import vstack
from scipy.interpolate import InterpolatedUnivariateSpline

base_urls = {"1m":"ftp://ftp.swpc.noaa.gov/pub/lists/ace/%s_ace_%s_1m.txt",
             "5m":"ftp://ftp.swpc.noaa.gov/pub/lists/ace/%s_ace_%s_5m.txt",
             "1h":"ftp://ftp.swpc.noaa.gov/pub/lists/ace2/%s_ace_%s_1h.txt"}

cols = {}
cols["epam"] = ["year","month","day","time","mjd","jds","status_e","e_38-53_keV",
                "e_175-315_keV","status_p","p_47-68_keV","p_115-195_keV",
                "p_310-580_keV","p_795-1193_keV","p_1060-1900_keV","index"]
cols["mag"] = ["year","month","day","time","mjd","jds",
               "status","Bx","By","Bz","Bt","lat","lon"]
cols["swepam"] = ["year","month","day","time","mjd","jds",
                  "status","density","speed","temperature"]
excludes = {}
excludes["swepam"] = ["year","month","day","time"]
excludes["mag"] = ["year","month","day","time"]
excludes["epam"] = ["year","month","day","time","index"]

class ACE(object):
    units = {}
    def __init__(self, dtype, start_time, end_time, cadence):
        self.start_time = get_time(start_time)
        self.end_time = get_time(end_time)
        self.dtype = dtype
        tables = []
        if cadence == "1h":
            dt = relativedelta(months=1)
        else:
            dt = relativedelta(days=1)
        time = self.start_time.to_datetime()
        end_time = self.end_time.to_datetime()
        while time <= end_time:
            tables.append(self._get_table(cadence, time))
            time += dt
        self.data = vstack(tables)
        self._time = (Time(self.data["mjd"].data, format="mjd") + 
                      TimeDelta(self.data["jds"].data, format='sec')).yday
        self.mask = self._time >= self.start_time
        self.mask = np.logical_and(self.mask, self._time <= self.end_time)

    def _get_table(self, cadence, time):
        datestr = "%s%02d" % (time.year, time.month)
        if cadence != "1h":
            datestr += "%02d" % time.day
        base_url = base_urls[cadence]
        url = base_url % (datestr, self.dtype)
        u = request.urlopen(url).read().decode("utf8").split("\n")[2:]
        mycols = cols[self.dtype]
        myexcludes = excludes[self.dtype]
        table = ascii.read(u, format='fast_no_header', data_start=0, comment="#",
                           guess=False, names=mycols, exclude_names=myexcludes)
        return table

    def _setup_interp(self):
        self.interp = {}
        for k in self.units.keys():
            self.interp[k] = InterpolatedUnivariateSpline(self.time.decimalyear,
                                                          self[k].value)

    @property
    def time(self):
        return Time(self._time[self.mask])

    def __getitem__(self, item):
        return self.data[item][self.mask]*self.units[item]

    def get_data(self, time):
        time = get_time(time).decimalyear
        return dict((k,float(self.interp[k](time))*self.units[k]) 
                    for k in self.units.keys())

class ACEParticles(ACE):
    def __init__(self, start_time, end_time, cadence="1m"):
        super(ACEParticles, self).__init__("epam", start_time, end_time, cadence=cadence)
        self.mask = np.logical_and(self.mask, self.data["status_p"] == 0)
        self.mask = np.logical_and(self.mask, self.data["status_e"] == 0)
        flux_units = 1./(u.cm**2*u.s*u.steradian*u.MeV)
        self.units = dict((k,flux_units) for k in cols["epam"] if k.endswith("keV"))
        self._setup_interp()

class ACESolarWind(ACE):
    units = {"density":u.cm**-3, "speed":u.km/u.s, "temperature":u.K}
    def __init__(self, start_time, end_time, cadence="1m"):
        super(ACESolarWind, self).__init__("swepam", start_time, end_time, cadence=cadence)
        self.mask = np.logical_and(self.mask, self.data["status"] == 0)
        self._setup_interp()

class ACEMagneticField(ACE):
    units = {"Bx":u.nT, "By":u.nT, "Bz":u.nT, "Bt":u.nT, "lat":u.deg, "lon":u.deg}
    def __init__(self, start_time, end_time, cadence="1m"):
        super(ACEMagneticField, self).__init__("mag", start_time, end_time, cadence=cadence)
        self.mask = np.logical_and(self.mask, self.data["status"] == 0)
        self._setup_interp()