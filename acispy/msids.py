from acispy.utils import get_time, mit_trans_table, ensure_list
from acispy.units import get_units
import Ska.engarchive.fetch_sci as fetch
from astropy.io import ascii
import numpy as np
from acispy.units import APQuantity, APStringArray, Quantity
from acispy.time_series import TimeSeriesData
import six

if six.PY2:
    str_type = "|S4"
else:
    str_type = "|U4"

tl_states = ["1dppsax", "1dppsa", "1dppsbx", "1dppsb",
             "1depsax", "1depsa", "1depsbx", "1depsb"]

class MSIDs(TimeSeriesData):
    def __init__(self, table, times, state_codes=None, masks=None):
        if state_codes is None:
            state_codes = {}
        if masks is None:
            masks = {}
        self.table = {}
        for k, v in table.items():
            mask = masks.get(k, None)
            t = Quantity(times[k], "s")
            if v.dtype.char in ['S', 'U']:
                self.table[k] = APStringArray(v, t, mask=mask)
            else:
                unit = get_units("msids", k)
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
        if line.startswith("#"):
            year = "#YEAR"
        else:
            year = "YEAR"
        data = ascii.read(filename, guess=False, format='csv',
                          delimiter=delimiter)
        mins, hours = np.modf(data["SEC"].data/3600.)
        secs, mins = np.modf(mins*60.)
        secs *= 60.0
        time_arr = ["%04d:%03d:%02d:%02d:%06.3f" % (y, d, h, m, s)
                    for y, d, h, m, s in zip(data[year].data,
                                             data["DOY"].data,
                                             hours, mins, secs)]
        table = {}
        times = {}
        for k in data.keys():
            if k not in [year, "DOY", "SEC"]:
                if k in mit_trans_table:
                    key = mit_trans_table[k]
                else:
                    key = k.lower()
                table[key] = data[k].data
                times[key] = get_time(time_arr).secs
        return cls(table, times)

    @classmethod
    def from_tracelog(cls, filename):
        f = open(filename, "r")
        header = f.readline().split()
        dtype = []
        for msid in header:
            if msid.lower() in tl_states:
                dtype.append((msid.lower(), str_type))
            else:
                dtype.append((msid.lower(), '<f8'))
        data = []
        for line in f:
            words = line.split()
            if len(words) == len(header):
                data.append(tuple(words))
        f.close()
        data = np.array(data, dtype=dtype)
        # Convert times in the TIME column to Chandra 1998 time
        data['time'] -= 410227200.
        table = dict((k.lower(), data[k]) for k in data.dtype.names if k != "time")
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
            table[k.lower()] = msid.vals
            if msid.bads is not None:
                masks[k.lower()] = ~msid.bads
        times = dict((k.lower(), get_time(data[k].times).secs) for k in data.keys())
        return cls(table, times, state_codes=state_codes, masks=masks)

