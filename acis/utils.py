from __future__ import print_function
from astropy.time import Time

def get_time(time):
    if time is "now":
        time = Time.now()
        print("Current time is %s UTC." % time.yday)
    else:
        time = Time(time)
    return time

def convert_decyear_to_yday(time):
    return Time(time, format='decimalyear').replicate(format='yday')

