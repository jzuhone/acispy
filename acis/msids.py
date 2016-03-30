from utils import get_time
import Ska.engarchive.fetch_sci as fetch
from astropy.io import ascii
from astropy.table import Table

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

    def __getitem__(self, item):
        return self.table[item]

    def keys(self):
        return self._keys

    def write_ascii(self, filename):
        Table(self.table).write(filename, format='ascii')
