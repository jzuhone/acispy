from astropy.units import Quantity
from six import string_types
import numpy as np
from Chandra.Time import secs2date, DateTime
from numpy import \
    add, subtract, multiply, divide, logaddexp, logaddexp2, true_divide, \
    power, remainder, mod, arctan2, hypot, bitwise_and, bitwise_or, \
    bitwise_xor, left_shift, right_shift, greater, greater_equal, less, \
    less_equal, not_equal, equal, logical_and, logical_or, logical_xor, \
    maximum, minimum, fmax, fmin, copysign, nextafter, ldexp, fmod

binary_operators = (
    add, subtract, multiply, divide, logaddexp, logaddexp2, true_divide, power,
    remainder, mod, arctan2, hypot, bitwise_and, bitwise_or, bitwise_xor,
    left_shift, right_shift, greater, greater_equal, less, less_equal,
    not_equal, equal, logical_and, logical_or, logical_xor, maximum, minimum,
    fmax, fmin, copysign, nextafter, ldexp, fmod,
)

def parse_index(idx, times): 
    if isinstance(idx, (int, np.ndarray)):
        return idx
    else:
        if isinstance(idx, string_types):
            idx = DateTime(idx).secs
        idx = np.searchsorted(times, idx)
    return idx

def find_indices(item, times):
    if getattr(times, "ndim", None) == 2:
        t1 = times[0]
        t2 = times[1]
    else:
        t1 = t2 = times
    if isinstance(item, slice):
        idxs = slice(parse_index(item.start, t1),
                     parse_index(item.stop, t2))
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

    def __getitem__(self, item):
        idxs, t = find_indices(item, self.times.value)
        mask = self.mask[idxs]
        v = self.value[idxs]
        if isinstance(v, np.ndarray):
            return APStringArray(self.value[idxs], t, mask=mask)
        else:
            return v

    @property
    def dates(self):
        return secs2date(self.times.value)

    def __repr__(self):
        return self.value.__repr__()

    def __str__(self):
        return self.value.__str__()

class APQuantity(Quantity):
    def __new__(cls, value, times, unit=None, mask=None, dtype=None):
        ret = Quantity.__new__(cls, value, unit=unit, dtype=dtype)
        if mask is None:
            mask = np.ones(ret.size, dtype='bool')
        ret.mask = mask
        ret.times = times
        return ret

    def __array_wrap__(self, obj, context=None):
        ret = super(APQuantity, self).__array_wrap__(obj, context=context)
        mask = self.mask
        if context[0] in binary_operators:
            mask2 = getattr(context[1][1], "mask", None)
            if mask2 is not None:
                mask = np.logical_and(mask, mask2)
        ret_class = type(self)
        return ret_class(ret.value, self.times, unit=ret.unit, mask=mask,
                         dtype=ret.dtype)

    def __getitem__(self, item):
        idxs, t = find_indices(item, self.times.value)
        ret = super(APQuantity, self).__getitem__(idxs)
        mask = self.mask[idxs]
        return APQuantity(ret.value, t, unit=self.unit, 
                          dtype=self.dtype, mask=mask)

    @property
    def dates(self):
        return secs2date(self.times.value)
