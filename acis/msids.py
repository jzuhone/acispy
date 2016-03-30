from utils import get_time
import Ska.engarchive.fetch_sci as fetch
from astropy.io import ascii
import requests
from astropy.table import Table
import numpy as np

class MSIDs(object):
    def __init__(self, time, table, keys):
        self.time = time
        self.table = table
        self._keys = list(keys)

    @classmethod
    def from_tracelog(cls, filename):
        data = ascii.read(filename, format='csv', delimiter="\t", guess=False)
        return cls(data["TIME"]-410227200., data.as_array(), data.keys())

    @classmethod
    def from_archive(cls, msids, tstart, tstop=None, filter_bad=False,
                     stat=None):
        data = fetch.MSIDset(msids, tstart, stop=tstop, filter_bad=filter_bad,
                             stat=None)
        table = dict((k, data[k].vals) for k in data.keys())
        return cls(get_time(data[msids[0]].times).secs, table, data.keys())

    @classmethod
    def from_file(cls, filename):
        table = ascii.read(filename)
        return cls(table["time"].data, {table.colnames[-1]: table.columns[-1].data},
                   [table.colnames[-1]])

    @classmethod
    def from_webpage(cls, component, load):
        """
        Get the temperature model for a particular component and load from the web.
        :param component: The component to get the temperature for, e.g. "FP" for focal plane.
        :param load: The identifier for the load, e.g. "JAN1116A"
        :return: The TemperatureModel instance. 
        """
        url = "http://cxc.cfa.harvard.edu/acis/%s_thermPredic/" % component.upper()
        url += "%s/ofls%s/temperatures.dat" % (load[:-1].upper(), load[-1].lower())
        u = requests.get(url)
        return cls.from_file(u.text)

    @classmethod
    def from_model(cls, model, comps):
        table = dict((k,  model.comp[k].mvals) for k in comps)
        return cls(model.times, table)

    def __getitem__(self, item):
        return self.table[item]

    def keys(self):
        return self._keys

    def write_ascii(self, filename):
        Table(self.table).write(filename, format='ascii')
