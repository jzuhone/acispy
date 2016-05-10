from acispy.msids import MSIDs
from acispy.states import States
from acispy.model import Model
from Chandra.Time import secs2date
from acispy.fields import create_derived_fields, \
    DerivedField, FieldContainer
from acispy.time_series import TimeSeriesData
from acispy.utils import unit_table, \
    get_display_name, moving_average
import Ska.Numpy
from astropy.units import Quantity
import numpy as np

def make_field_func(ftype, fname):
    def _field_func(dc):
        obj = getattr(dc, ftype)
        return obj[fname]
    return _field_func

class DataContainer(object):
    def __init__(self, msids, states, model):
        self.msids = msids
        self.states = states
        self.model = model
        self.fields = FieldContainer()
        self.field_list = []
        for ftype in ["msids", "states", "model"]:
            obj = getattr(self, ftype)
            for fname in obj.keys():
                func = make_field_func(ftype, fname)
                unit = unit_table[ftype].get(fname, '')
                display_name = get_display_name(ftype, fname)
                df = DerivedField(ftype, fname, func, [], unit,
                                  display_name=display_name)
                self.fields[ftype, fname] = df
                self.field_list.append((ftype, fname))
        create_derived_fields(self)

    def __getitem__(self, item):
        self._check_derived_field(item)
        return self.fields[item](self)

    def __contains__(self, item):
        return item in self.fields

    def _check_derived_field(self, item):
        deps = self.fields[item].get_deps()
        for dep in deps:
            if dep not in self:
                raise RuntimeError("Derived field %s needs field %s, but you didn't load it!" % (item, dep))

    @property
    def derived_field_list(self):
        return list(self.fields.derived_fields.keys())

    def add_derived_field(self, ftype, fname, function, deps, units, time_func=None,
                          display_name=None):
        """
        Add a new derived field.

        Parameters
        ----------
        ftype : string
            The type of the field to add.
        fname : string
            The name of the field to add.
        function : function
            The function which computes the field.
        units : string
            The units of the field.
        time_func : function, optional
            A function which returns the timing data
            for the field.
        display_name : string, optional
            The name to use when displaying the field in plots. 

        Examples
        --------
        >>> def _dpaa_power(dc):
        ...     return (dc["msids", "1dp28avo"]*dc["msids", "1dpicacu"]).to("W")
        >>> dc.add_derived_field("msids", "dpa_a_power", _dpaa_power, 
        ...                      [("msids", "1dp28avo"), ("msids", "1dpicacu")],
        ...                      "W", display_name="DPA-A Power")
        """
        df = DerivedField(ftype, fname, function, deps, units, time_func=time_func,
                          display_name=display_name)
        self.fields.derived_fields[ftype, fname] = df

    def add_averaged_field(self, ftype, fname, n=10):
        """
        Add a new field from an average of another.

        Parameters
        ----------
        ftype : string
            The type of the field to be averaged.
        fname : string
            The name of the field to be averaged.
        n : integer, optional
            The number of samples to average over. Default: 5

        Examples
        --------
        >>> add_averaged_field("msids", "1dpicacu", n=10) 
        """
        def _avg(dc):
            return moving_average(dc[ftype, fname], n=n)
        def _avg_times(dc):
            return dc.times(ftype, fname)[n-1:]
        display_name = "Average %s" % self.fields[ftype, fname].display_name
        units = unit_table[ftype].get(fname, '')
        self.add_derived_field(ftype, "avg_%s" % fname, _avg, [(ftype, fname)], units,
                               time_func=_avg_times, display_name=display_name)

    def add_interpolated_field(self, ftype, fname, times):
        """
        Add a new field from interpolating a field to a new
        set of times.

        Parameters
        ----------
        ftype : string
            The type of the field to be averaged.
        fname : string
            The name of the field to be averaged.
        times : array of times
            The timing array to interpolate the array to.

        Examples
        --------
        >>> times = dc.times("msids", "1pdeaat")
        >>> add_interpolated_field("msids", "1pin1at", times) 
        """
        times_out = np.array(times)
        units = unit_table[ftype].get(fname, '')
        def _interp(dc):
            times_in = dc.times(ftype, fname).value
            return Quantity(Ska.Numpy.interpolate(dc[ftype, fname],
                                                  times_in, times_out,
                                                  method='linear'), units)
        def _interp_times(dc):
            return Quantity(times_out, 's')
        display_name = self.fields[ftype, fname].display_name
        self.add_derived_field(ftype, "interp_%s" % fname, _interp, [(ftype, fname)],
                               units, time_func=_interp_times, display_name=display_name)

    def times(self, ftype, fname):
        """
        Return the timing information in seconds from the beginning of the mission
        for a field given its *type* and *name*.

        Examples
        --------
        >>> dc.times("msids", "1deamzt")
        """
        if (ftype, fname) in self.fields.derived_fields:
            df = self.fields.derived_fields[ftype, fname]
            return df.time_func(self)
        elif (ftype, fname) in self.fields.output_fields:
            src = getattr(self, ftype)
            return src.times[fname]
        else:
            raise KeyError((ftype, fname))

    def dates(self, ftype, fname):
        """
        Return the timing information in date and time for a field given its *type* and *name*.

        Examples
        --------
        >>> dc.dates("states", "pitch")
        """
        times = self.times(ftype, fname)
        if ftype == 'states':
            return (secs2date(times[0]), secs2date(times[1]))
        else:
            return secs2date(times)

    @classmethod
    def fetch_from_database(cls, tstart, tstop, msid_keys=None, state_keys=None, 
                            filter_bad=True, stat=None):
        """
        Fetch MSIDs from the engineering archive and states from the commanded
        states database. 

        Parameters
        ----------
        tstart : string
            The start time in YYYY:DOY:HH:MM:SS format
        tstop : string
            The stop time in YYYY:DOY:HH:MM:SS format
        msid_keys : list of strings, optional
            List of MSIDs to pull from the engineering archive.
        state_keys : list of strings, optional
            List of commanded states to pull from the commanded states database.
        filter_bad : boolean, optional
            Whether or not to filter out bad values of MSIDs. Default: True.
        stat : string, optional
            return 5-minute or daily statistics ('5min' or 'daily') Default: '5min'

        Examples
        --------
        >>> from acispy import DataContainer
        >>> tstart = "2016:091:12:05:00.100"
        >>> tstop = "2016:100:13:07:45.234"
        >>> states = ["pitch", "off_nominal_roll"]
        >>> dc = DataContainer.fetch_from_database(tstart, tstop, msid_keys=msids,
        ...                                        state_keys=states)
        """
        if msid_keys is not None:
            msids = MSIDs.from_database(msid_keys, tstart, tstop=tstop, 
                                       filter_bad=filter_bad, stat=stat)
        else:
            msids = TimeSeriesData({}, {})
        if state_keys is not None:
            states = States.from_database(state_keys, tstart, tstop)
        else:
            states = TimeSeriesData({}, {})
        model = TimeSeriesData({}, {})
        return cls(msids, states, model)

    @classmethod
    def fetch_from_tracelog(cls, filename, state_keys=None):
        """
        Fetch MSIDs from a tracelog file and states from the commanded
        states database.

        Parameters
        ----------
        filename : string
            The path to the tracelog file
        state_keys : list of strings, optional
            List of commanded states to pull from the commanded states database.

        Examples
        --------
        >>> from acispy import DataContainer
        >>> states = ["ccd_count", "roll"]
        >>> dc = DataContainer.fetch_from_tracelog("acisENG10d_00985114479.70.tl",
        ...                                        state_keys=states)
        """
        states = TimeSeriesData({}, {})
        # Figure out what kind of file this is
        f = open(filename, "r")
        line = f.readline()
        f.close()
        if line.startswith("TIME"):
            msids = MSIDs.from_tracelog(filename)
        elif line.startswith("YEAR"):
            msids = MSIDs.from_mit_file(filename)
        else:
            raise RuntimeError("I cannot parse this file!")
        if state_keys is not None:
            tmin = 1.0e55
            tmax = -1.0e55
            for k in msids.keys():
                if k.endswith("_times"):
                    tmin = min(msids[k][0], tmin)
                    tmax = max(msids[k][-1], tmax)
            states = States.from_database(state_keys, secs2date(tmin), secs2date(tmax))
        model = TimeSeriesData({}, {})
        return cls(msids, states, model)

    @classmethod
    def fetch_model_from_load(cls, load, comps, get_msids=False):
        """
        Fetch a temperature model and its associated commanded states
        from a load review. Optionally get MSIDs for the same time period.

        Parameters
        ----------
        load : string
            The load review to get the model from, i.e. "JAN2516A"
        comps : list of strings
            List of temperature components to get from the load models.
        get_msids : boolean, optional
            Whether or not to load the MSIDs corresponding to the 
            temperature models for the same time period from the 
            engineering archive. Default: False.

        Examples
        --------
        >>> from acispy import DataContainer
        >>> comps = ["1deamzt", "1pdeaat", "fptemp_11"]
        >>> dc = DataContainer.fetch_model_from_load("APR0416C", comps, get_msids=True)
        """
        model = Model.from_load(load, comps)
        states = States.from_load(load)
        if get_msids:
            tstart = states["datestart"][0]
            tstop = states["datestop"][-1]
            msids = MSIDs.from_database(comps, tstart, tstop=tstop,
                                        filter_bad=True)
        else:
            msids = TimeSeriesData({}, {})
        return cls(msids, states, model)

    @classmethod
    def fetch_model_from_xija(cls, xija_model, comps):
        model = Model.from_xija(xija_model, comps)
        msids = TimeSeriesData({}, {})
        states = TimeSeriesData({}, {})
        return cls(msids, states, model)
