from acispy.utils import mit_trans_table, ensure_list, \
    get_state_codes
from acispy.units import get_units, APQuantity, APStringArray, \
    Quantity
import Ska.engarchive.fetch_sci as fetch
from astropy.io import ascii
import numpy as np
from acispy.time_series import TimeSeriesData
import Ska.Numpy
from acispy.fields import builtin_deps
from astropy.table import Table
from cxotime import CxoTime


def check_depends(msids):
    output_msids = []
    derived_msids = []
    for msid in msids:
        if ("msids", msid) in builtin_deps:
            output_msids += [field[1] for field in builtin_deps["msids", msid]]
            derived_msids.append(msid)
        else:
            output_msids.append(msid)
    return output_msids, derived_msids


class MSIDs(TimeSeriesData):
    def __init__(self, table, times, state_codes=None, masks=None,
                 derived_msids=None):
        super(MSIDs, self).__init__()
        if state_codes is None:
            state_codes = {}
        if masks is None:
            masks = {}
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
        if derived_msids is None:
            derived_msids = []
        self.derived_msids = derived_msids

    @classmethod
    def from_hdf5(cls, g):
        table = {}
        times = {}
        masks = {}
        for k in g:
            table[k] = g[k][()]
            times[k] = g[k].attrs["times"]
            if "mask" in g[k].attrs:
                masks[k] = g[k].attrs["mask"]
        state_codes = g.attrs.get("state_codes", None)
        derived_msids = g.attrs.get("derived_msids", None)
        return cls(table, times, masks=masks, state_codes=state_codes,
                   derived_msids=derived_msids)

    @classmethod
    def from_mit_file(cls, filename, tbegin=None, tend=None):
        if tbegin is None:
            tbegin = -1.0e22
        else:
            if isinstance(tbegin, str):
                tbegin = CxoTime(tbegin).secs
        if tend is None:
            tend = 1.0e22
        else:
            if isinstance(tend, str):
                tend = CxoTime(tend).secs
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
        data = Table(ascii.read(filename, guess=False, format='csv',
                                delimiter=delimiter), masked=True)
        mins, hours = np.modf(data["SEC"].data/3600.)
        secs, mins = np.modf(mins*60.)
        secs *= 60.0
        time_arr = ["%04d:%03d:%02d:%02d:%06.3f" % (y, d, h, m, s)
                    for y, d, h, m, s in zip(data[year].data,
                                             data["DOY"].data,
                                             hours, mins, secs)]
        tsecs = CxoTime(time_arr).secs
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
                table[key] = np.array(data[k].data[idxs])
                times[key] = tsecs[idxs]
                if key == "bilevels":
                    masks[key] = np.array(table[key] != "0")
                else:
                    masks[key] = ~data[k].data[idxs].mask
                state_codes[key] = get_state_codes(key)
        # Now we split the bilevel into its components
        bmask = masks["bilevels"]
        bilevels = np.char.strip(table["bilevels"], "b")[bmask]
        for i in range(8):
            key = f"1stat{7-i}dst"
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
            if isinstance(tbegin, str):
                tbegin = CxoTime(tbegin).secs
        if tend is None:
            tend = 1.0e22
        else:
            if isinstance(tend, str):
                tend = CxoTime(tend).secs
        f = open(filename, "r")
        header = f.readline().split()
        dtype = []
        state_codes = {}
        for msid in header:
            state_code = get_state_codes(msid.lower())
            if msid.lower() != "time":
                state_codes[msid.lower()] = state_code
            if state_code is not None:
                dtype.append((msid.lower(), "|U4"))
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
        derived_msids = ["dpa_a_power", "dpa_b_power", "dea_a_power", "dea_b_power"]
        return cls(table, times, state_codes=state_codes, derived_msids=derived_msids)

    @classmethod
    def from_database(cls, msids, tstart, tstop=None, filter_bad=False,
                      stat='5min', interpolate=None, interpolate_times=None):
        tstart = CxoTime(tstart).date
        tstop = CxoTime(tstop).date
        msids = ensure_list(msids)
        msids, derived_msids = check_depends(msids)
        msids = [msid.lower() for msid in msids]
        data = fetch.MSIDset(msids, tstart, stop=tstop, filter_bad=filter_bad,
                             stat=stat)
        table = {}
        times = {}
        state_codes = {}
        masks = {}
        if interpolate is not None:
            if interpolate_times is None:
                # Get the nominal tstart / tstop range
                max_fetch_tstart = max(msid.times[0] for msid in data.values())
                min_fetch_tstop = min(msid.times[-1] for msid in data.values())
                dt = 328.0
                start = CxoTime(tstart).secs if tstart else data.tstart
                stop = CxoTime(tstop).secs if tstop else data.tstop
                start = max(start, max_fetch_tstart)
                stop = min(stop, min_fetch_tstop)
                interpolate_times = np.arange((stop - start) // dt + 1) * dt + start
            else:
                interpolate_times = CxoTime(interpolate_times).secs
        for k, msid in data.items():
            if interpolate is not None:
                indexes = Ska.Numpy.interpolate(np.arange(len(msid.times)),
                                                msid.times, interpolate_times,
                                                method=interpolate, sorted=True).astype("int")
                times[k.lower()] = interpolate_times
            else:
                indexes = slice(None, None, None)
                times[k.lower()] = data[k].times
            if msid.state_codes:
                state_codes[k] = dict((k, v) for v, k in msid.state_codes)
            table[k.lower()] = msid.vals[indexes]
            if msid.bads is not None:
                masks[k.lower()] = (~msid.bads)[indexes]
        return cls(table, times, state_codes=state_codes, masks=masks,
                   derived_msids=derived_msids)

    @classmethod
    def from_maude(cls, msids, tstart, tstop=None, user=None, password=None):
        import maude
        tstart = CxoTime(tstart).date
        tstop = CxoTime(tstop).date
        msids = ensure_list(msids)
        msids, derived_msids = check_depends(msids)
        table = {}
        times = {}
        state_codes = {}
        out = maude.get_msids(msids, start=tstart, stop=tstop, user=user,
                              password=password)
        for msid in out["data"]:
            k = msid["msid"].lower()
            table[k] = msid["values"]
            times[k] = msid['times']
            state_codes[k] = get_state_codes(k)
        return cls(table, times, state_codes=state_codes, 
                   derived_msids=derived_msids)


class CombinedMSIDs(TimeSeriesData):
    def __init__(self, msid_list):
        super(CombinedMSIDs, self).__init__()
        self.state_codes = {}
        derived_msids = []
        for msids in msid_list:
            self.table.update(msids.table)
            self.table.update(msids.table)
            self.state_codes.update(msids.state_codes)
            self.state_codes.update(msids.state_codes)
            derived_msids += msids.derived_msids
        self.derived_msids = derived_msids


class ConcatenatedMSIDs(TimeSeriesData):
    def __init__(self, msids1, msids2):
        super(ConcatenatedMSIDs, self).__init__()
        self.state_codes = msids1.state_codes
        for key in msids1.table:
            v1 = msids1.table[key]
            v2 = msids2.table[key]
            v = np.concatenate([v1.value, v2.value])
            t = Quantity(np.concatenate([v1.times.value, v2.times.value]), "s")
            mask = np.concatenate([v1.mask, v2.mask])
            if v1.dtype.char in ['S', 'U']:
                self.table[key] = APStringArray(v, t, mask)
            else:
                self.table[key] = APQuantity(v, t, unit=v1.unit, dtype=v.dtype,
                                             mask=mask)
        self.derived_msids = msids1.derived_msids
