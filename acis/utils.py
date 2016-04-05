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
              'fptemp': '$\mathrm{^\circ{C}}$',
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
              '1crat': '$\mathrm{^\circ{C}}$',
              '1crbt': '$\mathrm{^\circ{C}}$',
              '1wrat': '$\mathrm{^\circ{C}}$',
              '1wrbt': '$\mathrm{^\circ{C}}$',
              '1dpamyt': '$\mathrm{^\circ{C}}$',
              '1sspyt': '$\mathrm{^\circ{C}}$',
              '1ssmyt': '$\mathrm{^\circ{C}}$',
              '1cbat': '$\mathrm{^\circ{C}}$',
              '1cbbt': '$\mathrm{^\circ{C}}$',
              '1dactbt': '$\mathrm{^\circ{C}}$',
              '3tsmydpt': '$\mathrm{^\circ{C}}$',
              '3tspyfet': '$\mathrm{^\circ{C}}$',
              '3tspzdet': '$\mathrm{^\circ{C}}$',
              '3tspzspt': '$\mathrm{^\circ{C}}$',
              '3tsmxspt': '$\mathrm{^\circ{C}}$',
              '3tsmxcet': '$\mathrm{^\circ{C}}$',
              '3rctubpt': '$\mathrm{^\circ{C}}$',
              '3ttacs1t': '$\mathrm{^\circ{C}}$',
              '3ttacs2t': '$\mathrm{^\circ{C}}$',
              '3ttacs3t': '$\mathrm{^\circ{C}}$',
              '1dahhavo': 'V',
              '1dahhbvo': 'V',
              '1dahavo': 'V',
              '1dahbvo': 'V',
              '1dahacu': 'A',
              '1dahbcu': 'A',
              '1dahat': '$\mathrm{^\circ{C}}$',
              '1dahbt': '$\mathrm{^\circ{C}}$',
              '1oahat': '$\mathrm{^\circ{C}}$',
              '1oahbt': '$\mathrm{^\circ{C}}$'}



