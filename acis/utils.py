from __future__ import print_function

from Chandra.Time import DateTime
import Ska.Sun
import numpy as np

def get_time(time):
    if time is "now":
        time = DateTime()
        print("Current time is %s UTC." % time.date)
    else:
        time = DateTime(time)
    return time

def calc_off_nom_rolls(states):
    off_nom_rolls = []
    for state in states:
        try:
            att = [state[x] for x in ['q1', 'q2', 'q3', 'q4']]
            time = (state['tstart'] + state['tstop']) / 2
            off_nom_rolls.append(Ska.Sun.off_nominal_roll(att, time))
        except (KeyError, ValueError):
            return None
    return np.array(off_nom_rolls)

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

msid_units = {'1deamzt': '$\mathrm{^\circ{C}}$',
              '1dpamzt': '$\mathrm{^\circ{C}}$',
              '1pdeaat': '$\mathrm{^\circ{C}}$',
              '1pin1at': '$\mathrm{^\circ{C}}$',
              '1pdeabt': '$\mathrm{^\circ{C}}$',
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
              '1dep3bvo': 'V'}


