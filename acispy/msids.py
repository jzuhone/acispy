from acispy.utils import get_time, mit_trans_table
import Ska.engarchive.fetch_sci as fetch
from astropy.table import Table
from astropy.io import ascii
import numpy as np

class MSIDs(object):
    def __init__(self, times, table):
        self.table = table
        for k, v in times.items():
            self.table[k+"_times"] = times[k]

    @classmethod
    def from_mit_file(cls, filename):
        data = ascii.read(filename)
        mins, hours = np.modf(data["SEC"].data/3600.)
        secs, mins = np.modf(mins*60.)
        secs *= 60.0
        time_arr = ["%04d:%03d:%02d:%02d:%06.3f" % (y, d, h, m, s)
                    for y, d, h, m, s in zip(data["YEAR"].data,
                                             data["DOY"].data,
                                             hours, mins, secs)]
        table = {}
        times = {}
        for k in data.keys():
            if k not in ["YEAR", "DOY", "SEC"]:
                if k in mit_trans_table:
                    key = mit_trans_table[k]
                else:
                    key = k.lower()
                table[key] = data[k].data
                times[key] = get_time(time_arr).secs
        return cls(times, table)

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
        table = dict((k, data[k]) for k in data.dtype.names)
        times = dict((k.lower(), data["time"]) for k in header if k != "TIME")
        return cls(times, table)

    @classmethod
    def from_database(cls, msids, tstart, tstop=None, filter_bad=False,
                      stat=None):
        data = fetch.MSIDset(msids, tstart, stop=tstop, filter_bad=filter_bad,
                             stat=None)
        table = dict((k, data[k].vals) for k in data.keys())
        times = dict((k, get_time(data[k].times).secs) for k in data.keys())
        return cls(times, table)

    def __getitem__(self, item):
        return self.table[item]

    def keys(self):
        return list(self.table.keys())

    def write_ascii(self, filename):
        Table(self.table).write(filename, format='ascii')
