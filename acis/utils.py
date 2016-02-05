from __future__ import print_function
from astropy.time import Time
import Ska.Sun
import numpy as np

def get_time(time):
    if time is "now":
        time = Time.now()
        print("Current time is %s UTC." % time.yday)
    else:
        time = Time(time)
    return time

def convert_decyear_to_yday(time):
    return Time(time, format='decimalyear').replicate(format='yday')

def calc_off_nom_rolls(states):
    off_nom_rolls = []
    for state in states:
        att = [state[x] for x in ['q1', 'q2', 'q3', 'q4']]
        time = (state['tstart'] + state['tstop']) / 2
        off_nom_rolls.append(Ska.Sun.off_nominal_roll(att, time))
    return np.array(off_nom_rolls)


