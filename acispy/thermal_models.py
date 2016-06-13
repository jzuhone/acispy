from __future__ import print_function
import xija
import os
from astropy.units import Quantity
from acispy.data_container import DataContainer
from acispy.plots import DatePlot
import numpy as np
from Chandra.Time import secs2date, date2secs
from acispy.states import States
from acispy.model import Model
from acispy.time_series import TimeSeriesData
from acispy.utils import mylog

limits = {'dea': 35.5,
          'dpa': 35.5,
          'psmc': 52.5}

msid_dict = {'dea': '1deamzt',
             'dpa': '1dpamzt',
             'psmc': '1pdeaat'}

default_json_path = os.path.join(os.environ["SKA"], "share/%s/%s_model_spec.json")

class ThermalModelRunner(DataContainer):
    """
    Class for running Xija thermal models.

    Parameters
    ----------
    name : string
        The name of the model to simulate. Can be "dea", "dpa", or "psmc".
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

    Examples
    --------
    >>> states = {"ccd_count": np.array([5,6,1]),
    ...          "pitch": np.array([150.0]*3),
    ...          "fep_count": np.array([5,6,1]),
    ...          "clocking": np.array([1]*3),
    ...          "vid_board": np.array([1]*3),
    ...          "off_nominal_roll": np.array([0.0]*3),
    ...          "simpos": np.array([-99616.0]*3)}
    >>> state_times = [["2015:002:00:00:00","2015:002:12:00:00","2015:003:12:00:00"],
    ...                ["2015:002:12:00:00","2015:003:12:00:00","2015:005:00:00:00"]]
    >>> dpa_model = ThermalModelRunner("dpa", "2015:002:00:00:00", 
    ...                                "2016:005:00:00:00", states,
    ...                                state_times, 10.1)
    """
    def __init__(self, name, tstart, tstop, states, state_times, 
                 T_init, model_spec=None):
        state_times = np.array([date2secs(state_times[0]),
                                date2secs(state_times[1])])
        if model_spec is None:
            if name == "psmc":
                path = "psmc_check"
            else:
                path = name
            model_spec = os.path.join(default_json_path % (path, name))
        else:
            model_spec = model_spec
        model = xija.XijaModel(name, start=tstart, stop=tstop, model_spec=model_spec)
        if 'eclipse' in model.comp:
            model.comp['eclipse'].set_data(False)
        model.comp[msid_dict[name]].set_data(T_init)
        model.comp['sim_z'].set_data(states['simpos'], state_times)
        if 'roll' in model.comp:
            model.comp['roll'].set_data(states['off_nominal_roll'], state_times)
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

        states["tstart"] = state_times[0,:]
        states["tstop"] = state_times[1,:]
        states.pop("dh_heater", None)

        self.name = name
        self.model_spec = model_spec

        model_obj = Model.from_xija(model, [msid_dict[name]])
        msids_obj = TimeSeriesData({}, {})
        states_obj = States(states)

        super(ThermalModelRunner, self).__init__(msids_obj, states_obj, model_obj)

class SimulateCTIRun(ThermalModelRunner):
    """
    Class for simulating thermal models during CTI runs under constant conditions.

    Parameters
    ----------
    name : string
        The name of the model to simulate. Can be "dea", "dpa", or "psmc".
    tstart : string
        The start time in YYYY:DOY:HH:MM:SS format.
    T_init : float
        The starting temperature for the model in degrees C.
    pitch : float
        The pitch at which to run the model in degrees. 
    days : float, optional
        The number of days to run the model. Default: 3.0
    simpos : float, optional
        The SIM position at which to run the model. Default: -99616.0
    ccd_count : integer, optional
        The number of CCDs to clock. Default: 6
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
    def __init__(self, name, tstart, T_init, pitch, days=3.0, simpos=-99616.0, 
                ccd_count=6, off_nominal_roll=0.0, dh_heater=0, model_spec=None):
        states = {"ccd_count": ccd_count,
                  "fep_count": ccd_count,
                  "clocking": 1,
                  'vid_board': 1,
                  "pitch": pitch,
                  "simpos": simpos,
                  "off_nominal_roll": off_nominal_roll,
                  "dh_heater": dh_heater}
        datestart = tstart
        tstart = date2secs(tstart)
        tstop = tstart + days*86400.
        datestop = secs2date(tstop)
        state_times = [[datestart], [datestop]]
        super(SimulateCTIRun, self).__init__(name, tstart, tstop, states,
                                             state_times, T_init, model_spec=model_spec)
        err = np.abs(self.asymptotic_temperature-self.mvals[-10])/self.asymptotic_temperature
        if err > 1.0e-5:
            raise RuntimeWarning("You may not have reached the asymptotic temperature! Suggest"
                                 " increasing the 'days' parameter past its current value of %g!" % days)
        self.limit = Quantity(limits[self.name], "deg_C")
        if self.asymptotic_temperature > self.limit:
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

