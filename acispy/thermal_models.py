import xija
from astropy.units import Quantity
from astropy.io import ascii
from acispy.dataset import Dataset
from acispy.plots import DatePlot
import numpy as np
from cxotime import CxoTime
from acispy.states import States
from acispy.model import Model
from acispy.msids import MSIDs
from acispy.time_series import EmptyTimeSeries
from acispy.utils import mylog, \
    ensure_list, plotdate2cxctime
import Ska.Numpy
import Ska.engarchive.fetch_sci as fetch
import matplotlib.pyplot as plt
from kadi import events, commands
import importlib
from matplotlib import font_manager
from pathlib import Path


short_name = {"1deamzt": "dea",
              "1dpamzt": "dpa",
              "1pdeaat": "psmc",
              "fptemp_11": "acisfp",
              "tmp_fep1_mong": "fep1_mong",
              "tmp_fep1_actel": "fep1_actel",
              "tmp_fep1_fb": "fep1_fb",
              "tmp_bep_pcb": "bep_pcb",
              "aacccdpt": "aca",
              "pftank2t": "pftank2t",
              "fwdblkhd": "4rt700t",
              "minusyz": "minusyz"}

short_name_rev = {v: k for k, v in short_name.items()}

full_name = {"1deamzt": "DEA",
             "1dpamzt": "DPA",
             "1pdeaat": "PSMC",
             "fptemp_11": "Focal Plane",
             "tmp_fep1_mong": "FEP1 Mongoose",
             "tmp_fep1_actel": "FEP1 Actel",
             "tmp_fep1_fb": "FEP1 FB",
             "tmp_bep_pcb": "BEP PCB"}

limits = {'1deamzt': 36.5,
          '1dpamzt': 37.5,
          '1pdeaat': 52.5,
          'tmp_fep1_mong': 47.0,
          'tmp_fep1_actel': 46.0,
          'tmp_bep_pcb': 43.0,
          'tmp_fep1_fb': 41.0,
          'fptemp_11': {"ACIS-I": -112.0, "ACIS-S": -111.0}}

low_limits = {
    'tmp_fep1_mong': 2.0,
    'tmp_fep1_actel': 2.0,
    'tmp_fep1_fb': 2.0,
    'tmp_bep_pcb': 4.5
}

acis_models = ["1deamzt",
               "1dpamzt",
               "1pdeaat",
               "fptemp_11",
               "tmp_fep1_mong",
               "tmp_fep1_actel",
               "tmp_bep_pcb"]

margins = {'1deamzt': 2.0,
           '1dpamzt': 2.0,
           '1pdeaat': 4.5,
           'tmp_fep1_mong': 2.0,
           'tmp_fep1_actel': 2.0,
           'tmp_fep1_fb': 2.0,
           'tmp_bep_pcb': 2.0}

model_classes = {
    "dpa": "DPACheck",
    "dea": "DEACheck",
    "psmc": "PSMCCheck",
    "acisfp": "ACISFPCheck",
    "fep1_mong": "FEP1MongCheck",
    "fep1_actel": "FEP1ActelCheck",
    "bep_pcb": "BEPPCBCheck"
}


def find_json(name, model_spec):
    from xija.get_model_spec import get_xija_model_spec, REPO_PATH
    msg = f"The JSON file {model_spec} does not exist! Please " \
          f"specify a JSON file using the 'model_spec' keyword argument."
    if model_spec is None:
        name = short_name.get(name, name)
        try:
            model_spec, version = get_xija_model_spec(name)
        except ValueError:
            raise IOError(msg)
        mylog.info("chandra_models version = %s", version)
        model_path = Path(REPO_PATH / 'chandra_models' / 'xija' /
                          name / f'{name}_spec.json')
    else:
        model_path = Path(model_spec).resolve()
        if not model_path.exists():
            raise IOError(msg)
    mylog.info("model_spec = %s", model_path)
    return model_spec


class ModelDataset(Dataset):
    def __init__(self, msids, states, model):
        super(ModelDataset, self).__init__(msids, states, model)

    def write_model(self, filename, overwrite=False):
        """
        Write the model data vs. time to an ASCII text file.

        Parameters
        ----------
        filename : string
            The filename to write the data to.
        overwrite : boolean, optional
            If True, an existing file with the same name will be overwritten.
        """
        if Path(filename).exists() and not overwrite:
            raise IOError(f"File {filename} already exists, but overwrite=False!")
        names = []
        arrays = []
        for i, msid in enumerate(self.model.keys()):
            if i == 0:
                times = self.times("model", msid).value
                dates = self.dates("model", msid)
                names += ['time', 'date']
                arrays += [times, dates]
            names.append(msid)
            arrays.append(self["model", msid].value)
        temp_array = np.rec.fromarrays(arrays, names=names)
        fmt = {(name, '%.2f') for name in names if name != "date"}
        out = open(filename, 'w')
        Ska.Numpy.pprint(temp_array, fmt, out)
        out.close()

    def write_model_and_data(self, filename, overwrite=False, 
                             mask_radzones=False, mask_fmt1=False,
                             mask_badtimes=True, tstart=None,
                             tstop=None):
        """
        Write the model, telemetry, and states data vs. time to
        an ASCII text file. The state data is interpolated to the
        times of the model so that everything is at a common set
        of times.

        Parameters
        ----------
        filename : string
            The filename to write the data to.
        overwrite : boolean, optional
            If True, an existing file with the same name will be overwritten.
        """
        states_to_map = ["vid_board", "pitch", "clocking", "simpos",
                         "ccd_count", "fep_count", "off_nom_roll"]
        out = []
        for i, msid in enumerate(self.model.keys()):
            if i == 0:
                if self.states._is_empty:
                    out += [("model", state) for state in states_to_map]
                else:
                    for state in states_to_map:
                        self.map_state_to_msid(state, msid)
                        out.append(("msids", state))
            out.append(("model", msid))
            if ("msids", msid) in self.field_list:
                self.add_diff_data_model_field(msid)
                out += [("msids", msid), ("model", f"diff_{msid}")]
        msid = list(self.model.keys())[0]
        telem = self["msids", msid]
        mask = np.ones_like(telem.value, dtype='bool')
        if tstart is not None:
            tstart = CxoTime(tstart).secs
            mask[telem.times.value < tstart] = False
        if tstop is not None:
            tstop = CxoTime(tstop).secs
            mask[telem.times.value > tstop] = False
        if mask_radzones:
            rad_zones = events.rad_zones.filter(start=telem.dates[0],
                                                stop=telem.dates[-1])
            for rz in rad_zones:
                idxs = np.logical_and(telem.times.value >= rz.tstart,
                                      telem.times.value <= rz.tstop)
                mask[idxs] = False
        if mask_fmt1:
            which = self["msids", "ccsdstmf"] == "FMT1"
            mask[which] = False
        self.write_msids(filename, out, overwrite=overwrite, mask=mask)

    def _get_msids(self, model, comps, tl_file):
        comps = [comp.lower() for comp in comps]
        times = model[comps[0]].times.value
        tstart = times[0] - 700.0
        tstop = times[-1] + 700.0
        start = CxoTime(tstart).date
        stop = CxoTime(tstop).date
        if tl_file is not None:
            msids = MSIDs.from_tracelog(tl_file, tbegin=tstart, tend=tstop)
        else:
            if "earth_solid_angle" in comps:
                comps.remove("earth_solid_angle")
            comps.append("ccsdstmf")
            tlast = 1.0e99
            for comp in comps:
                tlast = min(fetch.get_time_range(comp, format='secs')[1], tlast)
            if tstop > tlast:
                raise RuntimeError("The model extends past the the last date in the "
                                   "engineering archive. Please set get_msids=False.")
            msids = MSIDs.from_database(comps, start, tstop=stop, filter_bad=True,
                                        interpolate='nearest', interpolate_times=times)
        return msids

    def make_dashboard_plots(self, msid, tstart=None, tstop=None, yplotlimits=None,
                             errorplotlimits=None, fig=None, figfile=None,
                             bad_times=None, mask_radzones=False, plot_limits=True, 
                             mask_fmt1=False):
        """
        Make dashboard plots for the particular thermal model.

        Parameters
        ----------
        msid : string
            The MSID name to plot in the dashboard. 
        tstart : string, optional
            The start time of the data for the dashboard plot. If not specified,
            the beginning of the thermal model run is used.
        tstop : string, optional
            The stop time of the data for the dashboard plot. If not specified,
            the end of the thermal model run is used.
        yplotlimits : two-element array_like, optional
            The (min, max) bounds on the temperature to use for the
            temperature vs. time plot. Default: Determine the min/max
            bounds from the telemetry and model prediction and
            decrease/increase by degrees to determine the plot limits.
        errorplotlimits : two-element array_like, optional
            The (min, max) error bounds to use for the error plot.
            Default: [-15, 15]
        fig : :class:`~matplotlib.figure.Figure`, optional
            A Figure instance to plot in. Default: None, one will be
            created if not provided.
        figfile : string, optional
            The file to write the dashboard plot to. One will be created
            if not provided.
        bad_times : list of tuples, optional
            Provide a set of times to exclude from the creation of the
            dashboard plot.
        mask_radzones : boolean, optional
            If True, mask out radzone periods for dashboard plots of the
            focal plane model. Default: False
        plot_limits : boolean, optional
            If True, plot the yellow caution and planning limits on the
            dashboard plots. Default: True
        """
        from xijafit import dashboard as dash
        if fig is None:
            fig = plt.figure(figsize=(20,10))
        if ("msids", msid) not in self.field_list:
            raise RuntimeError("You must include the real data if you want to make a "
                               "dashboard plot! Set get_msids=True when creating the"
                               "thermal model!")
        telem = self["msids", msid]
        pred = self["model", msid]
        mask = np.logical_and(telem.mask, pred.mask)
        if tstart is not None:
            tstart = CxoTime(tstart).secs
            mask[telem.times.value < tstart] = False
        if tstop is not None:
            tstop = CxoTime(tstop).secs
            mask[telem.times.value > tstop] = False
        if bad_times is not None:
            for (left, right) in bad_times:
                idxs = np.logical_and(telem.times.value >= CxoTime(left).secs,
                                      telem.times.value <= CxoTime(right).secs)
                mask[idxs] = False
        if msid == "fptemp_11" and mask_radzones:
            rad_zones = events.rad_zones.filter(start=telem.dates[0],
                                                stop=telem.dates[-1])
            for rz in rad_zones:
                idxs = np.logical_and(telem.times.value >= rz.tstart,
                                      telem.times.value <= rz.tstop)
                mask[idxs] = False
        if mask_fmt1:
            which = self["msids", "ccsdstmf"] == "FMT1"
            mask[which] = False
        times = telem.times.value[mask]
        if yplotlimits is None:
            ymin = min(telem.value[mask].min(), pred.value[mask].min())-2
            ymax = min(telem.value[mask].max(), pred.value[mask].max())+2
            yplotlimits = [ymin, ymax]
        if errorplotlimits is None:
            errorplotlimits = [-5, 5]
        mylimits = {"units": "C"}
        if plot_limits:
            if msid == "fptemp_11":
                mylimits["acisi_limit"] = -112.0
                mylimits["aciss_limit"] = -111.0
                mylimits["fp_sens_limit"] = -118.7
            else:
                mylimits["caution_high"] = limits[msid]+margins[msid]
                mylimits["planning_limit"] = limits[msid]
        dash.dashboard(pred.value[mask], telem.value[mask], times, mylimits,
                       msid=msid, modelname=full_name.get(msid, msid),
                       errorplotlimits=errorplotlimits, yplotlimits=yplotlimits,
                       fig=fig, savefig=False)
        if figfile is not None:
            fig.savefig(figfile)
        return fig


class ThermalModelFromRun(ModelDataset):
    """
    Fetch multiple temperature models and their associated commanded states
    from ASCII table files generated by xija or model check tools. If MSID
    data will be added, it will be interpolated to the times of the model
    data.

    Parameters
    ----------
    loc : string or list of strings
        Path to the directory where the model and state data are stored.
    get_msids : boolean, optional
        Whether or not to load the MSIDs corresponding to the
        temperature models for the same time period from the
        engineering archive. Default: False.
    tl_file : string
        Path to the location of the tracelog file to get the MSID data from.
        Default: None, which means the engineering archive will be queried
        if get_msids=True.
    Examples
    --------
    >>> from acispy import ThermalModelFromRun
    >>> ds = ThermalModelFromRun("/data/acis/LoadReviews/2019/MAY2019/ofls/out_dpa",
    ...                          get_msids=True)
    """
    def __init__(self, loc, get_msids=False, tl_file=None):
        loc = Path(loc)
        temp_file = loc / "temperatures.dat"
        state_file = loc / "states.dat"
        esa_file = loc / "earth_solid_angle.dat"
        if not state_file.exists():
            state_file = None
        if not esa_file.exists():
            esa_file = None
        model = Model.from_load_file(temp_file, esa_file=esa_file)
        comps = list(model.keys())
        if state_file is not None:
            states = States.from_load_file(state_file)
        else:
            states = EmptyTimeSeries()
        if get_msids:
            msids = self._get_msids(model, comps, tl_file)
        else:
            msids = EmptyTimeSeries()
        super(ThermalModelFromRun, self).__init__(msids, states, model)


class ThermalModelFromLoad(ModelDataset):
    """
    Fetch a temperature model and its associated commanded states
    from a load review. Optionally get MSIDs for the same time period.
    If MSID data will be added, it will be interpolated to the times
    of the model data.

    Parameters
    ----------
    load : string
        The load review to get the model from, i.e. "JAN2516A".
    comps : list of strings, optional
        List of temperature components to get from the load models. If
        not specified all four components will be loaded.
    get_msids : boolean, optional
        Whether or not to load the MSIDs corresponding to the
        temperature models for the same time period from the
        engineering archive. Default: False.
    states_comp : string, optional
        The thermal model page to use to get the states. "DEA", "DPA",
        "PSMC", or "FP". Default: "DPA"

    Examples
    --------
    >>> from acispy import ThermalModelFromLoad
    >>> comps = ["1deamzt", "1pdeaat", "fptemp_11"]
    >>> ds = ThermalModelFromLoad("APR0416C", comps, get_msids=True)
    """
    def __init__(self, load, comps=None, get_msids=False,
                 tl_file=None, states_comp="DPA"):
        if comps is None:
            comps = ["1deamzt", "1dpamzt", "1pdeaat", "fptemp_11",
                     "tmp_fep1_mong", "tmp_fep1_actel", "tmp_bep_pcb"]
        comps = ensure_list(comps)
        model = Model.from_load_page(load, comps)
        states = States.from_load_page(load, comp=states_comp)
        if get_msids:
            msids = self._get_msids(model, comps, tl_file)
        else:
            msids = EmptyTimeSeries()
        super(ThermalModelFromLoad, self).__init__(msids, states, model)


class ThermalModelRunner(ModelDataset):
    """
    Class for running Xija thermal models.

    Parameters
    ----------
    name : string
        The name of the MSID to simulate, e.g. "1dpamzt"
    tstart : string
        The start time in YYYY:DOY:HH:MM:SS format.
    tstop : string
        The stop time in YYYY:DOY:HH:MM:SS format.
    states : dict, optional
        A dictionary of modeled commanded states required for the model. The
        states can either be a constant value or NumPy arrays. If not supplied,
        the thermal model will be run with states from the commanded states
        database.
    T_init : float, optional
        The initial temperature for the thermal model run. If None,
        an initial temperature will be determined from telemetry.
        Default: None
    other_init : dict, optional
        A dictionary of names of nodes (such as pseudo-nodes) and initial
        values, which can be supplied to initialize these nodes for the
        start of the model run. Default: None
    get_msids : boolean, optional
        Whether or not to pull data from the engineering archive. 
        Default: False
    dt : float, optional
        The timestep to use for this run. Default is 328 seconds or is provided
        by the model specification file.
    model_spec : string, optional
        Path to the model spec JSON file for the model. Default: None, the 
        standard model path will be used.
    mask_bad_times : boolean, optional
        If set, bad times from the data are included in the array masks
        and plots. Default: False
    ephem_file : string, optional
        An AstroPy ASCII table containing a custom ephemeris. Must have
        the following columns:
        times: CXC seconds
        orbitephem0_x: Chandra orbit ephemeris x-component in units of m
        orbitephem0_y: Chandra orbit ephemeris y-component in units of m
        orbitephem0_z: Chandra orbit ephemeris z-component in units of m
        solarephem0_x: Solar orbit ephemeris x-component in units of m
        solarephem0_y: Solar orbit ephemeris y-component in units of m
        solarephem0_z: Solar orbit ephemeris z-component in units of m
        Default : None, which means the ephemeris will be taken from the
        cheta archive. 
    evolve_method : integer, optional
        Whether to use the old xija core solver (1) or the new one (2).
        Default: None, which defaults to the value in the model spec
        file.
    rk4 : integer, optional
        Whether to use 4th-order Runge-Kutta (1) instead of 2nd order (0). 
        Only works with evolve_method=2. Default: None, which defaults 
        to the value in the model spec file.
    tl_file : string, optional
        The path to a tracelog file which will supply MSID information
        if ``use_msids=True``. Default: None
    compute_model_supp : callable, optional
        A function which takes the model name, tstart, tstop,
        and a XijaModel object, and allows the user to 
        perform custom operations on the model.

    Examples
    --------
    >>> states = {"ccd_count": np.array([5, 6, 1]),
    ...           "pitch": np.array([150.0] * 3),
    ...           "fep_count": np.array([5, 6, 1]),
    ...           "clocking": np.array([1] * 3),
    ...           "vid_board": np.array([1] * 3),
    ...           "off_nom_roll": np.array([0.0] * 3),
    ...           "simpos": np.array([-99616.0] * 3),
    ...           "datestart": np.array(["2015:002:00:00:00", "2015:002:12:00:00", "2015:003:12:00:00"]),
    ...           "datestop": np.array(["2015:002:12:00:00", "2015:003:12:00:00", "2015:005:00:00:00"])}
    >>> dpa_model = ThermalModelRunner("1dpamzt", "2015:002:00:00:00",
    ...                                "2015:005:00:00:00", states=states,
    ...                                T_init=10.1)
    """
    def __init__(self, name, tstart, tstop, states=None, T_init=None,
                 other_init=None, get_msids=False, dt=328.0, model_spec=None,
                 mask_bad_times=False, ephem_file=None, evolve_method=None,
                 rk4=None, tl_file=None, compute_model_supp=None):

        self.name = name.lower()
        self.sname = short_name.get(name, name)
        if self.name in acis_models:
            self.model_check = importlib.import_module(f"{self.sname}_check")
        else:
            self.model_check = None

        self.model_spec = find_json(name, model_spec)

        self.ephem_file = ephem_file
 
        self.compute_model_supp = compute_model_supp

        tstart = CxoTime(tstart).date
        tstop = CxoTime(tstop).date

        tstart_secs = CxoTime(tstart).secs
        tstop_secs = CxoTime(tstop).secs

        self.datestart = tstart
        self.datestop = tstop
        self.tstart = Quantity(tstart_secs, "s")
        self.tstop = Quantity(tstop_secs, "s")

        last_ecl_time = fetch.get_time_range("aoeclips", format='secs')[1]
        self.no_eclipse = tstop_secs > last_ecl_time
        self.no_earth_heat = getattr(self, "no_earth_heat", False)

        if states is not None:
            if isinstance(states, States):
                states = states.as_array()
            elif isinstance(states, dict):
                if "tstart" not in states:
                    states["tstart"] = CxoTime(states["datestart"]).secs
                if "tstop" not in states:
                    states["tstop"] = CxoTime(states["datestop"]).secs
                num_states = states["tstart"].size
                if "letg" not in states:
                    states["letg"] = np.array(["RETR"] * num_states)
                if "hetg" not in states:
                    states["hetg"] = np.array(["RETR"] * num_states)

        if T_init is None:
            last_tlm_date = fetch.get_time_range(self.name, format='secs')[1]
            if tstart_secs+700.0 > last_tlm_date:
                raise RuntimeError(f"T_init=None, but the start time of {tstart} "
                                   "is ahead of the last time in telemetry. "
                                   "Please specify T_init or choose a different "
                                   "time.")
            T_init = fetch.MSID(self.name, tstart_secs-700., tstart_secs).vals[-1]

        self.T_init = Quantity(T_init, "deg_C")

        if self.name in acis_models and states is not None:
            self.xija_model = self._compute_acis_model(self.name, tstart, tstop,
                                                       states, dt, T_init, 
                                                       rk4=rk4, other_init=other_init,
                                                       evolve_method=evolve_method)
        else:
            self.xija_model = self._compute_model(name, tstart, tstop, dt, T_init,
                                                  states, other_init=other_init,
                                                  evolve_method=evolve_method, 
                                                  rk4=rk4)

        if states is None:
            states = self.xija_model.cmd_states
        states_obj = States(states)

        self.bad_times = getattr(self.xija_model, "bad_times", None)
        self.bad_times_indices = getattr(self.xija_model, "bad_times_indices", None)

        if isinstance(states, dict):
            states.pop("dh_heater", None)

        components = [self.name]
        if 'dpa_power' in self.xija_model.comp:
            components.append('dpa_power')
        if 'earthheat__fptemp' in self.xija_model.comp:
            components.append('earthheat__fptemp')
        if states is None:
            for c in ["pitch", "roll", "fep_count", "vid_board", "clocking",
                      "ccd_count", "sim_z"]:
                if c in self.xija_model.comp:
                    components.append(c)

        masks = {}
        if mask_bad_times and self.bad_times is not None:
            masks[self.name] = np.ones(self.xija_model.times.shape, dtype='bool')
            for (left, right) in self.bad_times_indices:
                masks[self.name][left:right] = False

        model_obj = Model.from_xija(self.xija_model, components, masks=masks)

        if get_msids:
            msids_obj = self._get_msids(model_obj, [self.name], tl_file)
        else:
            msids_obj = EmptyTimeSeries()
        super(ThermalModelRunner, self).__init__(msids_obj, states_obj, model_obj)

    def _get_ephemeris(self, tstart, tstop, times):
        msids = [f"orbitephem0_{axis}" for axis in "xyz"]
        msids += [f"solarephem0_{axis}" for axis in "xyz"]
        ephem = {}
        if self.ephem_file is None:
            e = fetch.MSIDset(msids, tstart - 2000.0, tstop + 2000.0)
            for msid in msids:
                ephem[msid] = Ska.Numpy.interpolate(e[msid].vals, e[msid].times,
                                                    times)
        else:
            e = ascii.read(self.ephem_file)
            idxs = np.logical_and(e["times"] >= tstart - 2000.0,
                                  e["times"] <= tstop + 2000.0)
            for msid in msids:
                ephem[msid] = Ska.Numpy.interpolate(e[msid][idxs],
                                                    e["times"][idxs], times)
        return ephem

    def _compute_model(self, name, tstart, tstop, dt, T_init, states,
                       other_init=None, evolve_method=None, rk4=None):
        if name == "fptemp_11":
            name = "fptemp"
        model = xija.XijaModel(name, start=tstart, stop=tstop, dt=dt,
                               model_spec=self.model_spec,
                               evolve_method=evolve_method, rk4=rk4)
        model.comp[name].set_data(T_init)
        for t in ["dea0", "dpa0"]:
            if t in model.comp:
                model.comp[t].set_data(T_init)
        if other_init is not None:
            for k, v in other_init.items():
                model.comp[k].set_data(v)
        if states is not None:
            if isinstance(states, np.ndarray):
                state_names = states.dtype.names
            else:
                state_names = list(states.keys())
            state_times = CxoTime(
                np.array([states["datestart"], states["datestop"]])).secs
            for k in state_names:
                if k in model.comp:
                    model.comp[k].set_data(states[k], state_times)
        if self.no_eclipse:
            model.comp["eclipse"].set_data(False)
        if self.compute_model_supp is not None:
            self.compute_model_supp(name, tstart, tstop, model)
        model.make()
        model.calc()
        return model

    def _compute_acis_model(self, name, tstart, tstop, states, dt, T_init,
                            other_init=None, evolve_method=None, rk4=None):
        import re
        from acis_thermal_check import calc_pitch_roll
        check_obj = getattr(self.model_check, model_classes[self.sname])()
        if name == "fptemp_11":
            name = "fptemp"
        model = xija.XijaModel(name, start=tstart, stop=tstop, dt=dt, 
                               model_spec=self.model_spec, rk4=rk4,
                               evolve_method=evolve_method)
        ephem = self._get_ephemeris(model.tstart, model.tstop, model.times)
        if states is None:
            state_times = model.times
            state_names = ["ccd_count", "fep_count", "vid_board", 
                           "clocking", "pitch", "roll"]
            if 'aoattqt1' in model.comp:
                state_names += ["q1", "q2", "q3", "q4"]
            states = {}
            pattern = re.compile("q[1-4]")
            for n in state_names:
                nstate = n
                ncomp = n
                if pattern.match(n):
                    ncomp = f'aoattqt{n[-1]}'
                elif name == "roll":
                    nstate = "off_nom_roll"
                states[nstate] = np.array(model.comp[ncomp].dvals)
        else:
            if isinstance(states, np.ndarray):
                state_names = states.dtype.names
            else:
                state_names = list(states.keys())
            state_times = np.array([states["tstart"], states["tstop"]])
            model.comp['sim_z'].set_data(np.array(states['simpos']), state_times)
            if 'pitch' in state_names:
                model.comp['pitch'].set_data(np.array(states['pitch']), state_times)
            else:
                pitch, roll = calc_pitch_roll(model.times, ephem, states)
                model.comp['pitch'].set_data(pitch, model.times)
                model.comp['roll'].set_data(roll, model.times)
            for st in ('ccd_count', 'fep_count', 'vid_board', 'clocking'):
                model.comp[st].set_data(np.array(states[st]), state_times)
            if 'dh_heater' in model.comp:
                dhh = states["dh_heater"] if "dh_heater" in state_names else 0
                model.comp['dh_heater'].set_data(dhh, state_times)
            if "off_nom_roll" in state_names:
                roll = np.array(states["off_nom_roll"])
                model.comp["roll"].set_data(roll, state_times)
        if 'dpa_power' in model.comp:
            # This is just a hack, we're not
            # really setting the power to zero.
            # But this value has no effect on
            # model evolution.
            model.comp['dpa_power'].set_data(0.0)
        model.comp[name].set_data(T_init)
        if self.no_eclipse:
            model.comp["eclipse"].set_data(False)
        check_obj._calc_model_supp(model, state_times, states, ephem, None)
        if self.name == "fptemp_11" and self.no_earth_heat:
            model.comp["earthheat__fptemp"].k = 0.0
        if other_init is not None:
            for k, v in other_init.items():
                model.comp[k] = v
        if self.compute_model_supp is not None:
            self.compute_model_supp(name, tstart, tstop, model)
        model.make()
        model.calc()
        return model

    @classmethod
    def from_states_file(cls, name, states_file, **kwargs):
        """
        Run a xija thermal model using a states.dat file.

        Parameters
        ----------
        name : string
            The name of the MSID to simulate, e.g. 
            "1dpamzt"
        states_file : string
            A file containing commanded states, in the same 
            format as "states.dat" which is outputted by ACIS 
            thermal model runs for loads.

        All other keyword arguments which are passed to the main
        :class:`~acispy.thermal_models.ThermalModelRunner`
        constructor can be passed to this method as well.
        """
        states = States.from_load_file(states_file)
        tstart = CxoTime(states['tstart'].value[0]).date
        tstop = CxoTime(states['tstop'].value[-1]).date
        return cls(name, tstart, tstop, states=states, **kwargs)

    @classmethod
    def from_commands(cls, name, cmds, **kwargs):
        """

        Parameters
        ----------
        name : string
            The name of the MSID to simulate, e.g. "1dpamzt"
        cmds : list of commands or CommandTable 
            The commands from which to derive states. 

        All other keyword arguments which are passed to the main
        :class:`~acispy.thermal_models.ThermalModelRunner`
        constructor can be passed to this method as well.
        """
        if not isinstance(cmds, commands.CommandTable):
            cmds = commands.CommandTable(cmds)
        states = States.from_commands(cmds)
        return cls(name, states["datestart"][0], states["datestop"][-1],
                   states=states, **kwargs)

    @classmethod
    def from_backstop(cls, name, backstop_file, days=3, T_init=None, 
                      other_cmds=None, **kwargs):
        """
        Run a thermal model using states derived from a backstop
        file. Continuity with previous states will be automatically 
        handled. 

        Parameters
        ----------
        name : string
            The name of the MSID to simulate, e.g. "1dpamzt"
        backstop_file : string
            The path to the backstop file. 
        days : float
        T_init : float, optional
            The initial temperature for the thermal model run. If None,
            an initial temperature will be determined from telemetry.
            Default: None
        other_cmds : list of commands or CommandTable
            Other commands to be included in the list. 

        All other keyword arguments which are passed to the main
        :class:`~acispy.thermal_models.ThermalModelRunner`
        constructor can be passed to this method as well.
        """
        bs_cmds = commands.get_cmds_from_backstop(backstop_file)
        bs_dates = bs_cmds["date"]
        bs_cmds['time'] = CxoTime(bs_cmds['date']).secs
        last_tlm_date = fetch.get_time_range(name, format='date')[1]
        last_tlm_time = CxoTime(last_tlm_date).secs
        tstart = min(last_tlm_time-3600.0, bs_cmds['time'][0]-days*86400.)
        if T_init is None:
            T_init = fetch.MSID(name, tstart).vals[-1]
        ok = bs_cmds['event_type'] == 'RUNNING_LOAD_TERMINATION_TIME'
        if np.any(ok):
            rltt = CxoTime(bs_dates[ok][0])
        else:
            # Handle the case of old loads (prior to backstop 6.9) where there
            # is no RLTT. If the first command is AOACRSTD this indicates the
            # beginning of a maneuver ATS which may overlap by 3 mins with the
            # previous loads because of the AOACRSTD command. So move the RLTT
            # forward by 3 minutes (exactly 180.0 sec). If the first command is
            # not AOACRSTD then that command time is used as RLTT.
            if bs_cmds['tlmsid'][0] == 'AOACRSTD':
                rltt = CxoTime(bs_cmds['time'][0] + 180)
            else:
                rltt = CxoTime(bs_cmds['date'][0])

        # Get non-backstop commands for continuity
        cmds = commands.get_cmds(tstart, rltt, inclusive_stop=True)
        # Add backstop commands
        cmds = cmds.add_cmds(bs_cmds)

        if other_cmds is not None:
            if not isinstance(other_cmds, commands.CommandTable):
                other_cmds = commands.CommandTable(other_cmds)
            cmds = cmds.add_cmds(other_cmds)

        return cls.from_commands(name, cmds, T_init=T_init, **kwargs)

    def make_solarheat_plot(self, node, figfile=None, fig=None):
        """
        Make a plot which shows the solar heat value vs. pitch.

        Parameters
        ----------
        node : string
            The xija node which has the solar heating applied to it
            in the model. Can be an real node on the spacecraft like
            1DEAMZT or a pseudo-node like "dpa0" in the 1DPAMZT model.
        figfile : string, optional
            The file to write the solar heating plot to. One will be created
            if not provided.
        fig : :class:`~matplotlib.figure.Figure`, optional
            A Figure instance to plot in. Default: None, one will be
            created if not provided.
        """
        if fig is None:
            fig, ax = plt.subplots(figsize=(15, 10))
        else:
            ax = fig.add_subplot(111)
        try:
            comp = self.xija_model.comp[f"solarheat__{node}"]
        except KeyError:
            raise KeyError(f"{node} does not have a SolarHeat component!")
        comp.plot_solar_heat__pitch(fig, ax)
        ax.set_xlabel("Pitch (deg)", fontsize=18)
        ax.set_ylabel("SolarHeat", fontsize=18)
        ax.lines[1].set_label("P")
        ax.lines[2].set_label("P+dP")
        ax.legend(fontsize=18)
        ax.tick_params(width=2, length=6)
        for axis in ['top', 'bottom', 'left', 'right']:
            ax.spines[axis].set_linewidth(2)
        fontProperties = font_manager.FontProperties(size=18)
        for label in ax.get_xticklabels():
            label.set_fontproperties(fontProperties)
        for label in ax.get_yticklabels():
            label.set_fontproperties(fontProperties)
        ax.title.set_fontsize(18)
        if figfile is not None:
            fig.savefig(figfile)
        return fig

    def make_power_plot(self, figfile=None, fig=None, use_ccd_count=False):
        """
        Make a plot which shows the ACIS state power coefficients, 
        vs. either FEP or CCD count.

        Parameters
        ----------
        figfile : string, optional
            The file to write the power coefficient plot to.
            One will be created if not provided.
        fig : :class:`~matplotlib.figure.Figure`, optional
            A Figure instance to plot in. Default: None, one 
            will be created if not provided.
        use_ccd_count : boolean, optional
            If True, plot the CCD count on the x-axis. Primarily 
            useful for the 1DEAMZT model. Default: False
        """
        if fig is None:
            fig, ax = plt.subplots(figsize=(10, 10))
        else:
            ax = fig.add_subplot(111)
        xm = self.xija_model
        dtype = [('x', 'int'), ('y', 'float'), ('name', '<U32')]
        clocking = []
        not_clocking = []
        either = []
        for i, parname in enumerate(xm.parnames):
            name = parname.split("__")[-1]
            if name.startswith("pow"):
                coeff = name.split("_")[-1]
                if use_ccd_count:
                    count = int(coeff[1])
                else:
                    count = int(coeff[0])
                if name.endswith("x"):
                    either.append((count, xm.parvals[i], coeff))
                elif name.endswith("1"):
                    clocking.append((count, xm.parvals[i], coeff))
                elif name.endswith("0"):
                    not_clocking.append((count, xm.parvals[i], coeff))
        clocking = np.array(clocking, dtype=dtype)
        not_clocking = np.array(not_clocking, dtype=dtype)
        either = np.array(either, dtype=dtype)
        ax.scatter(clocking["x"], clocking["y"], label="Clocking", s=40,
                   color="C0")
        for i, txt in enumerate(clocking["name"]):
            ax.text(clocking["x"][i] + 0.25, clocking["y"][i], txt, color="C0",
                    fontsize=18)
        ax.scatter(not_clocking["x"], not_clocking["y"], label="Not Clocking",
                   s=40, color="C1")
        for i, txt in enumerate(not_clocking["name"]):
            ax.text(not_clocking["x"][i] + 0.25, not_clocking["y"][i], txt, 
                    color="C1", fontsize=18)
        ax.scatter(either["x"], either["y"], label="Either", s=40, color="C2")
        for i, txt in enumerate(either["name"]):
            ax.text(either["x"][i] + 0.25, either["y"][i], txt, color="C2", 
                    fontsize=18)
        ax.tick_params(width=2, length=6)
        ax.set_xlabel("{} Count".format("CCD" if use_ccd_count else "FEP"), fontsize=18)
        ax.set_ylabel("Coefficient Value", fontsize=18)
        ax.set_xticks(np.arange(7))
        ax.set_xlim(-0.25, 7.0)
        ax.legend(fontsize=18)
        for axis in ['top', 'bottom', 'left', 'right']:
            ax.spines[axis].set_linewidth(2)
        fontProperties = font_manager.FontProperties(size=18)
        for label in ax.get_xticklabels():
            label.set_fontproperties(fontProperties)
        for label in ax.get_yticklabels():
            label.set_fontproperties(fontProperties)
        if figfile is not None:
            fig.savefig(figfile)
        return fig


def find_text_time(time, hours=1.0):
    return CxoTime(CxoTime(time).secs+hours*3600.0).date


def make_default_states():
    return {
        "ccd_count": np.array([0], dtype='int'),
        "fep_count": np.array([0], dtype='int'),
        "clocking": np.array([0], dtype='int'),
        "vid_board": np.array([0], dtype='int'),
        "pitch": np.array([90.0]),
        "simpos": np.array([-99616.0]),
        "hetg": np.array(["RETR"]),
        "letg": np.array(["RETR"]),
        "off_nom_roll": np.array([0.0]),
        "dh_heater": np.array([0], dtype='int'),
        "targ_q1": np.array([1.0]),
        "targ_q2": np.array([0.0]),
        "targ_q3": np.array([0.0]),
        "targ_q4": np.array([0.0]),
        "q1": np.array([1.0]),
        "q2": np.array([0.0]),
        "q3": np.array([0.0]),
        "q4": np.array([0.0])
    }


class SimulateSingleState(ThermalModelRunner):
    """
    Class for simulating thermal models under constant conditions.

    Parameters
    ----------
    name : string
        The name of the model to simulate. 
    tstart : string or float
        The start time of the single-state run.
    tstop : string or float
        The stop time of the single-state run.
    states : dict
        A dictionary of modeled commanded states required for the single-state
        run. All states must be single values. Any particular states which are
        not included in this dict will be filled in using the "default" states,
        which assume zero ACIS CCDs and FEPs, normal Sun, zero off-nominal roll,
        HRC-S sim position, and no gratings inserted.
    T_init : float
        The starting temperature for the model in degrees C or F.
    model_spec : string, optional
        Path to the model spec JSON file for the model. Default: None, the
        standard model path will be used.
    dt : float, optional
        The timestep to use for this run. Default is 328 seconds or is provided
        by the model specification file.
    evolve_method : integer, optional
        Whether to use the old xija core solver (1) or the new one (2).
        Default: None, which defaults to the value in the model spec
        file.
    rk4 : integer, optional
        Whether to use 4th-order Runge-Kutta (1) instead of 2nd order (0). 
        Only works with evolve_method=2. Default: None, which defaults 
        to the value in the model spec file.
    no_earth_heat : boolean, optional
        Ignore the effect of earthshine in the ACIS radiator field of view.
        This really only might be useful for the ACIS focal plane 
        temperature model. Default: False
    other_init : dict, optional
        A dictionary of names of nodes (such as pseudo-nodes) and initial
        values, which can be supplied to initialize these nodes for the
        start of the model run. Default: None
    compute_model_supp : callable, optional
        A function which takes the model name, tstart, tstop,
        and a XijaModel object, and allows the user to 
        perform custom operations on the model.

    Examples
    --------
    >>> states = {"pitch": 75.0, "off_nom_roll": -6.0, "clocking": 1,
    ...           "ccd_count": 6, "dh_heater": 1, "simpos": 75624.0,}
    >>> dea_run = SimulateSingleState("1deamzt", "2016:201:05:12:03",
    ...                               "2016:202:05:12:03", states, 15.0)
    """
    def __init__(self, name, tstart, tstop, states, T_init, model_spec=None,
                 dt=328.0, evolve_method=None, rk4=None, no_earth_heat=False,
                 other_init=None, compute_model_supp=None):

        _states = make_default_states()
        if "ccd_count" in states and "fep_count" not in states:
            states["fep_count"] = states["ccd_count"]
        if "fep_count" in states and "ccd_count" not in states:
            states["ccd_count"] = states["fep_count"]
        for k in list(states.keys()):
            if k in _states:
                _states[k][0] = states[k]
            else:
                raise KeyError(f"You input a state ('{k}') which does not exist!")
        if name in short_name_rev:
            name = short_name_rev[name]
        tstart = CxoTime(tstart).secs
        datestart = CxoTime(tstart).date
        tstop = CxoTime(tstop).secs
        datestop = CxoTime(tstop).date
        _states["datestart"] = np.array([datestart])
        _states["datestop"] = np.array([datestop])
        _states["tstart"] = np.array([tstart])
        _states["tstop"] = np.array([tstop])
        self.no_earth_heat = no_earth_heat
        super().__init__(name, datestart, datestop, states=_states, 
                         T_init=T_init, dt=dt, evolve_method=evolve_method, 
                         rk4=rk4, model_spec=model_spec, get_msids=False,
                         other_init=other_init, 
                         compute_model_supp=compute_model_supp)

    def write_msids(self, filename, fields, mask_field=None, overwrite=False):
        raise NotImplementedError

    def write_states(self, states_file, overwrite=False):
        raise NotImplementedError

    def make_dashboard_plots(self, yplotlimits=None, errorplotlimits=None, fig=None):
        raise NotImplementedError

    def write_model_and_data(self, filename, overwrite=False):
        raise NotImplementedError


class SimulateECSRun(ThermalModelRunner):
    """
    Class for simulating thermal models for ECS measurements.

    name : string
        The msid of the model to simulate.
    tstart : string or float
        The start time of the single-state run.
    hours : integer or float
        The length of the ECS measurement in hours. NOTE that the
        actual length of the ECS run is hours + 10 ks + 12 s, as
        per the ECS CAP.
    T_init : float
        The starting temperature for the model in degrees C.
    pitch : float
        The pitch at which to run the model in degrees. If `vehicle_load`
        is not None, then this parameter will be ignored. 
    ccd_count : integer
        The number of CCDs to clock.
    vehicle_load : string, optional
        If a vehicle load is running, specify it here, e.g. "SEP0917C".
        Default: None, meaning no vehicle load. If this parameter is set,
        the input values of pitch and off-nominal roll will be ignored
        and the values from the vehicle load will be used.
    off_nom_roll : float, optional
        The off-nominal roll in degrees for the model. If `vehicle_load`
        is not None, then this parameter will be ignored. Default: 0.0
    dh_heater: integer, optional
        Flag to set whether (1) or not (0) the detector housing heater is on.
        Default: 0
    dt : float, optional
        The timestep to use for this run. Default is 328 seconds or is provided
        by the model specification file.
    evolve_method : integer, optional
        Whether to use the old xija core solver (1) or the new one (2).
        Default: None, which defaults to the value in the model spec
        file.
    rk4 : integer, optional
        Whether to use 4th-order Runge-Kutta (1) instead of 2nd order (0). 
        Only works with evolve_method=2. Default: None, which defaults 
        to the value in the model spec file.
    model_spec : string, optional
        Path to the model spec JSON file for the model. Default: None, the
        standard model path will be used.
    no_earth_heat : boolean, optional
        Ignore the effect of earthshine in the ACIS radiator field of view.
        This really only might be useful for the ACIS focal plane 
        temperature model. Default: False
    other_init : dict, optional
        A dictionary of names of nodes (such as pseudo-nodes) and initial
        values, which can be supplied to initialize these nodes for the
        start of the model run. Default: None
    compute_model_supp : callable, optional
        A function which takes the model name, tstart, tstop,
        and a XijaModel object, and allows the user to 
        perform custom operations on the model.

    Examples
    --------
    >>> dea_run = SimulateECSRun("1deamzt", "2016:201:05:12:03", 24, 14.0,
    ...                          150., 5, off_nom_roll=-6.0, dh_heater=1)
    """
    def __init__(self, name, tstart, hours, T_init, pitch, ccd_count,
                 vehicle_load=None, off_nom_roll=0.0, dh_heater=0,
                 dt=328.0, evolve_method=None, rk4=None, 
                 model_spec=None, no_earth_heat=False,
                 other_init=None, compute_model_supp=None):
        tstart = CxoTime(tstart).secs
        tend = tstart+hours*3600.0+10012.0
        tstop = tend+0.5*(tend-tstart)
        datestart = CxoTime(tstart).date
        datestop = CxoTime(tstop).date
        self.vehicle_load = vehicle_load
        self.hours = hours
        self.no_earth_heat = no_earth_heat
        if self.vehicle_load is not None:
            mylog.info(f"Modeling a {ccd_count}-chip state concurrent with "
                       f"the {self.vehicle_load} vehicle loads.")
            states = dict((k, state.value) for (k, state) in
                          States.from_load_page(self.vehicle_load).table.items())
            run_idxs = states["tstart"] < tstop
            states["ccd_count"][run_idxs] = ccd_count
            states["fep_count"][run_idxs] = ccd_count
            states["clocking"][run_idxs] = 1
            states["vid_board"][run_idxs] = 1
            states["simpos"][run_idxs] = -99616.0
            states["hetg"][run_idxs] = "RETR"
            states["letg"][run_idxs] = "RETR"
        else:
            states = {
                "ccd_count": np.array([ccd_count], dtype='int'),
                "fep_count": np.array([ccd_count], dtype='int'),
                "clocking": np.array([1], dtype='int'),
                "vid_board": np.array([1], dtype='int'),
                "pitch": np.array([pitch]),
                "simpos": np.array([-99616.0]),
                "datestart": np.array([datestart]),
                "datestop": np.array([datestop]),
                "tstart": np.array([tstart]),
                "tstop": np.array([tstop]),
                "hetg": np.array(["RETR"]),
                "letg": np.array(["RETR"]),
                "off_nom_roll": np.array([off_nom_roll]),
                "dh_heater": np.array([dh_heater], dtype='int')
            }
        super().__init__(name, tstart, tstop, states=states, T_init=T_init,
                         dt=dt, evolve_method=evolve_method, rk4=rk4, 
                         model_spec=model_spec, other_init=other_init,
                         compute_model_supp=compute_model_supp)

        mylog.info("Run Parameters")
        mylog.info("--------------")
        mylog.info(f"Start Datestring: {datestart}")
        mylog.info(f"Length of state in hours: {self.hours}")
        mylog.info(f"Stop Datestring: {datestop}")
        mylog.info(f"Initial Temperature: {T_init} degrees C")
        mylog.info(f"CCD/FEP Count: {ccd_count}")
        if self.vehicle_load is None:
            mylog.info(f"Pitch: {pitch}")
            mylog.info(f"Off-nominal Roll: {off_nom_roll}")
        dhh = {0: "OFF", 1: "ON"}[dh_heater]
        mylog.info(f"Detector Housing Heater: {dhh}")

        self.tend = tend
        self.dateend = CxoTime(tend).date

        mylog.info("Model Result")
        mylog.info("------------")

        limit = limits[self.name]
        margin = margins[self.name]
        if self.name in low_limits:
            self.low_limit = Quantity(low_limits[self.name], "deg_C")
        else:
            self.low_limit = None
        self.limit = Quantity(limit, "deg_C")
        self.margin = Quantity(margin, 'deg_C')
        self.limit_time = None
        self.limit_date = None
        self.duration = None
        self.violate = False
        self.hours = hours
        viols = self.mvals.value > self.limit.value
        if np.any(viols):
            idx = np.where(viols)[0][0]
            self.limit_time = self.times('model', self.name)[idx]
            self.limit_date = CxoTime(self.limit_time).date
            self.duration = Quantity((self.limit_time.value-tstart)*0.001, "ks")
            msg = f"The limit of {self.limit.value} degrees C will be reached at {self.limit_date}, "
            msg += f"after {self.duration.value} ksec."
            mylog.info(msg)
            if self.limit_time.value < self.tend:
                self.violate = True
                viol_time = "before"
            else:
                self.violate = False
                viol_time = "after"
            mylog.info(f"The limit is reached {viol_time} the end of the observation.")
        else:
            mylog.info(f"The limit of {self.limit.value} degrees C is never reached.")

        if self.violate:
            mylog.warning("This observation is NOT safe from a thermal perspective.")
        else:
            mylog.info("This observation is safe from a thermal perspective.")

    def _time_ticks(self, dp, ymax, fontsize):
        from matplotlib.ticker import AutoMinorLocator
        axt = dp.ax.twiny()
        mtimes = self.xija_model.times
        xmin, xmax = (plotdate2cxctime(dp.ax.get_xlim())-mtimes[0])*1.0e-3
        axt.plot((mtimes-mtimes[0])*1.0e-3, 
                 ymax*np.ones_like(mtimes))
        axt.set_xlim(xmin, xmax)
        axt.xaxis.set_minor_locator(AutoMinorLocator(5))
        axt.set_xlabel("Time (ks)", fontdict={"size": fontsize})
        fontProperties = font_manager.FontProperties(size=fontsize)
        for label in axt.get_xticklabels():
            label.set_fontproperties(fontProperties)
        for label in axt.get_yticklabels():
            label.set_fontproperties(fontProperties)
        axt.tick_params(which="major", width=2, length=6)
        axt.tick_params(which="minor", width=2, length=3)

    def plot_model(self, plot=None, fontsize=18, **kwargs):
        """
        Plot the simulated ECS run.

        Parameters
        ----------
        plot : :class:`~acispy.plots.DatePlot` or :class:`~acispy.plots.CustomDatePlot`, optional
            An existing DatePlot to add this plot to. Default: None, one 
            will be created if not provided.
        fontsize : integer, optional
            The font size for the labels in the plot. Default: 18 pt.
        """
        if self.vehicle_load is None:
            field2 = None
        else:
            field2 = "pitch"
        viol_text = "NOT SAFE" if self.violate else "SAFE"
        dp = DatePlot(self, [("model", self.name)], field2=field2, plot=plot,
                      fontsize=fontsize, **kwargs)
        dp.add_text(find_text_time(self.dateend, hours=4.0), self.T_init.value + 2.0,
                    viol_text, fontsize=22, color='black')
        dp.add_hline(self.limit.value, ls='-', lw=2, color='g')
        dp.add_hline(self.limit.value+self.margin.value, ls='-', lw=2, color='gold')
        if self.low_limit is not None:
            dp.add_hline(self.low_limit.value, ls='-', lw=2, color='g')
            dp.add_hline(self.low_limit.value - self.margin.value, ls='-', lw=2, color='gold')
        dp.add_vline(self.datestart, ls='--', lw=2, color='b')
        dp.add_text(find_text_time(self.datestart), self.limit.value - 2.0,
                    "START", color='blue', rotation="vertical")
        dp.add_vline(self.dateend, ls='--', lw=2, color='b')
        dp.add_text(find_text_time(self.dateend), self.limit.value - 12.0,
                    "END", color='blue', rotation="vertical")
        if self.limit_date is not None:
            dp.add_vline(self.limit_date, ls='--', lw=2, color='r')
            dp.add_text(find_text_time(self.limit_date), self.limit.value-2.0,
                        "VIOLATION", color='red', rotation="vertical")
        dp.set_xlim(find_text_time(self.datestart, hours=-1.0), self.datestop)
        if self.low_limit is not None:
            ymin = self.low_limit.value-self.margin.value
        else:
            ymin = self.T_init.value
        ymin = min(ymin, self.mvals.value.min())-2.0
        ymax = max(self.limit.value+self.margin.value, self.mvals.value.max())+3.0
        self._time_ticks(dp, ymax, fontsize)
        dp.set_ylim(ymin, ymax)
        return dp

    def get_temp_at_time(self, t):
        """
        Get the model temperature at a time *t* seconds
        past the beginning of the single-state run.
        """
        t += self.tstart.value
        return Quantity(np.interp(t, self['model', self.name].times.value,
                                  self['model', self.name].value), "deg_C")

    @property
    def mvals(self):
        return self['model', self.name]

    def write_msids(self, filename, fields, mask_field=None, overwrite=False):
        raise NotImplementedError

    def write_states(self, states_file, overwrite=False):
        raise NotImplementedError

    def make_dashboard_plots(self, yplotlimits=None, errorplotlimits=None, fig=None):
        raise NotImplementedError

    def write_model_and_data(self, filename, overwrite=False):
        raise NotImplementedError
