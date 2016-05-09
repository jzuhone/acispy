from __future__ import print_function
import xija
import os
from astropy.units import Quantity
from acispy.data_container import DataContainer
from acispy.plots import DatePlot
import numpy as np
from Chandra.Time import secs2date, DateTime, date2secs

limits = {'dea': 35.5,
          'dpa': 35.5,
          'psmc': 52.5}

msid_dict = {'dea': '1deamzt',
             'dpa': '1dpamzt',
             'psmc': '1pdeaat'}

model_root = "/proj/sot/ska/bin"

class ThermalModelRunner(object):
    def __init__(self, name, tstart, tstop, states, T_init, model_spec=None):
        self.name = name
        self.tstart = tstart
        self.tstop = tstop
        self.states = states
        if 'dh_heater' not in states:
            self.states['dh_heater'] = 0
        self.T_init = T_init
        if model_spec is None:
            self.model_spec = os.path.join(model_root, '%s_check' % name, 
                                           '%s_model_spec.json' % name)
        else:
            self.model_spec = model_spec
        self.model = xija.XijaModel(self.name, start=self.tstart,
                                    stop=self.tstop, model_spec=self.model_spec)
        if 'eclipse' in self.model.comp:
            self.model.comp['eclipse'].set_data(False)
        self.model.comp[msid_dict[name]].set_data(self.T_init)
        self.model.comp['sim_z'].set_data(self.states['simpos'])
        if 'roll' in self.model.comp:
            self.model.comp['roll'].set_data(self.states['off_nominal_roll'])
        if 'dpa_power' in self.model.comp:
            self.model.comp['dpa_power'].set_data(0.0) # This is just a hack, we're not 
                                                       # really setting the power to zero.
        if 'pin1at' in self.model.comp:
            self.model.comp['pin1at'].set_data(self.states['pin1at'])
        if 'dh_heater' in self.model.comp:
            self.model.comp['dh_heater'].set_data(self.states['dh_heater'])
        for st in ('ccd_count', 'fep_count', 'vid_board', 'clocking', 'pitch'):
            self.model.comp[st].set_data(states[st])
        self.model.make()
        self.model.calc()

    def plot_model(self):
        dc = DataContainer.fetch_model_from_xija(self.model, [msid_dict[self.name]])
        dp = DatePlot(dc, [("model", msid_dict[self.name])])
        return dp

    @property
    def times(self):
        return Quantity(self.model.times, 's')

    @property
    def dates(self):
        return secs2date(self.model.times)

    @property
    def mvals(self):
        return Quantity(self.model.mvals[0], 'deg_C')

class SimulateCTIRun(ThermalModelRunner):
    def __init__(self, name, tstart, T_init, pitch, days=3.0, simpos=-99616, 
                 ccd_count=6, off_nominal_roll=0.0, dh_heater=0, model_spec=None):
        states = {"ccd_count": ccd_count,
                  "fep_count": ccd_count,
                  "clocking": 1,
                  'vid_board': 1,
                  "pitch": pitch,
                  "simpos": simpos,
                  "off_nominal_roll": off_nominal_roll,
                  "dh_heater": dh_heater}
        tstart = date2secs(tstart)
        tstop = tstart + days*86400.
        super(SimulateCTIRun, self).__init__(name, tstart, tstop, states,
                                             T_init, model_spec=model_spec)
        err = np.abs(self.asymptotic_temperature-self.mvals[-10])/self.asymptotic_temperature
        if err > 1.0e-5:
            raise RuntimeWarning("You may not have reached the asymptotic temperature! Suggest"
                                 " increasing the 'days' parameter past its current value of %g!" % days)
        self.limit = Quantity(limits[self.name], "deg_C")
        if self.asymptotic_temperature > self.limit:
            idx = np.searchsorted(self.model.mvals[0], self.limit.value)-1
            self.limit_time = self.model.times[idx]
            self.limit_date = secs2date(self.limit_time)
            self.duration = (self.limit_time-self.tstart)*0.001
            msg = "The limit of %s degrees C will be reached at %s, " % (self.limit, self.limit_date)
            msg += "after %g ksec." % self.duration
        else:
            self.limit_time = None
            self.limit_date = None
            self.duration = None
            msg = "The limit of %s degrees C is never reached!" % self.limit
        print(msg)

    def plot_model(self):
        dp = super(SimulateCTIRun, self).plot_model()
        dp.add_hline(self.limit.value, ls='--', lw=2, color='g')
        if self.limit_date is not None:
            dp.add_vline(self.limit_date, ls='--', lw=2, color='r')
        return dp

    @property
    def asymptotic_temperature(self):
        return self.mvals[-1]

