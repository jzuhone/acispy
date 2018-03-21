from acispy.utils import get_time, mit_trans_table, ensure_list, \
    get_state_codes
from acispy.units import get_units
import Ska.engarchive.fetch_sci as fetch
from astropy.io import ascii
import numpy as np
from acispy.units import APQuantity, APStringArray, Quantity
from acispy.time_series import TimeSeriesData
import six
from Chandra.Time import date2secs, DateTime
import Ska.Numpy

if six.PY2:
    str_type = "|S4"
else:
    str_type = "|U4"

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
    def from_mit_file(cls, filename, tbegin=None, tend=None):
        if tbegin is None:
            tbegin = -1.0e22
        else:
            if isinstance(tbegin, six.string_types):
                tbegin = date2secs(tbegin)
        if tend is None:
            tend = 1.0e22
        else:
            if isinstance(tend, six.string_types):
                tend = date2secs(tend)
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
        tsecs = date2secs(time_arr)
        idxs = np.logical_and(tsecs >= tbegin, tsecs <= tend)
        table = {}
        times = {}
        masks = {}
        state_codes = {}
        for k in data.keys():
            if k not in [year, "DOY", "SEC"]:
                if k in mit_trans_table:
                    key = mit_trans_table[k]
                else:
                    key = k.lower()
                table[key] = data[k].data[idxs]
                times[key] = tsecs[idxs]
                if key == "bilevels":
                    masks[key] = table[key] != "0"
                else:
                    masks[key] = ~np.isnan(table[key]) 
                state_codes[key] = get_state_codes(key)
        # Now we split the bilevel into its components
        bmask = masks["bilevels"]
        bilevels = np.char.strip(table["bilevels"], "b")[bmask]
        for i in range(8):
            key = "1stat%dst" % (7-i)
            table[key] = np.array(["BAD"]*bmask.size)
            table[key][bmask] = np.array([b[i] for b in bilevels])
            times[key] = times["bilevels"]
            masks[key] = bmask
            state_codes[key] = get_state_codes(key)
        return cls(table, times, masks=masks, state_codes=state_codes)

    @classmethod
    def from_tracelog(cls, filename, tbegin=None, tend=None):
        if tbegin is None:
            tbegin = -1.0e22
        else:
            if isinstance(tbegin, six.string_types):
                tbegin = date2secs(tbegin)
        if tend is None:
            tend = 1.0e22
        else:
            if isinstance(tend, six.string_types):
                tend = date2secs(tend)
        f = open(filename, "r")
        header = f.readline().split()
        dtype = []
        state_codes = {}
        for msid in header:
            state_code = get_state_codes(msid.lower())
            if msid.lower() != "time":
                state_codes[msid.lower()] = state_code
            if state_code is None:
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
        idxs = np.logical_and(data['time'] >= tbegin, data['time'] <= tend)
        table = dict((k.lower(), data[k][idxs]) for k in data.dtype.names if k != "time")
        times = dict((k.lower(), data["time"][idxs]) for k in header if k != "time")
        return cls(table, times, state_codes=state_codes)

    @classmethod
    def from_database(cls, msids, tstart, tstop=None, filter_bad=False,
                      stat='5min', interpolate=False, interpolate_times=None):
        msids = ensure_list(msids)
        data = fetch.MSIDset(msids, tstart, stop=tstop, filter_bad=filter_bad,
                             stat=stat)
        table = {}
        times = {}
        state_codes = {}
        masks = {}
        if interpolate and interpolate_times is None:
            # Get the nominal tstart / tstop range
            max_fetch_tstart = max(msid.times[0] for msid in data.values())
            min_fetch_tstop = min(msid.times[-1] for msid in data.values())
            dt = 328.0
            start = DateTime(tstart).secs if tstart else data.tstart
            stop = DateTime(tstop).secs if tstop else data.tstop
            start = max(start, max_fetch_tstart)
            stop = min(stop, min_fetch_tstop)
            interpolate_times = np.arange((stop - start) // dt + 1) * dt + start
        for k, msid in data.items():
            if interpolate:
                indexes = Ska.Numpy.interpolate(np.arange(len(msid.times)),
                                                msid.times, interpolate_times,
                                                method='nearest', sorted=True)
            else:
                indexes = slice(None, None, None)
            if msid.state_codes:
                state_codes[k] = dict((k, v) for v, k in msid.state_codes)
            table[k.lower()] = msid.vals[indexes]
            if msid.bads is not None:
                masks[k.lower()] = (~msid.bads)[indexes]
            times[k.lower()] = get_time(data[k].times[indexes], 'secs')
        return cls(table, times, state_codes=state_codes, masks=masks)


class CombinedMSIDs(TimeSeriesData):
    def __init__(self, msid_list):
        self.table = {}
        self.state_codes = {}
        for msids in msid_list:
            self.table.update(msids.table)
            self.table.update(msids.table)
            self.state_codes.update(msids.state_codes)
            self.state_codes.update(msids.state_codes)
