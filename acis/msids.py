from utils import get_time
import Ska.engarchive.fetch_sci as fetch
from astropy.io import ascii
from astropy.table import Table
import numpy as np

class MSIDs(object):
    def __init__(self, time, table, keys):
        self.time = time
        self.table = table
        self._keys = list(keys)

    @classmethod
    def from_tracelog(cls, filename):
        f = open(filename, "r")
        header = f.readline().split()
        dtype = [(msid.lower(), '<f8') for msid in header]
        data = []
        for line in f:
            words = line.split()
            if len(words) == len(header):
                data.append(tuple(map(float, words)))
        f.close()
        data = np.array(data, dtype=dtype)
        # Convert times in the TIME column to Chandra 1998 time
        data['time'] -= 410227200.
        return cls(data["time"], data, header)

    @classmethod
    def from_archive(cls, msids, tstart, tstop=None, filter_bad=False,
                     stat=None):
        data = fetch.MSIDset(msids, tstart, stop=tstop, filter_bad=filter_bad,
                             stat=None)
        table = dict((k, data[k].vals) for k in data.keys())
        return cls(get_time(data[msids[0]].times).secs, table, data.keys())

    def __getitem__(self, item):
        return self.table[item]

    def keys(self):
        return self._keys

    def write_ascii(self, filename):
        Table(self.table).write(filename, format='ascii')
