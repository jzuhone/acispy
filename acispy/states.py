from astropy.io import ascii
import requests
from acispy.units import get_units
from acispy.utils import ensure_list, find_load, calc_off_nom_rolls, \
    dict_to_array
from acispy.units import APQuantity, APStringArray, Quantity
from acispy.time_series import TimeSeriesData
import numpy as np
from cxotime import CxoTime

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
        import numpy.lib.recfunctions as rf
        new_table = {}
        if isinstance(table, np.ndarray):
            state_names = list(table.dtype.names)
            if "date" in state_names:
                table = rf.append_fields(
                    table, ['time'],
                    [CxoTime(table["date"]).secs],
                    usemask=False
                )
                state_names.append("time")
            elif "tstart" not in state_names:
                table = rf.append_fields(
                    table, ["tstart", "tstop"],
                    [CxoTime(table["datestart"]).secs,
                     CxoTime(table["datestop"]).secs],
                    usemask=False)
                state_names += ["tstart", "tstop"]
        else:
            state_names = list(table.keys())
            if "date" in state_names:
                table["time"] = CxoTime(table["date"]).secs
                state_names.append("time")
            elif "tstart" not in state_names:
                table["tstart"] = CxoTime(table["datestart"]).secs
                table["tstop"] = CxoTime(table["datestop"]).secs
                state_names += ["tstart", "tstop"]
        if "tstart" in state_names:
            times = Quantity([table["tstart"], table["tstop"]], "s")
        else:
            times = Quantity(table["time"], "s")
        for k in state_names:
            v = np.asarray(table[k])
            if k == "trans_keys" and v.dtype.char == "O":
                new_table[k] = APStringArray(
                    np.array([",".join(d) for d in v]), times)
            elif v.dtype.char in ['S', 'U', 'O']:
                new_table[k] = APStringArray(v, times)
            else:
                new_table[k] = APQuantity(v, times, get_units("states", k),
                                          dtype=v.dtype)
        if "off_nom_roll" not in state_names:
            v = calc_off_nom_rolls(new_table)
            new_table["off_nom_roll"] = APQuantity(v, times, "deg", dtype=v.dtype)
        super(States, self).__init__(table=new_table)
        derived_states = []
        if "hetg" in new_table and "letg" in new_table:
            derived_states.append("grating")
        if "simpos" in new_table:
            derived_states.append("instrument")
        self.derived_states = derived_states

    @classmethod
    def from_hdf5(cls, g):
        table = dict((k, g[k][()]) for k in g)
        cls(table)

    @classmethod
    def from_kadi_states(cls, tstart, tstop, state_keys=None):
        from kadi.commands import states
        tstart = CxoTime(tstart).date
        tstop = CxoTime(tstop).date
        if state_keys is not None:
            state_keys = ensure_list(state_keys)
        t = states.get_states(tstart, tstop, state_keys=state_keys,
                              merge_identical=True).as_array()
        return cls(t)

    @classmethod
    def from_load_page(cls, load, comp="DPA"):
        load = find_load(load)
        url = f"http://cxc.cfa.harvard.edu/acis/{comp}_thermPredic/"
        url += f"{load[:-1].upper()}/ofls{load[-1].lower()}/states.dat"
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
    def from_commands(cls, cmds, state_keys=None):
        from kadi.commands import states
        t = states.get_states(cmds=cmds, state_keys=state_keys,
                              merge_identical=True).as_array()
        return cls(t)

    def get_states(self, time):
        """
        Get the commanded states at a given *time*.
        """
        time = CxoTime(time).secs
        state = {}
        for key in self.keys():
            state[key] = self[key][time]
        return state

    def as_array(self):
        return dict_to_array(self.table)

    @property
    def current_states(self):
        return self.get_states("now")

    def __len__(self):
        return self['tstart'].size