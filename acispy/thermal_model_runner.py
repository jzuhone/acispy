from __future__ import print_function
import xija
import os
from astropy.units import Quantity
from acispy.data_container import DataContainer
from acispy.plots import DatePlot
import numpy as np
from Chandra.Time import secs2date, DateTime

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
            self.model.comp['roll'].set_data(self.states['roll'])
        if 'dpa_power' in self.model.comp:
            self.model.comp['dpa_power'].set_data(0.0) # This is just a hack, we're not 
                                                       # really setting the power to zero.
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

    def time_until_limit(self, limit):
        idx = np.searchsorted(self.model.mvals[0], limit)-1
        date = secs2date(self.model.times[idx])
        start = DateTime(self.tstart).secs
        msg = "The limit of %s degrees C will be reached at %s, " % (limit, date)
        msg += "after %g ksec." % ((self.model.times[idx]-start)*0.001)
        print(msg)

    @property
    def times(self):
        return Quantity(self.model.times, 's')

    @property
    def dates(self):
        return secs2date(self.model.times)

    @property
    def mvals(self):
        return Quantity(self.model.mvals[0], 'deg_C')