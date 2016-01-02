from __future__ import print_function
from astropy.time import Time
import numpy as np
from six import string_types

def get_time(time):
    if isinstance(time, string_types):
        if time == "now":
            time = Time.now()
            print("Current time is %s UTC." % time.yday)
    else:
        time = Time(time)
    return time

def search_for_status(status_list, time):
    # We have this if we need it
    err = "The time %s is not within the current time frame!" % time
    if time.decimalyear < status_list[0][0]:
        raise RuntimeError(err)
    idx = np.searchsorted(status_list[0], time.decimalyear)
    try:
        stat = status_list[1][idx]
    except IndexError:
        raise RuntimeError(err)
    return stat

def convert_decyear_to_yday(time):
    return Time(time, format='decimalyear').replicate(format='yday')

