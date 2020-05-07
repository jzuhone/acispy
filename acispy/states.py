from astropy.io import ascii
import requests
from acispy.units import get_units
from acispy.utils import get_time, ensure_list, find_load
from Chandra.cmd_states import fetch_states, get_states, \
    get_state0, get_cmds
from acispy.units import APQuantity, APStringArray, Quantity
from acispy.time_series import TimeSeriesData
import os
import numpy as np

cmd_state_codes = {("states", "hetg"): {"RETR": 0, "INSR": 1},
                   ("states", "letg"): {"RETR": 0, "INSR": 1},
                   ("states", "grating"): {"NONE": 0, "LETG": 1,
                                           "HETG": 2},
                   ("states", "instrument"): {"ACIS-S": 0, "ACIS-I": 1,
                                              "HRC-S": 2, "HRC-I": 3},
                   ("states", "dither"): {"DISA": 0, "ENAB": 1},
                   ("states", "pcad_mode"): {"STBY": 0, "NPNT": 1, 
                                             "NMAN": 2, "NSUN": 3, 
                                             "PWRF": 4, "RMAN": 5, 
                                             "NULL": 6}}

state_dtypes = {"ccd_count": "int",
                "fep_count": "int",
                "vid_board": "int",
                "clocking":  "int"}


class States(TimeSeriesData):

    def __init__(self, table):
        new_table = {}
        times = Quantity([table["tstart"], table["tstop"]], "s")
        if isinstance(table, np.ndarray):
            state_names = table.dtype.names
        else:
            state_names = list(table.keys())
        for k in state_names:
            v = table[k]
            if v.dtype.char in ['S', 'U', 'O']:
                new_table[k] = APStringArray(v, times)
            else:
                new_table[k] = APQuantity(v, times, get_units("states", k),
                                          dtype=v.dtype)
        super(States, self).__init__(table=new_table)

    @classmethod
    def from_hdf5(cls, g):
        table = dict((k, g[k][()]) for k in g)
        cls(table)

    @classmethod
    def from_database(cls, tstart, tstop, states=None, server=None):
        tstart = get_time(tstart)
        tstop = get_time(tstop)
        if states is not None:
            states = ensure_list(states)
        t = fetch_states(tstart, tstop, vals=states, server=server)
        return cls(t)

    @classmethod
    def from_load_page(cls, load, comp="DPA"):
        load = find_load(load)
        url = "http://cxc.cfa.harvard.edu/acis/%s_thermPredic/" % comp
        url += "%s/ofls%s/states.dat" % (load[:-1].upper(), load[-1].lower())
        u = requests.get(url)
        t = ascii.read(u.text)
        table = dict((k, t[k].data) for k in t.keys())
        # hack
        if 'T_pin1at' in table:
            table.pop("T_pin1at")
        return cls(table)

    @classmethod
    def from_load_file(cls, states_file):
        t = ascii.read(states_file)
        table = dict((k, t[k].data) for k in t.keys())
        # hack
        if 'T_pin1at' in table:
            table.pop("T_pin1at")
        return cls(table)

    @classmethod
    def from_commands(cls, tstart, tstop, cmds=None):
        import Ska.DBI
        tstart = get_time(tstart)
        tstop = get_time(tstop)
        server = os.path.join(os.environ['SKA'], 'data', 'cmd_states', 'cmd_states.db3')
        db = Ska.DBI.DBI(dbi='sqlite', server=server, user='aca_read', database='aca')
        if cmds is None:
            cmds = get_cmds(tstart, tstop, db)
        state0 = get_state0(tstart, db, datepar='datestart', date_margin=None)
        t = get_states(state0, cmds)
        return cls(t)

    def get_states(self, time):
        time = get_time(time, 'secs')
        state = {}
        for key in self.keys():
            state[key] = self[key][time]
        return state

    @property
    def current_states(self):
        return self.get_states("now")

    def __len__(self):
        return self['tstart'].size