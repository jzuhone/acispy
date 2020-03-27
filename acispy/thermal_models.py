import xija
import os
from astropy.units import Quantity
from astropy.io import ascii
from acispy.dataset import Dataset
from acispy.plots import DatePlot
import numpy as np
from Chandra.Time import secs2date, DateTime, date2secs
from acispy.states import States
from acispy.model import Model
from acispy.msids import MSIDs
from acispy.time_series import EmptyTimeSeries
from acispy.utils import mylog, calc_off_nom_rolls, \
    get_time, ensure_list, default_states, KadiWrapper
import Ska.Numpy
import Ska.engarchive.fetch_sci as fetch
from chandra_models import get_xija_model_file
import matplotlib.pyplot as plt
from kadi import events

short_name = {"1deamzt": "dea",
              "1dpamzt": "dpa",
              "1pdeaat": "psmc",
              "fptemp_11": "acisfp",
              "tmp_fep1_mong": "fep1_mong",
              "tmp_fep1_actel": "fep1_actel",
              "tmp_bep_pcb": "bep_pcb"}

short_name_rev = {v: k for k, v in short_name.items()}

full_name = {"1deamzt": "DEA",
             "1dpamzt": "DPA",
             "1pdeaat": "PSMC",
             "fptemp_11": "Focal Plane",
             "tmp_fep1_mong": "FEP1 Mongoose",
             "tmp_fep1_actel": "FEP1 Actel",
             "tmp_bep_pcb": "BEP PCB"}

limits = {'1deamzt': 36.5,
          '1dpamzt': 37.5,
          '1pdeaat': 52.5,
          'tmp_fep1_mong': 43.0,
          'tmp_fep1_actel': 43.0,
          'tmp_bep_pcb': 43.0,
          'fptemp_11': {"ACIS-I": -112.0, "ACIS-S": -111.0}}

margins = {'1deamzt': 2.0,
           '1dpamzt': 2.0,
           '1pdeaat': 4.5,
           'tmp_fep1_mong': 2.0,
           'tmp_fep1_actel': 2.0,
           'tmp_bep_pcb': 2.0}


def find_json(name, model_spec):
    if model_spec is None:
        name = short_name[name]
        model_spec = get_xija_model_file(name)
    elif not os.path.exists(model_spec):
        raise IOError("The JSON file %s does not exist!" % model_spec)
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
        if os.path.exists(filename) and not overwrite:
            raise IOError("File %s already exists, but overwrite=False!" % filename)
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
                         "ccd_count", "fep_count", "off_nominal_roll"]
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
                out += [("msids", msid), ("model", "diff_%s" % msid)]
        msid = list(self.model.keys())[0]
        telem = self["msids", msid]
        mask = np.ones_like(telem.value, dtype='bool')
        if tstart is not None:
            tstart = DateTime(tstart).secs
            mask[telem.times.value < tstart] = False
        if tstop is not None:
            tstop = DateTime(tstop).secs
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
        tstart = secs2date(times[0] - 700.0)
        tstop = secs2date(times[-1] + 700.0)
        if tl_file is not None:
            msids = MSIDs.from_tracelog(tl_file, tbegin=tstart, tend=tstop)
        else:
            if "earth_solid_angle" in comps:
                comps.remove("earth_solid_angle")
            comps.append("ccsdstmf")
            msids = MSIDs.from_database(comps, tstart, tstop=tstop, filter_bad=True,
                                        interpolate=True, interpolate_times=times)
            if msids[comps[0]].times.size != times.size:
                raise RuntimeError("Lengths of time arrays for model data and MSIDs "
                                   "do not match. You probably ran a model past the "
                                   "end date in the engineering archive!")
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
            tstart = DateTime(tstart).secs
            mask[telem.times.value < tstart] = False
        if tstop is not None:
            tstop = DateTime(tstop).secs
            mask[telem.times.value > tstop] = False
        if bad_times is not None:
            for (left, right) in bad_times:
                idxs = np.logical_and(telem.times.value >= date2secs(left),
                                      telem.times.value <= date2secs(right))
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
            errorplotlimits = [-15, 15]
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
        temp_file = os.path.join(loc, "temperatures.dat")
        state_file = os.path.join(loc, "states.dat")
        esa_file = os.path.join(loc, "earth_solid_angle.dat")
        if not os.path.exists(state_file):
            state_file = None
        if not os.path.exists(esa_file):
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
        The name of the model to simulate. Can be "dea", "dpa", "psmc", or "fep1_mong".
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
    dt : float, optional
        The timestep to use for this run. Default is 328 seconds or is provided
        by the model specification file.
    model_spec : string, optional
        Path to the model spec JSON file for the model. Default: None, the 
        standard model path will be used.
    mask_bad_times : boolean, optional
        If set, bad times from the data are included in the array masks
        and plots. Default: False
    server : string 
         DBI server or HDF5 file. Only used if the commanded states database
         is used. Default: None

    Examples
    --------
    >>> states = {"ccd_count": np.array([5,6,1]),
    ...           "pitch": np.array([150.0]*3),
    ...           "fep_count": np.array([5,6,1]),
    ...           "clocking": np.array([1]*3),
    ...           "vid_board": np.array([1]*3),
    ...           "off_nominal_roll": np.array([0.0]*3),
    ...           "simpos": np.array([-99616.0]*3)}
    >>> dpa_model = ThermalModelRunner("dpa", "2015:002:00:00:00",
    ...                                "2016:005:00:00:00", states=states,
    ...                                T_init=10.1)
    """
    def __init__(self, name, tstart, tstop, states=None, T_init=None,
                 get_msids=True, dt=328.0, model_spec=None,
                 mask_bad_times=False, ephemeris=None,
                 tl_file=None, no_eclipse=False, compute_model=None):

        self.name = name.lower()

        tstart = get_time(tstart)
        tstop = get_time(tstop)

        tstart_secs = DateTime(tstart).secs
        tstop_secs = DateTime(tstop).secs

        if states is not None:
            if "tstart" not in states:
                states["tstart"] = DateTime(states["datestart"]).secs
                states["tstop"] = DateTime(states["datestop"]).secs
            num_states = states["tstart"].size
            if "letg" not in states:
                states["letg"] = np.array(["RETR"]*num_states)
            if "hetg" not in states:
                states["hetg"] = np.array(["RETR"]*num_states)
            states_obj = States(states)
        else:
            states_obj = EmptyTimeSeries()

        if T_init is None:
            T_init = fetch.MSID(self.name, tstart_secs-700., tstart_secs+700.).vals.mean()

        self.model_spec = find_json(self.name, model_spec)

        ephem_times, ephem_data = self._get_ephemeris(ephemeris, tstart_secs, tstop_secs)

        if compute_model is not None:
            self.xija_model = compute_model(self.name, tstart, tstop, states,
                                            dt, T_init, model_spec)
        elif self.name in short_name and states is not None:
            self.xija_model = self._compute_acis_model(self.name, tstart, tstop, states,
                                                       dt, T_init, ephem_times=ephem_times,
                                                       ephem_data=ephem_data,
                                                       no_eclipse=no_eclipse)
        else:
            self.xija_model = self._compute_model(self.name, tstart, tstop, dt, T_init)

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
            components += ["pitch", "roll", "fep_count", "vid_board", "clocking",
                           "ccd_count", "sim_z"]
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

    def _get_ephemeris(self, ephemeris, tstart, tstop):
        if ephemeris is None:
            return None, None
        ephem_data = ascii.read(ephemeris)
        msids = ['orbitephem0_{}'.format(axis) for axis in "xyz"]
        idxs = np.logical_and(ephem_data["times"] >= tstart - 2000.0,
                              ephem_data["times"] <= tstop + 2000.0)
        ephemeris = dict((k, ephem_data[k].data[idxs]) for k in msids)
        ephemeris_times = ephem_data["times"].data[idxs]
        return ephemeris_times, ephemeris

    def _compute_model(self, name, tstart, tstop, dt, T_init):
        if name == "fptemp_11":
            name = "fptemp"
        model = xija.XijaModel(name, start=tstart, stop=tstop, dt=dt, model_spec=self.model_spec)
        model.comp[name].set_data(T_init)
        for t in ["dea0","dpa0"]:
            if t in model.comp:
                model.comp[t].set_data(T_init)
        model.make()
        model.calc()
        return model

    def _compute_acis_model(self, name, tstart, tstop, states, dt, T_init,
                            ephem_times=None, ephem_data=None, no_eclipse=False):
        state_times = np.array([states["tstart"], states["tstop"]])
        if name == "fptemp_11":
            name = "fptemp"
        if isinstance(states, np.ndarray):
            state_names = states.dtype.names
        else:
            state_names = list(states.keys())
        if "off_nominal_roll" in state_names:
            roll = np.array(states["off_nominal_roll"])
        else:
            roll = calc_off_nom_rolls(states)
        model = xija.XijaModel(name, start=tstart, stop=tstop, dt=dt, model_spec=self.model_spec)
        model.comp[name].set_data(T_init)
        model.comp['sim_z'].set_data(np.array(states['simpos']), state_times)
        if no_eclipse:
            model.comp["eclipse"].set_data(False)
        if 'roll' in model.comp:
            model.comp['roll'].set_data(roll, state_times)
        if 'dpa_power' in model.comp:
            # This is just a hack, we're not
            # really setting the power to zero.
            model.comp['dpa_power'].set_data(0.0) 
        # This is for the PSMC model
        if 'pin1at' in model.comp:
            model.comp['pin1at'].set_data(T_init-10.)
        if 'dpa0' in model.comp:
            model.comp['dpa0'].set_data(T_init)
        if 'dea0' in model.comp:
            model.comp['dea0'].set_data(T_init)
        if 'dh_heater' in model.comp:
            model.comp['dh_heater'].set_data(states.get("dh_heater", 0), state_times)
        for st in ('ccd_count', 'fep_count', 'vid_board', 'clocking', 'pitch'):
            model.comp[st].set_data(np.array(states[st]), state_times)
        if name == "fptemp":
            for axis in "xyz":
                ephem = 'orbitephem0_{}'.format(axis)
                if ephem_times is None:
                    msid = fetch.Msid(ephem, model.tstart - 2000, model.tstop + 2000)
                    e_times = msid.times
                    e_data = msid.vals
                else:
                    e_times = ephem_times
                    e_data = ephem_data[ephem]
                model.comp[ephem].set_data(e_data, e_times)
            for i in range(1, 5):
                quat = 'aoattqt{}'.format(i)
                quat_name = 'q{}'.format(i)
                model.comp[quat].set_data(states[quat_name], state_times)
            model.comp['1cbat'].set_data(-53.0)
            model.comp['sim_px'].set_data(-120.0)

        model.make()
        model.calc()
        return model

    @classmethod
    def from_states_file(cls, name, states_file, T_init,
                         dt=328.0, model_spec=None, mask_bad_times=False, 
                         ephemeris=None, get_msids=True, no_eclipse=False):
        """
        Class for running Xija thermal models.

        Parameters
        ----------
        name : string
            The name of the model to simulate. Can be "dea", "dpa", "psmc", or "fep1mong".
        states_file : string
            A file containing commanded states, in the same format as "states.dat" which is
            outputted by ACIS thermal model runs for loads.
        T_init : float
            The starting temperature for the model in degrees C.
        model_spec : string, optional
            Path to the model spec JSON file for the model. Default: None, the
            standard model path will be used.
        mask_bad_times : boolean, optional
            If set, bad times from the data are included in the array masks
            and plots. Default: False
        """
        states = ascii.read(states_file)
        states_dict = dict((k, states[k]) for k in states.colnames)
        if "off_nominal_roll" not in states.colnames:
            states_dict["off_nominal_roll"] = calc_off_nom_rolls(states)
        tstart = get_time(states_dict['tstart'][0])
        tstop = get_time(states_dict['tstop'][-1])
        return cls(name, tstart, tstop, states=states_dict, T_init=T_init,
                   dt=dt, model_spec=model_spec, mask_bad_times=mask_bad_times,
                   ephemeris=ephemeris, get_msids=get_msids, no_eclipse=no_eclipse)

    @classmethod
    def from_database(cls, name, tstart, tstop, T_init, server=None, get_msids=True,
                      dt=328.0, model_spec=None, mask_bad_times=False,
                      ephemeris=None, no_eclipse=False, compute_model=None):
        from Chandra.cmd_states import fetch_states
        t = fetch_states(tstart, tstop, server=server)
        states = dict((k, t[k]) for k in t.dtype.names)
        states["off_nominal_roll"] = calc_off_nom_rolls(states)
        return cls(name, tstart, tstop, states=states, T_init=T_init, dt=dt,
                   model_spec=model_spec, mask_bad_times=mask_bad_times,
                   ephemeris=ephemeris, get_msids=get_msids, no_eclipse=no_eclipse,
                   compute_model=compute_model)

    @classmethod
    def from_commands(cls, name, tstart, tstop, cmds, T_init, get_msids=True,
                      dt=328.0, model_spec=None, mask_bad_times=False, 
                      ephemeris=None, no_eclipse=False, compute_model=None):
        tstart = get_time(tstart)
        tstop = get_time(tstop)
        t = States.from_commands(tstart, tstop, cmds)
        states = {k: t[k].value for k in t.keys()}
        return cls(name, tstart, tstop, states=states, T_init=T_init, dt=dt,
                   model_spec=model_spec, mask_bad_times=mask_bad_times,
                   ephemeris=ephemeris, get_msids=get_msids, no_eclipse=no_eclipse,
                   compute_model=compute_model)

    @classmethod
    def from_kadi(cls, name, tstart, tstop, T_init, get_msids=True, dt=328.0,
                  model_spec=None, mask_bad_times=False, ephemeris=None,
                  no_eclipse=False, compute_model=None):
        from kadi.commands import states as get_states
        tstart = get_time(tstart)
        tstop = get_time(tstop)
        t = get_states(tstart, tstop)
        states = {}
        for k in default_states:
            if k == "tstart":
                states[k] = date2secs(t["datestart"].data)
            elif k == "tstop":
                states[k] = date2secs(t["datestop"].data)
            elif k == "trans_keys":
                states[k] = np.array([",".join(d) for d in t["trans_keys"].data])
            else:
                states[k] = t[k].data
        return cls(name, tstart, tstop, states=states, T_init=T_init, dt=dt,
                   model_spec=model_spec, mask_bad_times=mask_bad_times,
                   ephemeris=ephemeris, get_msids=get_msids, no_eclipse=no_eclipse,
                   compute_model=compute_model)

    @classmethod
    def from_backstop(cls, name, backstop_file, T_init, model_spec=None, dt=328.0,
                      mask_bad_times=False, ephemeris=None, get_msids=True,
                      no_eclipse=False, compute_model=None):
        import Ska.ParseCM
        bs_cmds = Ska.ParseCM.read_backstop(backstop_file)
        tstart = bs_cmds[0]['time']
        tstop = bs_cmds[-1]['time']
        return cls.from_commands(name, tstart, tstop, bs_cmds, T_init, dt=dt,
                                 model_spec=model_spec, get_msids=get_msids,
                                 mask_bad_times=mask_bad_times, compute_model=compute_model,
                                 ephemeris=ephemeris, no_eclipse=no_eclipse)

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
            comp = self.xija_model.comp["solarheat__%s" % node]
        except KeyError:
            raise KeyError("%s does not have a SolarHeat component!" % node)
        comp.plot_solar_heat__pitch(fig, ax)
        if figfile is not None:
            fig.savefig(figfile)
        return fig

    def make_power_plot(self, figfile=None, fig=None, use_ccd_count=False):
        """
        Make a plot which shows the ACIS state power coefficients.

        Parameters
        ----------
        figfile : string, optional
            The file to write the power coefficient plot to. One will be created
            if not provided.
        fig : :class:`~matplotlib.figure.Figure`, optional
            A Figure instance to plot in. Default: None, one will be
            created if not provided.
        """
        plt.rc("font", size=18)
        plt.rc("axes", linewidth=2)
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
            ax.text(clocking["x"][i] + 0.25, clocking["y"][i], txt, color="C0")
        ax.scatter(not_clocking["x"], not_clocking["y"], label="Not Clocking", 
                   s=40, color="C1")
        for i, txt in enumerate(not_clocking["name"]):
            ax.text(not_clocking["x"][i] + 0.25, not_clocking["y"][i], txt, 
                    color="C1")
        ax.scatter(either["x"], either["y"], label="Either", s=40, color="C2")
        for i, txt in enumerate(either["name"]):
            ax.text(either["x"][i] + 0.25, either["y"][i], txt, color="C2")
        ax.tick_params(width=2, length=6)
        ax.set_xlabel("{} Count".format("CCD" if use_ccd_count else "FEP"))
        ax.set_ylabel("Coefficient Value")
        ax.set_xticks(np.arange(7))
        ax.set_xlim(-0.25, 7.0)
        ax.legend()
        if figfile is not None:
            fig.savefig(figfile)
        return fig


def find_text_time(time, hours=1.0):
    return secs2date(date2secs(time)+hours*3600.0)


class SimulateSingleObs(ThermalModelRunner):
    """
    Class for simulating thermal models during ECS runs under constant conditions.

    Parameters
    ----------
    name : string
        The name of the model to simulate. 
    tstart : string
        The start time of the ECS run in YYYY:DOY:HH:MM:SS format.
    tstop : string
        The stop time of the ECS run in YYYY:DOY:HH:MM:SS format.
    T_init : float
        The starting temperature for the model in degrees C.
    pitch : float
        The pitch at which to run the model in degrees. 
    ccd_count : integer
        The number of CCDs to clock.
    vehicle_load : string, optional
        If a vehicle load is running, specify it here, e.g. "SEP0917C".
        Default: None, meaning no vehicle load. If this parameter is set,
        the input values of pitch and off-nominal roll will be ignored
        and the values from the vehicle load will be used.
    simpos : float, optional
        The SIM position at which to run the model. Default: -99616.0
    off_nominal_roll : float, optional
        The off-nominal roll in degrees for the model. Default: 0.0
    dh_heater: integer, optional
        Flag to set whether (1) or not (0) the detector housing heater is on. 
        Default: 0
    ccd_count : integer, optional
        The number of FEPs which are on. Default: equal to ccd_count.
    clocking : integer, optional
        Set to 0 if you want to simulate a ECS run which doesn't clock, which
        you probably don't want to do if you're going to simulate an actual
        ECS run. Default: 1
    model_spec : string, optional
        Path to the model spec JSON file for the model. Default: None, the 
        standard model path will be used. 

    Examples
    --------
    >>> dea_run = SimulateSingleObs("1deamzt", "2016:201:05:12:03", "2016:201:05:12:03",
    ...                             14.0, 150., ccd_count=5, off_nominal_roll=-6.0,
    ...                             dh_heater=1)
    """
    def __init__(self, name, tstart, tstop, T_init, pitch, ccd_count,
                 vehicle_load=None, simpos=-99616.0, off_nominal_roll=0.0, 
                 dh_heater=0, fep_count=None, clocking=1, q=None, instrument=None,
                 model_spec=None, no_limit=False):
        if name in short_name_rev:
            name = short_name_rev[name]
        if name == "fptemp_11" and instrument is None:
            raise RuntimeError("Must specify either 'ACIS-I' or 'ACIS-S' in "
                               "'instrument' if you want to test a focal plane " 
                               "temperature prediction!")
        if fep_count is None:
            fep_count = ccd_count
        tstart = get_time(tstart)
        tstop = get_time(tstop)
        if q is None and name == "fptemp_11":
            raise RuntimeError("Please supply an attitude quaternion for the focal plane model!")
        self.vehicle_load = vehicle_load
        self.no_limit = no_limit
        datestart = tstart
        tstart = DateTime(tstart).secs
        tstop = DateTime(tstop).secs
        datestop = secs2date(tstop)
        tend = tstop+0.5*(tstop-tstart)
        dateend = secs2date(tend)
        self.datestart = datestart
        self.datestop = datestop
        self.tstart = Quantity(tstart, "s")
        self.tstop = Quantity(tstop, "s")
        self.dateend = dateend
        self.T_init = Quantity(T_init, "deg_C")
        if vehicle_load is None:
            states = {"ccd_count": np.array([ccd_count], dtype='int'),
                      "fep_count": np.array([fep_count], dtype='int'),
                      "clocking": np.array([clocking], dtype='int'),
                      'vid_board': np.array([ccd_count > 0], dtype='int'),
                      "pitch": np.array([pitch]),
                      "simpos": np.array([simpos]),
                      "datestart": np.array([self.datestart]),
                      "datestop": np.array([self.dateend]),
                      "tstart": np.array([self.tstart.value]),
                      "tstop": np.array([tend]),
                      "hetg": np.array(["RETR"]),
                      "letg": np.array(["RETR"]),
                      "off_nominal_roll": np.array([off_nominal_roll]),
                      "dh_heater": np.array([dh_heater], dtype='int')}
            # For the focal plane model we need a quaternion.
            if name == "fptemp_11":
                for i in range(4):
                    states["q%d" % (i+1)] = q[i]
        else:
            mylog.info("Modeling a %d-chip observation concurrent with " % ccd_count +
                       "the %s vehicle loads." % vehicle_load)
            states = dict((k, state.value) for (k, state) in
                          States.from_load_page(vehicle_load).table.items())
            states["off_nominal_roll"] = calc_off_nom_rolls(states)
            ecs_run_idxs = states["tstart"] < tstop
            states["ccd_count"][ecs_run_idxs] = ccd_count
            states["fep_count"][ecs_run_idxs] = fep_count
            states["clocking"][ecs_run_idxs] = clocking
            states["vid_board"][ecs_run_idxs] = ccd_count > 0
        super(SimulateSingleObs, self).__init__(name, datestart, dateend, states,
                                                T_init, model_spec=model_spec,
                                                get_msids=False, no_eclipse=True)

        mylog.info("Run Parameters")
        mylog.info("--------------")
        mylog.info("Start Datestring: %s" % datestart)
        mylog.info("Stop Datestring: %s" % datestop)
        mylog.info("Initial Temperature: %g degrees C" % T_init)
        mylog.info("CCD Count: %d" % ccd_count)
        if vehicle_load is None:
            disp_pitch = pitch
            disp_roll = off_nominal_roll
        else:
            pitches = states["pitch"][ecs_run_idxs]
            rolls = states["off_nominal_roll"][ecs_run_idxs]
            disp_pitch = "Min: %g, Max: %g" % (pitches.min(), pitches.max())
            disp_roll = "Min: %g, Max: %g" % (rolls.min(), rolls.max())
        mylog.info("Pitch: %s" % disp_pitch)
        mylog.info("SIM Position: %g" % simpos)
        mylog.info("Off-nominal Roll: %s" % disp_roll)
        mylog.info("Detector Housing Heater: %s" % {0: "OFF", 1: "ON"}[dh_heater])

        mylog.info("Model Result")
        mylog.info("------------")

        if name == "fptemp_11":
            limit = limits[self.name][instrument]
        else:
            limit = limits[self.name]
        self.limit = Quantity(limit, "deg_C")
        self.limit_time = None
        self.limit_date = None
        self.duration = None
        self.violate = False
        if self.no_limit:
            return
        viols = self.mvals.value > self.limit.value
        if np.any(viols):
            idx = np.where(viols)[0][0]
            self.limit_time = self.times('model', self.name)[idx]
            self.limit_date = secs2date(self.limit_time)
            self.duration = Quantity((self.limit_time.value-tstart)*0.001, "ks")
            msg = "The limit of %g degrees C will be reached at %s, " % (self.limit.value, self.limit_date)
            msg += "after %g ksec." % self.duration.value
            mylog.info(msg)
            if self.limit_time < self.tstop:
                self.violate = True
                viol_time = "before"
            else:
                self.violate = False
                viol_time = "after"
            mylog.info("The limit is reached %s the end of the observation." % viol_time)
        else:
            mylog.info("The limit of %g degrees C is never reached." % self.limit.value)

        if self.violate:
            mylog.warning("This observation is NOT safe from a thermal perspective.")
        else:
            mylog.info("This observation is safe from a thermal perspective.")

    def plot_model(self, no_annotations=False):
        """
        Plot the simulated model run.

        Parameters
        ----------
        no_annotations : boolean, optional
            If True, don't put lines or text on the plot. Shouldn't be
            used if you're actually trying to determine if a ECS run is
            safe. Default: False
        """
        if self.vehicle_load is None:
            field2 = None
        else:
            field2 = "pitch"
        viol_text = "NOT SAFE" if self.violate else "SAFE"
        dp = DatePlot(self, [("model", self.name)], field2=field2)
        if not no_annotations:
            if not self.no_limit:
                dp.add_hline(self.limit.value, ls='--', lw=2, color='g')
                dp.add_text(find_text_time(self.datestop, hours=4.0), self.T_init.value + 2.0,
                            viol_text, fontsize=22, color='black')
            dp.add_vline(self.datestart, ls='--', lw=2, color='b')
            dp.add_text(find_text_time(self.datestart), self.limit.value - 2.0,
                        "START", color='blue', rotation="vertical")
            dp.add_vline(self.datestop, ls='--', lw=2, color='b')
            dp.add_text(find_text_time(self.datestop), self.limit.value - 12.0,
                        "END", color='blue', rotation="vertical")
            if self.limit_date is not None:
                dp.add_vline(self.limit_date, ls='--', lw=2, color='r')
                dp.add_text(find_text_time(self.limit_date), self.limit.value-2.0,
                            "VIOLATION", color='red', rotation="vertical")
        dp.set_xlim(find_text_time(self.datestart, hours=-1.0), self.dateend)
        dp.set_ylim(self.T_init.value-2.0, 
                    max(self.limit.value, self.mvals.value.max())+3.0)
        return dp

    def get_temp_at_time(self, t):
        """
        Get the model temperature at a time *t* seconds
        past the beginning of the ECS run.
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

    def write_model(self, filename, overwrite=False):
        raise NotImplementedError

    def make_dashboard_plots(self, yplotlimits=None, errorplotlimits=None, fig=None):
        raise NotImplementedError

    def write_model_and_data(self, filename, overwrite=False):
        raise NotImplementedError


class SimulateECSRun(SimulateSingleObs):
    pass


class SimulateCTIRun(SimulateECSRun):
    pass
