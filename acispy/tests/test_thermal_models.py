import numpy as np
from acispy.thermal_models import ThermalModelRunner, \
    ThermalModelFromRun, ThermalModelFromLoad, \
    SimulateSingleState, SimulateECSRun
from pathlib import Path
from astropy.io import ascii
from .utils import assert_equal_nounits, assert_allclose_nounits


test_dir = Path(__file__).resolve().parent
dpa_spec = test_dir / "dpa_test_spec.json"
aca_spec = test_dir / "aca_test_spec.json"
dea_spec = test_dir / "dea_test_spec.json"
fp_spec = test_dir / "acisfp_test_spec.json"


def test_handmade_states():
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
                                   T_init=13.0, model_spec=dpa_spec)
    t = ascii.read(test_dir / "handmade_temp.dat")
    assert_allclose_nounits(t["1dpamzt"].data, dpa_model["1dpamzt"])
    assert_allclose_nounits(t["time"].data, dpa_model["1dpamzt"].times)
    assert_equal_nounits(t["date"].data, dpa_model["1dpamzt"].dates)
    for k, v in states.items():
        assert_equal_nounits(dpa_model["states", k], v)


def test_get_msids():
    fp_model = ThermalModelRunner("fptemp_11", "2020:002:00:00:00", 
                                  "2020:005:00:00:00", get_msids=True, 
                                  model_spec=fp_spec)
    fp_model.map_state_to_msid("ccd_count", "fptemp_11")
    fp_model.map_state_to_msid("pitch", "fptemp_11")
    t = ascii.read(test_dir / "model_and_data.dat")
    assert_allclose_nounits(t["model_fptemp_11"].data, 
                            fp_model["model","fptemp_11"])
    assert_allclose_nounits(t["msids_fptemp_11"].data, 
                            fp_model["msids","fptemp_11"])
    assert_allclose_nounits(t["time"].data, fp_model["model","fptemp_11"].times)
    assert_equal_nounits(t["date"].data, fp_model["model","fptemp_11"].dates)
    assert_allclose_nounits(t["model_earth_solid_angle"].data, 
                            fp_model["model","earth_solid_angle"])
    assert_equal_nounits(t["msids_ccd_count"].data,
                         fp_model["msids","ccd_count"])


def test_states_from_commands():
    from kadi import commands
    # commands as a CommandTable from kadi
    cmds = commands.get_cmds('2018:001:00:00:00', '2018:002:00:00:00')
    dpa_model = ThermalModelRunner.from_commands("1dpamzt", cmds)
    # same commands as a list of dicts
    dict_cmds = cmds.as_list_of_dict()
    dpa_model2 = ThermalModelRunner.from_commands("1dpamzt", dict_cmds)
    assert_allclose_nounits(dpa_model["1dpamzt"], dpa_model2["1dpamzt"])
    assert_equal_nounits(dpa_model["ccd_count"], dpa_model2["ccd_count"])
    assert_allclose_nounits(dpa_model["pitch"], dpa_model2["pitch"])
    # Normal call, kadi is called internally by xija
    dpa_model3 = ThermalModelRunner("1dpamzt", cmds["date"][0],
                                    cmds["date"][-1])
    # we do not expect great precision here because the state structures
    # are slightly different
    assert_allclose_nounits(dpa_model["1dpamzt"], dpa_model3["1dpamzt"],
                            rtol=0.02)


def test_states_from_backstop():
    backstop = test_dir / "CR229_2202.backstop"
    aca_model = ThermalModelRunner.from_backstop("aacccdpt", backstop,
                                                 model_spec=aca_spec,
                                                 other_init={"aca0": -10})
    t = ascii.read(test_dir / "backstop_temp.dat")
    assert_allclose_nounits(t["aacccdpt"].data, aca_model["aacccdpt"])
    assert_allclose_nounits(t["time"].data, aca_model["aacccdpt"].times)
    assert_equal_nounits(t["date"].data, aca_model["aacccdpt"].dates)


def test_load_output():
    tm1 = ThermalModelFromLoad("JUN2121")
    tm2 = ThermalModelFromRun(test_dir / "out_dpa")
    assert_allclose_nounits(tm1["1dpamzt"], tm2["1dpamzt"])
    assert_allclose_nounits(tm1["1dpamzt"].times, tm2["1dpamzt"].times)
    assert_equal_nounits(tm1["1dpamzt"].dates, tm2["1dpamzt"].dates)


def test_specify_path():
    from xija.get_model_spec import REPO_PATH
    from pathlib import Path
    model_spec = Path(REPO_PATH / 'chandra_models' / 'xija' /
                      'dpa' / 'dpa_spec.json')
    tm1 = ThermalModelRunner("1dpamzt", '2018:001:00:00:00',
                             '2018:002:00:00:00')
    tm2 = ThermalModelRunner("1dpamzt", '2018:001:00:00:00',
                             '2018:002:00:00:00', model_spec=model_spec)
    assert_allclose_nounits(tm1["1dpamzt"], tm2["1dpamzt"])
    assert_allclose_nounits(tm1["1dpamzt"].times, tm2["1dpamzt"].times)
    assert_equal_nounits(tm1["1dpamzt"].dates, tm2["1dpamzt"].dates)
    assert_equal_nounits(tm1["ccd_count"], tm2["ccd_count"])
    assert_allclose_nounits(tm1["pitch"], tm2["pitch"])


def test_single_state():
    states = {"pitch": 75.0, "off_nom_roll": -6.0, "clocking": 1,
              "ccd_count": 6, "simpos": 75624.0}
    tm = SimulateSingleState("1deamzt", "2016:201:05:12:03",
                             "2016:202:05:12:03", states, 15.0,
                             model_spec=dea_spec)
    t = ascii.read(test_dir / "single_state.dat")
    assert_allclose_nounits(t["1deamzt"].data, tm["1deamzt"])
    assert_allclose_nounits(t["time"].data, tm["1deamzt"].times)
    assert_equal_nounits(t["date"].data, tm["1deamzt"].dates)
    for k, v in states.items():
        assert tm["states", k].size == 1
        if tm['states',k].dtype == np.float64:
            func = assert_allclose_nounits
        else:
            func = assert_equal_nounits
        func(tm["states", k][0], v)
