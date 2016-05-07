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
                "ra": "RA",
                "dec": "Dec",
                "dither": None,
                "fep_count": "FEP Count",
                "hetg": None,
                "letg": None,
                "obsid": "ObsID",
                "pcad_mode": None,
                "pitch": "Pitch",
                "power_cmd": None,
                "roll": "Roll",
                "si_mode": None,
                "simfa_pos": None,
                "simpos": "SIM-Z",
                "q1": "q1",
                "q2": "q2",
                "q3": "q3",
                "q4": "q4",
                "trans_keys": None,
                "vid_board": None,
                "off_nominal_roll": "Off-Nominal\nRoll"}

state_units = {'ra': 'deg',
               'dec': 'deg',
               'roll': 'deg',
               'off_nominal_roll': 'deg',
               'tstart': 's',
               'tstop': 's',
               'pitch': 'deg'}

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
              'gnd_2': 'V'}

unit_table = {"msids": msid_units,
              "states": state_units,
              "model": msid_units}

mit_trans_table = {"BEP_PCB": "tmp_bep_pcb",
                   "BEP_OSC": "tmp_bep_osc",
                   "FEP0_MONG": "tmp_fep0_mong",
                   "FEP0_PCB": "tmp_fep0_pcb",
                   "FEP0_ACTEL": "tmp_fep0_actel",
                   "FEP0_RAM": "tmp_fep0_ram",
                   "FEP0_FB": "tmp_fep0_fb",
                   "FEP1_MONG": "tmp_fep1_mong",
                   "FEP1_PCB": "tmp_fep1_pcb",
                   "FEP1_ACTEL": "tmp_fep1_actel",
                   "FEP1_RAM": "tmp_fep1_ram",
                   "FEP1_FB": "tmp_fep1_fb",
                   "DEA28VDCA": "dea28volta",
                   "DEA24VDCA": "dea24volta",
                   "DEAM15VDCA": "deam15volta",
                   "DEAP15VDCA": "deap15volta",
                   "DEAM6VDCA": "deam6volta",
                   "DEAP6VDCA": "deap6volta",
                   "DEA28VDCB": "dea28voltb",
                   "DEA24VDCB": "dea24voltb",
                   "DEAM15VDCB": "deam15voltb",
                   "DEAP15VDCB": "deap15voltb",
                   "DEAM6VDCB": "deam6voltb",
                   "DEAP6VDCB": "deap6voltb"}

unit_labels = {"V": 'V',
               "A": 'A',
               "deg_C": '$\mathrm{^\circ{C}}$',
               "W": "W",
               "s": "s",
               "deg": "deg"}

def get_display_name(type, name):
    if type == "model":
        display_name = name.upper() + " Model"
    elif type == "states":
        display_name = state_labels[name]
    else:
        display_name = name.upper()
    return display_name

def interpolate(times_in, times_out):
    ok = (times_out >= times_in[0]) & (times_out <= times_in[-1])
    times_out = times_out[ok]
    idxs = Ska.Numpy.interpolate(np.arange(len(times_in)),
                                 times_in, times_out,
                                 method='nearest', sorted=True)
    return ok, idxs

def moving_average(a, n=5):
    shape = a.shape[:-1] + (a.shape[-1] - n + 1, n)
    strides = a.strides + (a.strides[-1],)
    return np.mean(np.lib.stride_tricks.as_strided(a, shape=shape, strides=strides), -1)
