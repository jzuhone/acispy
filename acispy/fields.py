from acispy.units import APQuantity, APStringArray
from acispy.utils import calc_off_nom_rolls
import numpy as np
from itertools import count
from acis_taco import calc_earth_vis

class OutputFieldFunction(object):
    def __init__(self, ftype, fname):
        self.ftype = ftype
        self.fname = fname

    def __call__(self, ds):
        obj = getattr(ds, self.ftype)
        return obj[self.fname]

class DerivedField(object):
    def __init__(self, ftype, fname, function, units, display_name=None):
        self.ftype = ftype
        self.fname = fname
        self.function = function
        self.units = units
        if display_name is None:
            self.display_name = fname.upper()
        else:
            self.display_name = display_name

    def __call__(self, ds):
        return self.function(ds)

class FieldContainer(object):
    def __init__(self):
        self.output_fields = {}
        self.derived_fields = {}
        self.types = []

    def __getitem__(self, item):
        if item in self.derived_fields:
            return self.derived_fields[item]
        elif item in self.output_fields:
            return self.output_fields[item]
        else:
            raise KeyError(item)

    def __contains__(self, item):
        return item in self.output_fields or item in self.derived_fields

def create_derived_fields(dset):

    # Off-nominal roll

    def _off_nominal_roll(ds):
        return APQuantity(calc_off_nom_rolls(ds.states),
                          ds.states["q1"].times, "deg")

    dset.add_derived_field("states", "off_nominal_roll", _off_nominal_roll,
                           "deg", display_name="Off-Nominal Roll")

    # Grating

    def _grating(ds):
        grat = np.array(["NONE"]*ds.states["hetg"].value.size)
        grat[ds.states["hetg"] == "INSR"] = "HETG"
        grat[ds.states["letg"] == "INSR"] = "LETG"
        return APStringArray(grat, ds.states["hetg"].times)

    dset.add_derived_field("states", "grating", _grating, "",
                           display_name="Grating")

    # Instrument

    def _instrument(ds):
        simpos = ds.states["simpos"].value
        inst = np.array(["ACIS-I"]*simpos.size)
        inst[np.logical_and(82108 >= simpos, simpos >= 70736)] = "ACIS-S"
        inst[np.logical_and(-20000 >= simpos,  simpos >= -86147)] = "HRC-I"
        inst[np.logical_and(-86148 >= simpos, simpos >= -104362)] = "HRC-S"
        return APStringArray(inst, ds.states["simpos"].times)

    dset.add_derived_field("states", "instrument", _instrument, "",
                           display_name="Instrument")

    # DPA, DEA powers

    def _dpaa_power(ds):
        return (ds["msids", "1dp28avo"]*ds["msids", "1dpicacu"]).to("W")

    dset.add_derived_field("msids", "dpa_a_power", _dpaa_power, 
                           "W", display_name="DPA-A Power")

    def _dpab_power(ds):
        return (ds["msids", "1dp28bvo"]*ds["msids", "1dpicbcu"]).to("W")

    dset.add_derived_field("msids", "dpa_b_power", _dpab_power, 
                           "W", display_name="DPA-B Power")

    def _deaa_power(ds):
        return (ds["msids", "1de28avo"]*ds["msids", "1deicacu"]).to("W")

    dset.add_derived_field("msids", "dea_a_power", _deaa_power, 
                           "W", display_name="DEA-A Power")

    def _deab_power(ds):
        return (ds["msids", "1de28bvo"]*ds["msids", "1deicbcu"]).to("W")

    dset.add_derived_field("msids", "dea_b_power", _deab_power, 
                           "W", display_name="DEA-B Power")

    def _simpos(ds):
        return ds['msids', '3tscpos']*397.7225924607
    dset.add_derived_field("msids", "simpos", _simpos,
                           "", display_name="SIM Position")


    def _earth_solid_angle(ds):
        # Collect individual MSIDs for use in calc_earth_vis()
        ephem_xyzs = [ds["msids", "orbitephem0_{}".format(x)]
                      for x in "xyz"]
        aoattqt_1234s = [ds["msids","aoattqt{}".format(x)]
                         for x in range(1, 5)]
        ephems = np.array([x.value for x in ephem_xyzs]).transpose()
        q_atts = np.array([x.value for x in aoattqt_1234s]).transpose()
        ret = np.empty(ds["msids", "orbitephem0_x"].shape, dtype=float)
        for i, ephem, q_att in zip(count(), ephems, q_atts):
            q_norm = np.sqrt(np.sum(q_att ** 2))
            if q_norm < 0.9:
                q_att = np.array([0.0, 0.0, 0.0, 1.0])
            else:
                q_att = q_att / q_norm
            _, illums, _ = calc_earth_vis(ephem, q_att)
            ret[i] = illums.sum()
        return ret
    dset.add_derived_field("msids", "earth_solid_angle", _earth_solid_angle,
                           "sr", display_name="Effective Earth Solid Angle")
