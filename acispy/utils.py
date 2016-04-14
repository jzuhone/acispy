from __future__ import print_function

from Chandra.Time import DateTime
import Ska.Sun
import Ska.Numpy
import numpy as np

def get_time(time):
    if time is "now":
        time = DateTime()
    else:
        time = DateTime(time)
    return time

def calc_off_nom_rolls(states):
    times = 0.5*(states['tstart'] + states['tstop'])
    atts = np.array([states["q%d" % x] for x in range(1, 5)]).transpose()
    return np.array([Ska.Sun.off_nominal_roll(att, time)
                     for time, att in zip(times, atts)])

state_labels = {"ccd_count": "CCD Count",
                "clocking": "Clocking",
                "ra": "RA (deg)",
                "dec": "Dec (deg)",
                "dither": None,
                "fep_count": "FEP Count",
                "hetg": None,
                "letg": None,
                "obsid": "ObsID",
                "pcad_mode": None,
                "pitch": "Pitch (deg)",
                "power_cmd": None,
                "roll": "Roll (deg)",
                "si_mode": None,
                "simfa_pos": None,
                "simpos": "SIM-Z (steps)",
                "q1": "q1",
                "q2": "q2",
                "q3": "q3",
                "q4": "q4",
                "trans_keys": None,
                "vid_board": None,
                "off_nominal_roll": "Off-Nominal\nRoll (deg)"}

state_list = len(state_labels.keys())

state_units = {'ra': 'deg',
               'dec': 'deg',
               'roll': 'deg',
               'off_nominal_roll': 'deg',
               'tstart': 's',
               'tstop': 's'}

msid_units = {'1deamzt': 'deg_C',
              '1dpamzt': 'deg_C',
              '1pdeaat': 'deg_C',
              '1pin1at': 'deg_C',
              '1pdeabt': 'deg_C',
              'fptemp_11': 'deg_C',
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
              '1oahbt': 'deg_C'}

msid_unit_labels = {"V": 'V',
                    "A": 'A',
                    "deg_C": '$\mathrm{^\circ{C}}$',
                    "W": "W"}

msid_list = list(msid_units.keys())

def interpolate(times_in, times_out, times_out2=None):
    ok = (times_out >= times_in[0]) & (times_out <= times_in[-1])
    if times_out2 is not None:
        ok2 = (times_out2 >= times_in[0]) & (times_out2 <= times_in[-1])
        ok = ok & ok2
    times_out = times_out[ok]
    idxs = Ska.Numpy.interpolate(np.arange(len(times_in)),
                                 times_in, times_out,
                                 method='nearest', sorted=True)
    if times_out2 is not None:
        times_out2 = times_out2[ok]
        idxs2 = Ska.Numpy.interpolate(np.arange(len(times_in)),
                                      times_in, times_out2,
                                      method='nearest', sorted=True)
        return ok, (idxs, idxs2)
    else:
        return ok, idxs