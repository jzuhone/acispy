from acispy.utils import get_time, mit_trans_table, ensure_list
from acispy.units import get_units
import Ska.engarchive.fetch_sci as fetch
from astropy.io import ascii
import numpy as np
from acispy.units import APQuantity, APStringArray, Quantity
from acispy.time_series import TimeSeriesData

class MSIDs(TimeSeriesData):
    def __init__(self, table, times, state_codes={}, masks={}):
        self.table = {}
        for k, v in table.items():
            mask = masks.get(k, None)
            t = Quantity(times[k], "s")
            if v.dtype.char in ['S', 'U']:
                self.table[k] = APStringArray(v, t, mask=mask)
            else:
                unit = get_units("model", k)
                self.table[k] = APQuantity(v, t, unit=unit, dtype=v.dtype, 
                                           mask=mask)
        self.state_codes = state_codes

    @classmethod
    def from_mit_file(cls, filename):
        f = open(filename, 'r')
        line = f.readline()
        f.close()
        if "," in line:
            delimiter = ","
        elif "\t" in line:
            delimiter = "\t"
        else:
            delimiter = " "
        data = ascii.read(filename, guess=False, format='csv',
                          delimiter=delimiter)
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
                times[key] = get_time(time_arr)
        return cls(table, times)

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
        table = dict((k, data[k]) for k in data.dtype.names if k != "time")
        times = dict((k.lower(), data["time"]) for k in header if k != "time")
        return cls(table, times)

    @classmethod
    def from_database(cls, msids, tstart, tstop=None, filter_bad=False,
                      stat='5min', interpolate=False, interpolate_times=None):
        msids = ensure_list(msids)
        data = fetch.MSIDset(msids, tstart, stop=tstop, filter_bad=filter_bad,
                             stat=stat)
        if interpolate:
            data.interpolate(times=interpolate_times)
        table = {}
        state_codes = {}
        masks = {}
        for k, msid in data.items():
            if msid.state_codes:
                state_codes[k] = dict((k, v) for v, k in msid.state_codes)
            table[k] = msid.vals
            if msid.bads is not None:
                masks[k] = ~msid.bads
        times = dict((k, get_time(data[k].times).secs) for k in data.keys())
        return cls(table, times, state_codes=state_codes)

