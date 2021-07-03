import astropy.units as u
from astropy.units import Quantity
from acispy.utils import mylog
import numpy as np
from Chandra.Time import secs2date, DateTime

u.imperial.enable()

state_units = {'ra': 'deg',
               'dec': 'deg',
               'roll': 'deg',
               'tstart': 's',
               'tstop': 's',
               'pitch': 'deg',
               'off_nom_roll': 'deg'}

msid_units = {'1deamzt': 'deg_C',
              '1dpamzt': 'deg_C',
              '1pdeaat': 'deg_C',
              '1pin1at': 'deg_C',
              '1pdeabt': 'deg_C',
              'fptemp_11': 'deg_C',
              'fptemp_12': 'deg_C',
              '1dp28avo': 'V',
              '1dp28bvo': 'V',
              '1dpicacu': 'A',
              '1dpicbcu': 'A',
              '1dpp0avo': 'V',
              '1dpp0bvo': 'V',
              '1de28avo': 'V',
              '1dep3avo': 'V',
              '1dep2avo': 'V',
              '1dep1avo': 'V',
              '1dep0avo': 'V',
              '1den1avo': 'V',
              '1den0avo': 'V',
              '1deicacu': 'A',
              '1de28bvo': 'V',
              '1dep3bvo': 'V',
              '1dep2bvo': 'V',
              '1dep1bvo': 'V',
              '1dep0bvo': 'V',
              '1den0bvo': 'V',
              '1den1bvo': 'V',
              '1deicbcu': 'A',
              '1crat': 'deg_C',
              '1crbt': 'deg_C',
              '1wrat': 'deg_C',
              '1wrbt': 'deg_C',
              '1dpamyt': 'deg_C',
              '1sspyt': 'deg_C',
              '1ssmyt': 'deg_C',
              '1cbat': 'deg_C',
              '1cbbt': 'deg_C',
              '1dactbt': 'deg_C',
              '2detart': 'ct', 
              '2detbrt': 'ct', 
              '2shldart': 'ct',
              '2shldbrt': 'ct',
              '3tsmydpt': 'deg_C',
              '3tspyfet': 'deg_C',
              '3tspzdet': 'deg_C',
              '3tspzspt': 'deg_C',
              '3tsmxspt': 'deg_C',
              '3tsmxcet': 'deg_C',
              '3rctubpt': 'deg_C',
              '3ttacs1t': 'deg_C',
              '3ttacs2t': 'deg_C',
              '3ttacs3t': 'deg_C',
              '1dahhavo': 'V',
              '1dahhbvo': 'V',
              '1dahavo': 'V',
              '1dahbvo': 'V',
              '1dahacu': 'A',
              '1dahbcu': 'A',
              '1dahat': 'deg_C',
              '1dahbt': 'deg_C',
              '1oahat': 'deg_C',
              '1oahbt': 'deg_C',
              'dp_pitch': 'deg',
              'pitch': 'deg',
              'tmp_bep_pcb': 'deg_C',
              'tmp_bep_osc': 'deg_C',
              'tmp_fep0_mong': 'deg_C',
              'tmp_fep0_pcb': 'deg_C',
              'tmp_fep0_actel': 'deg_C',
              'tmp_fep0_ram': 'deg_C',
              'tmp_fep0_fb': 'deg_C',
              'tmp_fep1_mong': 'deg_C',
              'tmp_fep1_pcb': 'deg_C',
              'tmp_fep1_actel': 'deg_C',
              'tmp_fep1_ram': 'deg_C',
              'tmp_fep1_fb': 'deg_C',
              'dpagndref1':	'V',
              'dpa5vhka': 'V',
              'dpagndref2':	'V',
              'dpa5vhkb': 'V',
              'dea28volta':	'V',
              'dea24volta':	'V',
              'deam15volta': 'V',
              'deap15volta': 'V',
              'deam6volta':	'V',
              'deap6volta': 'V',
              'gnd_1': 'V',
              'dea28voltb':	'V',
              'dea24voltb':	'V',
              'deam15voltb': 'V',
              'deap15voltb': 'V',
              'deam6voltb':	'V',
              'deap6voltb':	'V',
              'gnd_2': 'V',
              'dpa_power': 'W',
              'dp_dpa_power': 'W',
              'Point_EarthCentAng': 'deg',
              'Dist_SatEarth': 'm',
              'roll': 'deg',
              'vcdu': '',
              'fmt': '',
              'obsid': '',
              'cmdid': '',
              'earth_solid_angle': 'sr',
              'orbitephem0_x': 'm',
              'orbitephem0_y': 'm',
              'orbitephem0_z': 'm',
              'solarephem0_x': 'm',
              'solarephem0_y': 'm',
              'solarephem0_z': 'm',
              'orbitephem1_x': 'm',
              'orbitephem1_y': 'm',
              'orbitephem1_z': 'm',
              'solarephem1_x': 'm',
              'solarephem1_y': 'm',
              'solarephem1_z': 'm',
              'orbitephem0_vx': 'm/s',
              'orbitephem0_vy': 'm/s',
              'orbitephem0_vz': 'm/s',
              'solarephem0_vx': 'm/s',
              'solarephem0_vy': 'm/s',
              'solarephem0_vz': 'm/s',
              'orbitephem1_vx': 'm/s',
              'orbitephem1_vy': 'm/s',
              'orbitephem1_vz': 'm/s',
              'solarephem1_vx': 'm/s',
              'solarephem1_vy': 'm/s',
              'solarephem1_vz': 'm/s'
              }


def parse_index(idx, times): 
    if isinstance(idx, (int, np.ndarray)) or idx is None:
        return idx
    else:
        orig_idx = idx
        if isinstance(idx, str):
            idx = DateTime(idx).secs
        if idx < times[0] or idx > times[-1]:
            raise RuntimeError(f"The time {orig_idx} is outside the bounds of this dataset!")
        idx = np.searchsorted(times, idx)-1
    return idx


def find_indices(item, times):
    if getattr(times, "ndim", None) == 2:
        t1 = times[0]
        t2 = times[1]
    else:
        t1 = t2 = times
    if isinstance(item, slice):
        idxs = slice(parse_index(item.start, t1),
                     parse_index(item.stop, t2),
                     item.step)
    elif isinstance(item, tuple):
        idxs = slice(parse_index(item[0].start, t1),
                     parse_index(item[0].stop, t2),
                     item[0].step)
    else:
        idxs = parse_index(item, t1)
    if getattr(times, "ndim", None) == 2:
        t = times[:,idxs]
    else:
        t = times[idxs]
    return idxs, Quantity(t, "s")


class APStringArray(object):
    def __init__(self, value, times, mask=None):
        self.value = value
        self.times = times
        if mask is None:
            mask = np.ones(value.size, dtype='bool')
        self.mask = mask
        self.dtype = self.value.dtype

    def __getitem__(self, item):
        idxs, t = find_indices(item, self.times.value)
        mask = self.mask[idxs]
        v = self.value[idxs]
        if isinstance(v, np.ndarray):
            return APStringArray(v, t, mask=mask)
        else:
            return v

    @property
    def dates(self):
        return secs2date(self.times.value)

    def __repr__(self):
        return self.value.__repr__()

    def __str__(self):
        return self.value.__str__()

    def __eq__(self, other):
        return self.value.__eq__(other)

    def __ne__(self, other):
        return self.value.__eq__(other)


class APQuantity(Quantity):
    def __new__(cls, value, times, unit=None, mask=None, dtype=None, copy=True,
                order=None, ndmin=0):
        ret = Quantity.__new__(cls, value, unit=unit, dtype=dtype, copy=copy,
                               order=order, subok=True, ndmin=ndmin)
        if mask is None:
            mask = np.ones(ret.size, dtype='bool')
        ret.mask = mask
        ret.times = times
        return ret

    def __array_ufunc__(self, function, method, *inputs, **kwargs):
        ret = super(APQuantity, self).__array_ufunc__(function,
                                                      method, *inputs,
                                                      **kwargs)
        if ret.dtype == 'bool':
            return ret
        mask = self.mask
        if len(inputs) == 2:
            mask2 = getattr(inputs[1], "mask", None)
            if mask2 is not None:
                mask = np.logical_and(mask, mask2)
        ret.mask = mask
        ret.times = self.times
        return ret

    def __getitem__(self, item):
        idxs, t = find_indices(item, self.times.value)
        ret = super(APQuantity, self).__getitem__(idxs)
        mask = self.mask[idxs]
        return APQuantity(ret.value, t, unit=self.unit, 
                          dtype=self.dtype, mask=mask)

    def __getslice__(self, i, j):
        ret = super(APQuantity, self).__getslice__(i, j)
        t = self.times[i:j]
        mask = self.mask[i:j]
        return APQuantity(ret.value, t, unit=self.unit,
                          dtype=self.dtype, mask=mask)

    def to(self, unit, equivalencies=[]):
        ret = super(APQuantity, self).to(unit, equivalencies=equivalencies)
        return APQuantity(ret.value, self.times, unit=ret.unit, mask=self.mask,
                          dtype=ret.dtype)

    _dates = None
    @property
    def dates(self):
        if self._dates is None:
            self._dates = secs2date(self.times.value)
        return self._dates

    def argmax(self, dates=False):
        idx = np.argmax(self.value)
        times = self.times[idx]
        if dates:
            return secs2date(times)
        else:
            return times

    def argmin(self, dates=False):
        idx = np.argmin(self.value)
        times = self.times[idx]
        if dates:
            return secs2date(times)
        else:
            return times


units_trans = {"DEGC": "deg_C",
               "STEP": "",
               "0": "",
               "DEGF": "deg_F",
               "RADPS": "rad/s"}


mit_fields = ["beptic", "blockid", "bepint",
              "relay", "rad_pcb_a", "rad_pcb_b"]


def get_units(ftype, fname):
    import Ska.tdb
    if ftype == 'states':
        unit = state_units.get(fname, '')
    else:
        if ftype == 'model' and fname in state_units:
            unit = state_units[fname]
        else:
            unit = msid_units.get(fname, None)
        if unit is None:
            try:
                unit = Ska.tdb.msids[fname].eng_unit
                unit = units_trans.get(unit, unit)
                msid_units[fname] = unit
            except KeyError:
                if fname not in mit_fields:
                    mylog.warning(f"Cannot find a unit for MSID {fname}. "
                                  "Setting to dimensionless.")
                unit = ''
    if unit == "DEG":
        unit = 'deg'
    return unit
