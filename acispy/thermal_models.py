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
from acispy.utils import mylog, calc_off_nom_rolls
import Ska.Numpy
import Ska.engarchive.fetch_sci as fetch

limits = {'dea': 35.5,
          'dpa': 35.5,
          'psmc': 52.5,
          'fep1_mong': 43.0,
          'fep1_actel': 43.0,
          'bep_pcb': 43.0}

msid_dict = {'dea': '1deamzt',
             'dpa': '1dpamzt',
             'psmc': '1pdeaat',
             'fep1_mong': 'tmp_fep1_mong',
             'fep1_actel': 'tmp_fep1_actel',
             'bep_pcb': 'tmp_bep_pcb'}

full_name = {"dea": "DEA",
             "dpa": "DPA",
             "psmc": "PSMC",
             "fep1_mong": "FEP1 Mongoose",
             "fep1_actel": "FEP1 Actel",
             "bep_pcb": "BEP PCB"}

def find_json(name, model_spec):
    if model_spec is None:
        if name == "psmc":
            path = "psmc_check"
        else:
            path = name
        if "SKA" in os.environ and os.path.exists(os.environ["SKA"]):
            model_spec = os.path.join(os.environ["SKA"],
                                      "share/%s/%s_model_spec.json" % (path, name))
        else:
            model_spec = os.path.join(os.getcwd(), "%s_model_spec.json" % name)
    if not os.path.exists(model_spec):
        raise IOError("The JSON file %s does not exist!" % model_spec)
    return model_spec

class ThermalModelRunner(Dataset):
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
    states : dict
        A dictionary of modeled commanded states required for the model. The
        states can either be a constant value or NumPy arrays. 
    T_init : float
        The starting temperature for the model in degrees C.
    model_spec : string, optional
        Path to the model spec JSON file for the model. Default: None, the 
        standard model path will be used.
    include_bad_times : boolean, optional
        If set, bad times from the data are included in the array masks
        and plots. Default: False

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
    ...                                "2016:005:00:00:00", states,
    ...                                10.1)
    """
    def __init__(self, name, tstart, tstop, states, T_init,
                 model_spec=None, include_bad_times=False):

        state_times = np.array([states["tstart"], states["tstop"]])

        self.model_spec = find_json(name, model_spec)

        self.xija_model = self._compute_model(name, tstart, tstop, states, 
                                              state_times, T_init)

        if isinstance(states, dict):
            states.pop("dh_heater", None)

        self.name = name

        components = [msid_dict[name]]
        if 'dpa_power' in self.xija_model.comp:
            components.append('dpa_power')

        self.bad_times = self.xija_model.bad_times
        self.bad_times_indices = self.xija_model.bad_times_indices

        masks = {}
        if include_bad_times:
            masks[msid_dict[name]] = np.ones(self.xija_model.times.shape, dtype='bool')
            for (left, right) in self.bad_times_indices:
                masks[msid_dict[name]][left:right] = False

        model_obj = Model.from_xija(self.xija_model, components, masks=masks)
        msids_obj = EmptyTimeSeries()
        states_obj = States(states)

        super(ThermalModelRunner, self).__init__(msids_obj, states_obj, model_obj)

    def _compute_model(self, name, tstart, tstop, states, state_times, T_init):
        if isinstance(states, np.ndarray):
            state_names = states.dtype.names
        else:
            state_names = list(states.keys())
        if "off_nominal_roll" in state_names:
            roll = np.array(states["off_nominal_roll"])
        else:
            roll = calc_off_nom_rolls(states)
        model = xija.XijaModel(name, start=tstart, stop=tstop, model_spec=self.model_spec)
        if 'eclipse' in model.comp:
            model.comp['eclipse'].set_data(False)
        model.comp[msid_dict[name]].set_data(T_init)
        model.comp['sim_z'].set_data(np.array(states['simpos']), state_times)
        if 'roll' in model.comp:
            model.comp['roll'].set_data(roll, state_times)
        if 'dpa_power' in model.comp:
            model.comp['dpa_power'].set_data(0.0) # This is just a hack, we're not
            # really setting the power to zero.
        if 'pin1at' in model.comp:
            model.comp['pin1at'].set_data(T_init-10.)
        if 'dh_heater' in model.comp:
            model.comp['dh_heater'].set_data(states.get("dh_heater", 0), state_times)
        for st in ('ccd_count', 'fep_count', 'vid_board', 'clocking', 'pitch'):
            model.comp[st].set_data(np.array(states[st]), state_times)
        model.make()
        model.calc()
        return model

    @classmethod
    def from_states_table(cls, name, tstart, tstop, states_file, T_init,
                          model_spec=None, include_bad_times=False):
        """
        Class for running Xija thermal models.

        Parameters
        ----------
        name : string
            The name of the model to simulate. Can be "dea", "dpa", "psmc", or "fep1mong".
        tstart : string
            The start time in YYYY:DOY:HH:MM:SS format.
        tstop : string
            The stop time in YYYY:DOY:HH:MM:SS format.
        states_file : string
            A file containing commanded states, in the same format as "states.dat" which is
            outputted by ACIS thermal model runs for loads.
        T_init : float
            The starting temperature for the model in degrees C.
        model_spec : string, optional
            Path to the model spec JSON file for the model. Default: None, the
            standard model path will be used.
        include_bad_times : boolean, optional
            If set, bad times from the data are included in the array masks
            and plots. Default: False
        """
        state_keys = ["ccd_count", "pitch", "fep_count", "clocking", "vid_board", "simpos"]
        states = ascii.read(states_file)
        states_dict = dict((k, states[k]) for k in state_keys)
        if "off_nominal_roll" in states.colnames:
            states_dict["off_nominal_roll"] = states["off_nominal_roll"]
        else:
            states_dict["off_nominal_roll"] = calc_off_nom_rolls(states)
        state_times = np.array([states["datestart"], states["datestop"]])
        return cls(name, tstart, tstop, states_dict, state_times, T_init,
                   model_spec=model_spec, include_bad_times=include_bad_times)

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
        msid = msid_dict[self.name]
        T = self["model", msid].value
        times = self.times("model", msid).value
        dates = self.dates("model", msid)
        temp_array = np.rec.fromarrays([times, dates, T], names=('time', 'date', msid))
        fmt = {msid: '%.2f', 'time': '%.2f'}
        out = open(filename, 'w')
        Ska.Numpy.pprint(temp_array, fmt, out)
        out.close()

class ThermalModelFromData(ThermalModelRunner):
    """
    Class for running Xija thermal models using commanded states
    and telemetry data as an initial condition. 

    Parameters
    ----------
    name : string
        The name of the model to simulate. Can be "dea", "dpa", "psmc", 
        "fep1mong", or "fep1actel".
    tstart : string
        The start time in YYYY:DOY:HH:MM:SS format.
    tstop : string
        The stop time in YYYY:DOY:HH:MM:SS format.
    T_init : float, optional
        The initial temperature for the thermal moden run. If None, 
        an initial temperature will be determined from telemetry. 
        Default: None
    use_msids : boolean, optional
        If True, telemetry can be used to determine the initial temperature
        and will be loaded for comparison to the model run. Default: True
    model_spec : string, optional
        Path to the model spec JSON file for the model. Default: None, the
        standard model path will be used.
    include_bad_times : boolean, optional
        If set, bad times from the data are included in the array masks
        and plots. Default: False
    server : string
         DBI server or HDF5 file. Default: None

    Examples
    --------
    >>> from acispy import ThermalModelFromData
    >>> tstart = "2016:091:12:05:00.100"
    >>> tstop = "2016:100:13:07:45.234"
    >>> dpa_model = ThermalModelFromData("dpa", tstart, tstop)
    """
    def __init__(self, name, tstart, tstop, T_init=None, use_msids=True,
                 model_spec=None, include_bad_times=False, server=None):

        msid = msid_dict[name]
        tstart_secs = DateTime(tstart).secs
        start = secs2date(tstart_secs-700.0)

        self.model_spec = find_json(name, model_spec)

        states_obj = States.from_database(start, tstop, server=server)
        states = dict((k, np.array(v)) for k, v in states_obj.items())
        states["off_nominal_roll"] = calc_off_nom_rolls(states)

        if T_init is None:
            if not use_msids:
                raise RuntimeError("Set 'use_msids=True' if you want to use telemetry "
                                   "for setting the initial state!")
            T_init = fetch.MSID(msid, tstart_secs-700., tstart_secs+700.).vals.mean()

        self.xija_model = self._compute_model(name, tstart, tstop, states,
                                              states_obj["ccd_count"].times.value,
                                              T_init)

        model_times = self.xija_model.times

        components = [msid]
        if 'dpa_power' in self.xija_model.comp:
            components.append('dpa_power')

        self.name = name

        self.bad_times = self.xija_model.bad_times
        self.bad_times_indices = []
        for t0, t1 in self.bad_times:
            t0, t1 = DateTime([t0, t1]).secs
            i0, i1 = np.searchsorted(model_times, [t0, t1])
            if i1 > i0:
                self.bad_times_indices.append((i0, i1))

        masks = {}
        if include_bad_times:
            masks[msid] = np.ones(model_times.shape, dtype='bool')
            for (left, right) in self.bad_times_indices:
                masks[msid][left:right] = False

        model_obj = Model.from_xija(self.xija_model, components, masks=masks)
        if use_msids:
            msids_obj = MSIDs.from_database([msid], tstart, tstop=tstop,
                                            interpolate=True, interpolate_times=model_times)
        else:
            msids_obj = EmptyTimeSeries()
        super(ThermalModelRunner, self).__init__(msids_obj, states_obj, model_obj)

    def write_model_and_data(self, filename, overwrite=False):
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
        msid = msid_dict[self.name]
        self.add_diff_data_model_field(msid)
        states_to_map = ["vid_board", "pcad_mode", "pitch", "clocking", "simpos",
                         "ccd_count", "fep_count", "off_nominal_roll", "power_cmd"]
        for state in states_to_map:
            self.map_state_to_msid(state, msid)
        out = [("msids", state) for state in states_to_map]
        out += [("msids", msid), ("model", msid), ("model", "diff_%s" % msid)]
        self.write_msids(filename, out, overwrite=overwrite)

    def make_dashboard_plots(self, yplotlimits=None, errorplotlimits=None, fig=None):
        """
        Make dashboard plots for the particular thermal model.

        Parameters
        ----------
        yplotlimits : two-element array_like, optional
            The (min, max) bounds on the temperature to use for the
            temperature vs. time plot. Default: Determine the min/max
            bounds from the telemetry and model prediction and
            decrease/increase by degrees to determine the plot limits.
        errorplotlimits : two-element array_like, optional
            The (min, max) error bounds to use for the error plot.
            Default: [-15, 15]
        """
        from xijafit import dashboard as dash
        msid = msid_dict[self.name]
        telem = self["msids", msid]
        pred = self["model", msid]
        mask = np.logical_and(telem.mask, pred.mask)
        times = telem.times.value[mask]
        if yplotlimits is None:
            ymin = min(telem.value[mask].min(), pred.value[mask].min())-2
            ymax = min(telem.value[mask].max(), pred.value[mask].max())+2
            yplotlimits = [ymin, ymax]
        if errorplotlimits is None:
            errorplotlimits = [-15, 15]
        mylimits = {"units": "C", "caution_high": limits[self.name]+2,
                    "planning_limit": limits[self.name]}
        dash.dashboard(pred.value[mask], telem.value[mask], times, mylimits,
                       msid=msid_dict[self.name], modelname=full_name[self.name],
                       errorplotlimits=errorplotlimits, yplotlimits=yplotlimits,
                       fig=fig)

def find_text_time(time, hours=1.0):
    return secs2date(date2secs(time)+hours*3600.0)

class SimulateCTIRun(ThermalModelRunner):
    """
    Class for simulating thermal models during CTI runs under constant conditions.

    Parameters
    ----------
    name : string
        The name of the model to simulate. Can be "dea", "dpa", "psmc", or "fep1mong".
    tstart : string
        The start time of the CTI run in YYYY:DOY:HH:MM:SS format.
    tstop : string
        The stop time of the CTI run in YYYY:DOY:HH:MM:SS format.
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
    clocking : integer, optional
        Set to 0 if you want to simulate a CTI run which doesn't clock, which
        you probably don't want to do if you're going to simulate an actual
        CTI run. Default: 1
    model_spec : string, optional
        Path to the model spec JSON file for the model. Default: None, the 
        standard model path will be used. 

    Examples
    --------
    >>> dea_run = SimulateCTIRun("dea", "2016:201:05:12:03", "2016:201:05:12:03",
    ...                          14.0, 150., ccd_count=5, off_nominal_roll=-6.0, 
    ...                          dh_heater=1)
    """
    def __init__(self, name, tstart, tstop, T_init, pitch, ccd_count,
                 vehicle_load=None, simpos=-99616.0, off_nominal_roll=0.0, 
                 dh_heater=0, clocking=1, model_spec=None):
        self.vehicle_load = vehicle_load
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
                      "fep_count": np.array([ccd_count], dtype='int'),
                      "clocking": np.array([clocking], dtype='int'),
                      'vid_board': np.array([clocking], dtype='int'),
                      "pitch": np.array([pitch]),
                      "simpos": np.array([simpos]),
                      "datestart": np.array([self.datestart]),
                      "datestop": np.array([self.dateend]),
                      "tstart": np.array([self.tstart.value]),
                      "tstop": np.array([tend]),
                      "off_nominal_roll": np.array([off_nominal_roll]),
                      "dh_heater": np.array([dh_heater], dtype='int')}
        else:
            mylog.info("Modeling a %d-chip CTI run concurrent with " % ccd_count +
                       "the %s vehicle loads." % vehicle_load)
            states = dict((k, state.value) for (k, state) in
                          States.from_load_page(vehicle_load).table.items())
            states["off_nominal_roll"] = calc_off_nom_rolls(states)
            cti_run_idxs = states["tstart"] < tstop
            states["ccd_count"][cti_run_idxs] = ccd_count
            states["fep_count"][cti_run_idxs] = ccd_count
            states["clocking"][cti_run_idxs] = 1
            states["vid_board"][cti_run_idxs] = 1
        super(SimulateCTIRun, self).__init__(name, datestart, dateend, states,
                                             T_init, model_spec=model_spec)

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
            pitches = states["pitch"][cti_run_idxs]
            rolls = states["off_nominal_roll"][cti_run_idxs]
            disp_pitch = "Min: %g, Max: %g" % (pitches.min(), pitches.max())
            disp_roll = "Min: %g, Max: %g" % (rolls.min(), rolls.max())
        mylog.info("Pitch: %s" % disp_pitch)
        mylog.info("SIM Position: %g" % simpos)
        mylog.info("Off-nominal Roll: %s" % disp_roll)
        mylog.info("Detector Housing Heater: %s" % {0: "OFF", 1: "ON"}[dh_heater])

        mylog.info("Model Result")
        mylog.info("------------")

        self.limit = Quantity(limits[self.name], "deg_C")
        viols = self.mvals.value > self.limit.value
        if np.any(viols):
            idx = np.where(viols)[0][0]
            self.limit_time = self.times('model', msid_dict[self.name])[idx]
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
            mylog.info("The limit is reached %s the end of the CTI run." % viol_time)
        else:
            self.limit_time = None
            self.limit_date = None
            self.duration = None
            self.violate = False
            mylog.info("The limit of %g degrees C is never reached." % self.limit.value)

        if self.violate:
            mylog.warning("This CTI run is NOT safe from a thermal perspective.")
        else:
            mylog.info("This CTI run is safe from a thermal perspective.")

    def plot_model(self, no_annotations=False):
        """
        Plot the simulated model run.

        Parameters
        ----------
        no_annotations : boolean, optional
            If True, don't put lines or text on the plot. Shouldn't be
            used if you're actually trying to determine if a CTI run is
            safe. Default: False
        """
        if self.vehicle_load is None:
            field2 = None
        else:
            field2 = "pitch"
        viol_text = "NOT SAFE" if self.violate else "SAFE"
        dp = DatePlot(self, [("model", msid_dict[self.name])], field2=field2)
        if not no_annotations:
            dp.add_hline(self.limit.value, ls='--', lw=2, color='g')
            dp.add_vline(self.datestart, ls='--', lw=2, color='b')
            dp.add_text(find_text_time(self.datestart), self.limit.value - 2.0,
                        "START CTI RUN", color='blue', rotation="vertical")
            dp.add_vline(self.datestop, ls='--', lw=2, color='b')
            dp.add_text(find_text_time(self.datestop), self.limit.value - 12.0,
                        "END CTI RUN", color='blue', rotation="vertical")
            dp.add_text(find_text_time(self.datestop, hours=4.0), self.T_init.value+2.0,
                        viol_text, fontsize=22, color='black')
            if self.limit_date is not None:
                dp.add_vline(self.limit_date, ls='--', lw=2, color='r')
                dp.add_text(find_text_time(self.limit_date), self.limit.value-2.0,
                            "VIOLATION", color='red', rotation="vertical")
        dp.set_xlim(find_text_time(self.datestart, hours=-1.0), self.dateend)
        dp.set_ylim(self.T_init.value-2.0, 
                    max(self.limit.value, self.mvals.value.max())+3.0)
        return dp

    @property
    def mvals(self):
        return self['model', msid_dict[self.name]]

    def write_states(self, states_file):
        raise NotImplementedError
