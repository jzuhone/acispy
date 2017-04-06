from __future__ import print_function
import xija
import os
from astropy.units import Quantity
from astropy.io import ascii
from acispy.data_container import DataContainer
from acispy.plots import DatePlot
import numpy as np
from Chandra.Time import secs2date, DateTime
from acispy.states import States
from acispy.model import Model
from acispy.msids import MSIDs
from acispy.time_series import EmptyTimeSeries
from acispy.utils import mylog, calc_off_nom_rolls
import Ska.Numpy

limits = {'dea': 35.5,
          'dpa': 35.5,
          'psmc': 52.5,
          'fep1mong': 43.0}

msid_dict = {'dea': '1deamzt',
             'dpa': '1dpamzt',
             'psmc': '1pdeaat',
             'fep1mong': 'tmp_fep1_mong'}

default_json_path = os.path.join(os.environ["SKA"], "share/%s/%s_model_spec.json")

class ThermalModelRunner(DataContainer):
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
    states : dict
        A dictionary of modeled commanded states required for the model. The
        states can either be a constant value or NumPy arrays. 
    state_times : array of strings
        A list containting two arrays of times in YYYY:DOY:HH:MM:SS format 
        which correspond to the start and stop times of the states.
    T_init : float
        The starting temperature for the model in degrees C.
    model_spec : string, optional
        Path to the model spec JSON file for the model. Default: None, the 
        standard model path will be used.
    exclude_bad_times : boolean, optional
        If set, excludes bad times from the data. Default: False

    Examples
    --------
    >>> states = {"ccd_count": np.array([5,6,1]),
    ...           "pitch": np.array([150.0]*3),
    ...           "fep_count": np.array([5,6,1]),
    ...           "clocking": np.array([1]*3),
    ...           "vid_board": np.array([1]*3),
    ...           "off_nominal_roll": np.array([0.0]*3),
    ...           "simpos": np.array([-99616.0]*3)}
    >>> state_times = [["2015:002:00:00:00","2015:002:12:00:00","2015:003:12:00:00"],
    ...                ["2015:002:12:00:00","2015:003:12:00:00","2015:005:00:00:00"]]
    >>> dpa_model = ThermalModelRunner("dpa", "2015:002:00:00:00", 
    ...                                "2016:005:00:00:00", states,
    ...                                state_times, 10.1)
    """
    def __init__(self, name, tstart, tstop, states, state_times, 
                 T_init, model_spec=None, exclude_bad_times=False):
        state_times = np.array([DateTime(state_times[0]).secs,
                                DateTime(state_times[1]).secs])
        if model_spec is None:
            if name == "psmc":
                path = "psmc_check"
            else:
                path = name
            self.model_spec = os.path.join(default_json_path % (path, name))
        else:
            self.model_spec = model_spec

        states["tstart"] = state_times[0,:]
        states["tstop"] = state_times[1,:]
        states["datestart"] = secs2date(state_times[0,:])
        states["datestop"] = secs2date(state_times[1,:])

        self.xija_model = self._compute_model(name, tstart, tstop, states, 
                                              state_times, T_init)

        states.pop("dh_heater", None)

        self.name = name

        components = [msid_dict[name]]
        if 'dpa_power' in self.xija_model.comp:
            components.append('dpa_power')

        self.bad_times = self.xija_model.bad_times
        self.bad_times_indices = self.xija_model.bad_times_indices

        masks = {}
        if exclude_bad_times:
            masks[msid_dict[name]] = np.ones(self.xija_model.times.shape, dtype='bool')
            for (left, right) in self.bad_times_indices:
                masks[msid_dict[name]][left:right] = False

        model_obj = Model.from_xija(self.xija_model, components, masks=masks)
        msids_obj = EmptyTimeSeries()
        states_obj = States(states)

        super(ThermalModelRunner, self).__init__(msids_obj, states_obj, model_obj)

    def _compute_model(self, name, tstart, tstop, states, state_times, T_init):
        model = xija.XijaModel(name, start=tstart, stop=tstop, model_spec=self.model_spec)
        if 'eclipse' in model.comp:
            model.comp['eclipse'].set_data(False)
        model.comp[msid_dict[name]].set_data(T_init)
        model.comp['sim_z'].set_data(states['simpos'], state_times)
        if 'roll' in model.comp:
            model.comp['roll'].set_data(states["off_nominal_roll"], state_times)
        if 'dpa_power' in model.comp:
            model.comp['dpa_power'].set_data(0.0) # This is just a hack, we're not
            # really setting the power to zero.
        if 'pin1at' in model.comp:
            model.comp['pin1at'].set_data(T_init-10.)
        if 'dh_heater' in model.comp:
            model.comp['dh_heater'].set_data(states.get("dh_heater", 0), state_times)
        for st in ('ccd_count', 'fep_count', 'vid_board', 'clocking', 'pitch'):
            model.comp[st].set_data(states[st], state_times)
        model.make()
        model.calc()
        return model

    @classmethod
    def from_states_table(cls, name, tstart, tstop, states_file, T_init,
                          model_spec=None, exclude_bad_times=False):
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
        exclude_bad_times : boolean, optional
            If set, excludes bad times from the data. Default: False
        """
        state_keys = ["ccd_count", "pitch", "fep_count", "clocking", "vid_board", "simpos"]
        states = ascii.read(states_file)
        states_dict = dict((k, states[k]) for k in state_keys)
        states_dict["off_nominal_roll"] = calc_off_nom_rolls(states)
        state_times = np.array([states["datestart"], states["datestop"]])
        return cls(name, tstart, tstop, states_dict, state_times, T_init,
                   model_spec=model_spec, exclude_bad_times=exclude_bad_times)

    def write_model(self, model_file, overwrite=False):
        """
        Write the model data vs. time to an ASCII text file.

        Parameters
        ----------
        model_file : string
            The filename to write the data to.
        overwrite : boolean, optional
            If True, an existing file with the same name will be overwritten.
        """
        if os.path.exists(model_file) and not overwrite:
            raise IOError("File %s already exists, but overwrite=False!" % model_file)
        msid = msid_dict[self.name]
        T = self["model", msid].value
        times = self.times("model", msid).value
        dates = self.dates("model", msid)
        temp_array = np.rec.fromarrays([times, dates, T], names=('time', 'date', msid))
        fmt = {msid: '%.2f', 'time': '%.2f'}
        out = open(model_file, 'w')
        Ska.Numpy.pprint(temp_array, fmt, out)
        out.close()

class ThermalModelFromData(ThermalModelRunner):
    """
    Class for running Xija thermal models using commanded states
    and telemetry data as an initial condition, extracted from
    a :class:`~acispy.data_container.DataContainer` object.

    Parameters
    ----------
    dc : :class:`~acispy.data_container.DataContainer`
        The DataContainer to extract the information from.
    name : string
        The name of the model to simulate. Can be "dea", "dpa", "psmc", or "fep1mong".
    model_spec : string, optional
        Path to the model spec JSON file for the model. Default: None, the
        standard model path will be used.
    exclude_bad_times : boolean, optional
        If set, excludes bad times from the data. Default: False

    Examples
    --------
    >>> from acispy import DataContainer, ThermalModelFromData
    >>> tstart = "2016:091:12:05:00.100"
    >>> tstop = "2016:100:13:07:45.234"
    >>> msids = ["1dpamzt"]
    >>> dc = DataContainer.fetch_from_database(tstart, tstop, msid_keys=msids)
    >>> dpa_model = ThermalModelFromData(dc, "dpa")
    """
    def __init__(self, tstart, tstop, name, model_spec=None, exclude_bad_times=False):

        msid = msid_dict[name]
        tstart_secs = DateTime(tstart).secs
        start = secs2date(tstart_secs-700.0)
        msids_obj = MSIDs.from_database([msid], start, tstop=tstop)
        msid_times = msids_obj[msid].times.value

        if model_spec is None:
            if name == "psmc":
                path = "psmc_check"
            else:
                path = name
            self.model_spec = os.path.join(default_json_path % (path, name))
        else:
            self.model_spec = model_spec

        states_obj = States.from_database(start, tstop)
        states = dict((k, np.array(v)) for k, v in states_obj.items())
        states["off_nominal_roll"] = calc_off_nom_rolls(states)

        ok = ((msid_times >= tstart_secs - 700.) &
              (msid_times <= tstart_secs + 700.))

        T_init = msids_obj[msid].value[ok].mean()

        self.xija_model = self._compute_model(name, tstart, tstop, states,
                                              states_obj["ccd_count"].times.value,
                                              T_init)

        components = [msid]
        if 'dpa_power' in self.xija_model.comp:
            components.append('dpa_power')

        self.bad_times = self.xija_model.bad_times
        self.bad_times_indices = []
        for t0, t1 in self.bad_times:
            t0, t1 = DateTime([t0, t1]).secs
            i0, i1 = np.searchsorted(msid_times, [t0, t1])
            if i1 > i0:
                self.bad_times_indices.append((i0, i1))

        masks = {}
        if exclude_bad_times:
            masks[msid] = np.ones(msid_times.shape, dtype='bool')
            for (left, right) in self.bad_times_indices:
                masks[msid][left:right] = False

        model_obj = Model.from_xija(self.xija_model, components,
                                    interp_times=msid_times, masks=masks)

        super(ThermalModelRunner, self).__init__(msids_obj, states_obj, model_obj)

class SimulateCTIRun(ThermalModelRunner):
    """
    Class for simulating thermal models during CTI runs under constant conditions.

    Parameters
    ----------
    name : string
        The name of the model to simulate. Can be "dea", "dpa", "psmc", or "fep1mong".
    tstart : string
        The start time in YYYY:DOY:HH:MM:SS format.
    T_init : float
        The starting temperature for the model in degrees C.
    pitch : float
        The pitch at which to run the model in degrees. 
    ccd_count : integer
        The number of CCDs to clock.
    days : float, optional
        The number of days to run the model. Default: 3.0
    simpos : float, optional
        The SIM position at which to run the model. Default: -99616.0
    off_nominal_roll : float, optional
        The off-nominal roll in degrees for the model. Default: 0.0
    dh_heater: integer, optional
        Flag to set whether (1) or not (0) the detector housing heater is on. 
        Default: 0
    model_spec : string, optional
        Path to the model spec JSON file for the model. Default: None, the 
        standard model path will be used. 

    Examples
    --------
    >>> dea_run = SimulateCTIRun("dea", "2016:201:05:12:03", 14.0, 150.,
    ...                          ccd_count=5, off_nominal_roll=-6.0, dh_heater=1)
    """
    def __init__(self, name, tstart, T_init, pitch, ccd_count, days=3.0,
                 simpos=-99616.0, off_nominal_roll=0.0, dh_heater=0, model_spec=None):
        states = {"ccd_count": np.array([ccd_count], dtype='int'),
                  "fep_count": np.array([ccd_count], dtype='int'),
                  "clocking": np.array([1], dtype='int'),
                  'vid_board': np.array([1], dtype='int'),
                  "pitch": np.array([pitch]),
                  "simpos": np.array([simpos]),
                  "off_nominal_roll": np.array([off_nominal_roll]),
                  "dh_heater": np.array([dh_heater], dtype='int')}
        datestart = tstart
        tstart = DateTime(tstart).secs
        tstop = tstart + days*86400.
        datestop = secs2date(tstop)
        state_times = [[datestart], [datestop]]
        super(SimulateCTIRun, self).__init__(name, datestart, datestop, states,
                                             state_times, T_init, model_spec=model_spec)

        mylog.info("Run Parameters")
        mylog.info("--------------")
        mylog.info("Start Datestring: %s" % datestart)
        mylog.info("Start Time: %g s" % tstart)
        mylog.info("Initial Temperature: %g degrees C" % T_init)
        mylog.info("CCD Count: %d" % ccd_count)
        mylog.info("Pitch: %g" % pitch)
        mylog.info("SIM Position: %g" % simpos)
        mylog.info("Off-nominal Roll: %g" % off_nominal_roll)
        mylog.info("Detector Housing Heater: %s" % {0: "OFF", 1: "ON"}[dh_heater])

        mylog.info("Model Result")
        mylog.info("------------")

        err = np.abs(self.asymptotic_temperature-self.mvals[-10])/self.asymptotic_temperature
        if err.value > 1.0e-3:
            mylog.warning("You may not have reached the asymptotic temperature! Suggest"
                          " increasing the 'days' parameter past its current value of %g!" % days)
        self.limit = Quantity(limits[self.name], "deg_C")
        if self.asymptotic_temperature.value > self.limit.value:
            idx = np.searchsorted(self.mvals.value, self.limit.value)-1
            self.limit_time = self.times('model', msid_dict[self.name])[idx]
            self.limit_date = secs2date(self.limit_time)
            self.duration = Quantity((self.limit_time.value-tstart)*0.001, "ks")
            msg = "The limit of %g degrees C will be reached at %s, " % (self.limit.value, self.limit_date)
            msg += "after %g ksec." % self.duration.value
        else:
            self.limit_time = None
            self.limit_date = None
            self.duration = None
            msg = "The limit of %g degrees C is never reached!" % self.limit.value
        mylog.info(msg)
        mylog.info("The asymptotic temperature is %g degrees C." % self.asymptotic_temperature.value)

    def plot_model(self):
        """
        Plot the simulated model run.
        """
        dp = DatePlot(self, [("model", msid_dict[self.name])])
        dp.add_hline(self.limit.value, ls='--', lw=2, color='g')
        if self.limit_date is not None:
            dp.add_vline(self.limit_date, ls='--', lw=2, color='r')
        return dp

    @property
    def mvals(self):
        return self['model', msid_dict[self.name]]

    @property
    def asymptotic_temperature(self):
        return self.mvals[-1]

    def write_states(self, states_file):
        raise NotImplementedError
