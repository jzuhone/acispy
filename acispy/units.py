from astropy.units import Quantity
from six import string_types
import numpy as np

class APQuantity(Quantity):
    def __new__(cls, value, unit=None, mask=None, dtype=None):
        ret = Quantity.__new__(cls, value, unit=unit, dtype=dtype)
        ret.mask = mask
        return ret

class MSIDQuantity(APQuantity):
    pass

class StateQuantity(APQuantity):
    pass
