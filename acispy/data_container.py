from acispy.msids import MSIDs
from acispy.states import States, cmd_state_codes
from acispy.model import Model
from Chandra.Time import secs2date, DateTime
from acispy.fields import create_derived_fields, \
    DerivedField, FieldContainer, OutputFieldFunction, \
    OutputTimeFunction, dummy_time_function
from acispy.time_series import TimeSeriesData, EmptyTimeSeries
from acispy.utils import unit_table, \
    get_display_name, moving_average, \
    ensure_list
import numpy as np

class DataContainer(object):
    def __init__(self, msids, states, model):
        self.msids = msids
        self.states = states
        self.fields = FieldContainer()
        self.field_list = []
        for ftype in ["msids", "states"]:
            obj = getattr(self, ftype)
            self._populate_fields(ftype, obj)
        if isinstance(model, TimeSeriesData):
            self.model = model
            self._populate_fields("model", self.model)
        else:
            for key, value in model.items():
                setattr(self, key, value)
                self._populate_fields(key, value)
        create_derived_fields(self)
        self.data = {}
        self.state_codes = {}
        if hasattr(self.msids, "state_codes"):
            for k, v in self.msids.state_codes.items():
                self.state_codes["msids", k] = v
        self.state_codes.update(cmd_state_codes)

    def _populate_fields(self, ftype, obj):
        if ftype.startswith("model"):
            utype = "model"
        else:
            utype = ftype
        for fname in obj.keys():
            func = OutputFieldFunction(ftype, fname)
            unit = unit_table[utype].get(fname, '')
            display_name = get_display_name(ftype, fname)
            tfunc = OutputTimeFunction(ftype, fname)
            df = DerivedField(ftype, fname, func, unit,
                              tfunc, display_name=display_name)
            self.fields.output_fields[ftype, fname] = df
            self.field_list.append((ftype, fname))

    def __getitem__(self, item):
        if item not in self.data:
            self.data[item] = self.fields[item](self)
        return self.data[item]

    def __contains__(self, item):
        return item in self.fields

    @property
    def derived_field_list(self):
        return list(self.fields.derived_fields.keys())

    def add_derived_field(self, ftype, fname, function, units, times,
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
        times : array or tuple
            The timing data for the field in seconds from the
            beginning of the mission. Can supply an array of times
            or a field specification. If the latter, then the
            times for this field will be used.
        display_name : string, optional
            The name to use when displaying the field in plots. 

        Examples
        --------
        >>> def _dpaa_power(dc):
        ...     return (dc["msids", "1dp28avo"]*dc["msids", "1dpicacu"]).to("W")
        >>> dc.add_derived_field("msids", "dpa_a_power", _dpaa_power, 
        ...                      ("msids", "1dp28avo"), "W",
        ...                      display_name="DPA-A Power")
        """
        if isinstance(times, tuple):
            tfunc = OutputTimeFunction(times[0], times[1])
        else:
            tfunc = dummy_time_function(times)
        df = DerivedField(ftype, fname, function, units, tfunc, display_name=display_name)
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
        >>> dc.add_averaged_field("msids", "1dpicacu", n=10) 
        """
        def _avg(dc):
            return moving_average(dc[ftype, fname], n=n)
        display_name = "Average %s" % self.fields[ftype, fname].display_name
        units = unit_table[ftype].get(fname, '')
        self.add_derived_field(ftype, "avg_%s" % fname, _avg, units,
                               (ftype, fname), display_name=display_name)

    def map_state_to_msid(self, state, msid, ftype="msids"):
        """
        Create a new derived field by interpolating a state to the times of
        a MSID or model component.

        Parameters
        ----------
        state : string
            The state to be interpolated.
        msid : string
            The msid or model component to interpolate the state to.
        ftype : string, optional
            The field type to use. "msids" or "model". Default: "msids"

        Examples
        --------
        >>> dc.map_state_to_msid("ccd_count", "1dpamzt")
        """
        def _state(dc):
            msid_times = dc.times(ftype, msid)
            state_times = dc.times("states", state)[1]
            indexes = np.searchsorted(state_times, msid_times)
            return dc["states", state][indexes]
        units = unit_table['states'].get(state, '')
        self.add_derived_field(ftype, state, _state, units, (ftype, msid),
                               display_name=self.fields["states", state].display_name)

    def times(self, ftype, fname):
        """
        Return the timing information in seconds from the beginning of the mission
        for a field given its *ftype* and *fname*.

        Examples
        --------
        >>> dc.times("msids", "1deamzt")
        """
        return self.fields[ftype, fname].time_func(self)

    def dates(self, ftype, fname):
        """
        Return the timing information in date and time for a field given its *ftype* and *fname*.

        Examples
        --------
        >>> dc.dates("states", "pitch")
        """
        times = self.times(ftype, fname)
        if ftype == 'states':
            return (secs2date(times[0]), secs2date(times[1]))
        else:
            return secs2date(times)

    def slice_field_on_dates(self, ftype, fname, tstart, tstop):
        """
        Return a sliced array of a field between two dates.

        Parameters
        ----------
        ftype : string
            The field type.
        fname : string
            The field name.
        tstart : string
            The start time in YYYY:DOY:HH:MM:SS format
        tstop : string
            The stop time in YYYY:DOY:HH:MM:SS format

        Examples
        --------
        >>> dc.slice_field_on_dates("states", "pitch", "2016:100:10:21:30", "2016:110:09:23:11")
        """
        tstart = DateTime(tstart).secs
        tstop = DateTime(tstop).secs
        times = self.times(ftype, fname)
        if ftype == 'states':
            st = np.searchsorted(times[0].value, tstart)
            ed = np.searchsorted(times[1].value, tstop)
        else:
            st = np.searchsorted(times.value, tstart)
            ed = np.searchsorted(times.value, tstop)
        return self[ftype, fname][st:ed]

    @classmethod
    def fetch_from_database(cls, tstart, tstop, msid_keys=None, state_keys=None,
                            filter_bad=True, stat=None, interpolate_msids=False):
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
            If not supplied, a default list of states will be loaded. Default: None
        filter_bad : boolean, optional
            Whether or not to filter out bad values of MSIDs. Default: True.
        stat : string, optional
            return 5-minute or daily statistics ('5min' or 'daily') Default: '5min'
            If ``interpolate_msids=True`` this setting is ignored.
        interpolate_msids : boolean, optional
            If True, MSIDs are interpolated to a common time sequence with uniform
            timesteps of 328 seconds. Default: False

        Examples
        --------
        >>> from acispy import DataContainer
        >>> tstart = "2016:091:12:05:00.100"
        >>> tstop = "2016:100:13:07:45.234"
        >>> msids = ["1deamzt", "1pin1at"]
        >>> states = ["pitch", "ccd_count"]
        >>> dc = DataContainer.fetch_from_database(tstart, tstop, msid_keys=msids,
        ...                                        state_keys=states)
        """
        if msid_keys is not None:
            msids = MSIDs.from_database(msid_keys, tstart, tstop=tstop,
                                       filter_bad=filter_bad, stat=stat,
                                       interpolate=interpolate_msids)
        else:
            msids = EmptyTimeSeries()
        states = States.from_database(tstart, tstop, states=state_keys)
        model = EmptyTimeSeries()
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
            If not supplied, a default list of states will be loaded.

        Examples
        --------
        >>> from acispy import DataContainer
        >>> states = ["ccd_count", "roll"]
        >>> dc = DataContainer.fetch_from_tracelog("acisENG10d_00985114479.70.tl",
        ...                                        state_keys=states)
        """
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
        tmin = 1.0e55
        tmax = -1.0e55
        for k in msids.times.keys():
            tmin = min(msids.times[k][0].value, tmin)
            tmax = max(msids.times[k][-1].value, tmax)
        states = States.from_database(secs2date(tmin), secs2date(tmax), states=state_keys)
        model = EmptyTimeSeries()
        return cls(msids, states, model)

    @classmethod
    def fetch_model_from_load(cls, load, comps=None, get_msids=False, 
                              interpolate_msids=False):
        """
        Fetch a temperature model and its associated commanded states
        from a load review. Optionally get MSIDs for the same time period.

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
        interpolate_msids : boolean, optional
            If True, MSIDs are interpolated to a time sequence that is common
            with the model data. Default: False

        Examples
        --------
        >>> from acispy import DataContainer
        >>> comps = ["1deamzt", "1pdeaat", "fptemp_11"]
        >>> dc = DataContainer.fetch_model_from_load("APR0416C", comps, get_msids=True)
        """
        if comps is None:
            comps = ["1deamzt","1dpamzt","1pdeaat","fptemp_11"]
        model = Model.from_load_page(load, comps)
        states = States.from_load_page(load)
        if get_msids:
            times = model.times[comps[0]].value
            tstart = secs2date(times[0]-700.0)
            tstop = secs2date(times[-1]+700.0)
            if interpolate_msids:
                interpolate_times = times
            else:
                interpolate_times = None
            msids = MSIDs.from_database(comps, tstart, tstop=tstop,
                                        interpolate=interpolate_msids,
                                        interpolate_times=interpolate_times)
            if interpolate_msids and msids.times[comps[0]].size != times.size:
                raise RuntimeError("Lengths of time arrays for model data and MSIDs "
                                   "do not match. You probably ran a model past the "
                                   "end date in the engineering archive!")
        else:
            msids = EmptyTimeSeries()
        return cls(msids, states, model)

    @classmethod
    def fetch_models_from_files(cls, temp_files, state_file, get_msids=False, 
                                interpolate_msids=False):
        """
        Fetch a temperature model and its associated commanded states
        from ASCII table files generated by xija or model check tools. 
        Optionally get MSIDs for the same time period.

        Parameters
        ----------
        temp_files : string or list of strings
            Path(s) of file(s) to get the temperature model(s) from, generated from a tool
            like, i.e. dea_check. One or more files can be accepted. It is assumed
            that the files have the same timing information and have the same states.
        state_file : string
            Path of the states.dat file corresponding to the temperature file(s).
        get_msids : boolean, optional
            Whether or not to load the MSIDs corresponding to the 
            temperature models for the same time period from the 
            engineering archive. Default: False.
        interpolate_msids : boolean, optional
            If True, MSIDs are interpolated to a time sequence that is common
            with the model data. Default: False

        Examples
        --------
        >>> from acispy import DataContainer
        >>> dc = DataContainer.fetch_models_from_files(["old_model/temperatures.dat",
        ...                                             "new_model/temperatures.dat"],
        ...                                             "old_model/states.dat"
        ...                                             get_msids=True)

        >>> from acispy import DataContainer
        >>> dc = DataContainer.fetch_models_from_files(["temperatures_dea.dat",
        ...                                             "temperatures_dpa.dat"],
        ...                                             "old_model/states.dat"
        ...                                             get_msids=True)
        """
        temp_files = ensure_list(temp_files)
        if len(temp_files) == 1:
            models = Model.from_load_file(temp_files[0])
            comps = list(models.keys())
        else:
            model_list = []
            comps = []
            for temp_file in temp_files:
                m = Model.from_load_file(temp_file)
                model_list.append(m)
                comps.append(m.keys()[0])
            comps = np.unique(comps)
            if len(comps) == 1:
                models = dict(("model%d" % i, m) for i, m in enumerate(model_list))
            elif len(comps) == len(temp_files):
                models = Model.join_models(model_list)
            else:
                raise RuntimeError("You can only import model files where all are the same MSID"
                                   "or they are all different!")
        states = States.from_load_file(state_file)
        if get_msids:
            times = models[0].times[comps[0]].value
            tstart = secs2date(times[0]-700.0)
            tstop = secs2date(times[-1]+700.0)
            if interpolate_msids:
                interpolate_times = times
            else:
                interpolate_times = None
            msids = MSIDs.from_database(comps, tstart, tstop=tstop, filter_bad=True,
                                        interpolate=interpolate_msids, 
                                        interpolate_times=interpolate_times)
            if interpolate_msids and msids.times[comps[0]].size != times.size:
                raise RuntimeError("Lengths of time arrays for model data and MSIDs "
                                   "do not match. You probably ran a model past the "
                                   "end date in the engineering archive!")
        else:
            msids = EmptyTimeSeries()
        return cls(msids, states, models)
