import numpy as np
from acispy.thermal_models import ThermalModelRunner
from pathlib import Path
from astropy.io import ascii
from .utils import assert_equal_nounits


test_dir = Path(__file__).resolve().parent


def test_handmade_states():
    from IPython import embed
    states = {"ccd_count": np.array([5, 6, 1]),
              "pitch": np.array([150.0] * 3),
              "fep_count": np.array([5, 6, 1]),
              "clocking": np.array([1] * 3),
              "vid_board": np.array([1] * 3),
              "off_nom_roll": np.array([0.0] * 3),
              "simpos": np.array([-99616.0] * 3),
              "datestart": np.array(["2015:002:00:00:00", "2015:002:12:00:00", "2015:003:12:00:00"]),
              "datestop": np.array(["2015:002:12:00:00", "2015:003:12:00:00", "2015:005:00:00:00"])}
    dpa_model = ThermalModelRunner("1dpamzt", "2015:002:00:00:00",
                                   "2015:005:00:00:00", states=states,
                                   T_init=13.0, model_spec=test_dir / "dpa_test_spec.json")
    t = ascii.read(test_dir / "handmade_temp.dat")
    assert_equal_nounits(t["1dpamzt"].data, dpa_model["1dpamzt"])
    assert_equal_nounits(t["time"].data, dpa_model["1dpamzt"].times)
    assert_equal_nounits(t["date"].data, dpa_model["1dpamzt"].dates)
    for k, v in states.items():
        assert_equal_nounits(dpa_model["states", k], v)


def test_states_from_commands():
    from kadi import commands
    # commands as a CommandTable
    cmds = commands.get_cmds('2018:001:00:00:00', '2018:002:00:00:00')
    psmc_model = ThermalModelRunner.from_commands("1pdeaat", cmds)
    # commands as a list of dicts
    dict_cmds = cmds.as_list_of_dict()
    psmc_model2 = ThermalModelRunner.from_commands("1pdeaat", dict_cmds)
    assert_equal_nounits(psmc_model["1pdeaat"], psmc_model2["1pdeaat"])
    assert_equal_nounits(psmc_model["ccd_count"], psmc_model2["ccd_count"])
    assert_equal_nounits(psmc_model["pitch"], psmc_model2["pitch"])
    # Normal call
    psmc_model3 = ThermalModelRunner("1pdeaat", "2018:001:00:00:00",
                                     "2018:002:00:00:00")
    assert_equal_nounits(psmc_model["1pdeaat"], psmc_model3["1pdeaat"])
    assert_equal_nounits(psmc_model["ccd_count"], psmc_model3["ccd_count"])
    assert_equal_nounits(psmc_model["pitch"], psmc_model3["pitch"])


def test_states_from_backstop():
    backstop = test_dir / "CR229_2202.backstop"
    tm_aca = ThermalModelRunner.from_backstop("aacccdpt", backstop,
                                              other_init={"aca0": -10})
