from acispy.msids import MSIDs
from acispy.states import States, cmd_state_codes
from acispy.model import Model
from acispy.units import APQuantity, APStringArray
from Chandra.Time import secs2date, DateTime
from acispy.fields import create_derived_fields, \
    DerivedField, FieldContainer, OutputFieldFunction
from acispy.time_series import TimeSeriesData, EmptyTimeSeries
from acispy.utils import unit_table, \
    get_display_name, moving_average, \
    ensure_list
import numpy as np
import os

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
        self._times = {}
        self._dates = {}

    def _populate_fields(self, ftype, obj):
        if ftype.startswith("model"):
            utype = "model"
        else:
            utype = ftype
        for fname in obj.keys():
            func = OutputFieldFunction(ftype, fname)
            unit = unit_table[utype].get(fname, '')
            display_name = get_display_name(ftype, fname)
            df = DerivedField(ftype, fname, func, unit,
                              display_name=display_name)
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

    def add_derived_field(self, ftype, fname, function, units,
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
        ...                      "W", display_name="DPA-A Power")
        """
        df = DerivedField(ftype, fname, function, units,
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
        >>> dc.add_averaged_field("msids", "1dpicacu", n=10) 
        """
        def _avg(dc):
            v = dc[ftype, fname]
            return APQuantity(moving_average(v.value, n=n), v.times,
                              unit=v.unit, mask=v.mask)
        display_name = "Average %s" % self.fields[ftype, fname].display_name
        units = unit_table[ftype].get(fname, '')
        self.add_derived_field(ftype, "avg_%s" % fname, _avg, units,
                               display_name=display_name)

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
        units = unit_table['states'].get(state, '')
        def _state(dc):
            msid_times = dc.times(ftype, msid)
            state_times = dc.times("states", state)[1]
            indexes = np.searchsorted(state_times, msid_times)
            v = dc["states", state][indexes].value
            if v.dtype.char != 'S':
                return APQuantity(v, msid_times, unit=units)
            else:
                return APStringArray(v, msid_times)
        self.add_derived_field(ftype, state, _state, units,
                               display_name=self.fields["states", state].display_name)

    def times(self, ftype, fname):
        """
        Return the timing information in seconds from the beginning of the mission
        for a field given its *ftype* and *fname*.

        Examples
        --------
        >>> dc.times("msids", "1deamzt")
        """
        if (ftype, fname) not in self._times:
            self._times[ftype, fname] = self[ftype, fname].times
        return self._times[ftype, fname]

    def dates(self, ftype, fname):
        """
        Return the timing information in date and time for a field given its *ftype* and *fname*.

        Examples
        --------
        >>> dc.dates("states", "pitch")
        """
        if (ftype, fname) not in self._dates:
            self._dates[ftype, fname] = self[ftype, fname].dates
        return self._dates[ftype, fname]

    def write_msids(self, filename, fields, mask_field=None, overwrite=False):
        """
        Write MSIDs (or MSID-like quantities such as model values) to an ASCII
        table file. This assumes that all of the quantities have been
        interpolated to a common set of times.

        Parameters
        ----------
        filename : string
            The filename to write the quantities to.
        fields : list of (type, name) field specifications
            The quantities to be written to the ASCII table.
        overwrite : boolean, optional
            If True, an existing file with the same name will be overwritten.
        """
        from astropy.table import Table
        fields = ensure_list(fields)
        base_times = self.times(*fields[0]).value
        if mask_field is not None:
            mask = self[mask_field].mask
        else:
            mask = np.ones(base_times.size, dtype="bool")
        if len(fields) > 1:
            for field in fields[1:]:
                if not np.all(base_times == self.times(*field).value):
                    raise RuntimeError("To write MSIDs, all of the times should be the same!!")
        if os.path.exists(filename) and not overwrite:
            raise IOError("File %s already exists, but overwrite=False!" % filename)
        data = dict(("_".join(k), self[k].value[mask]) for k in fields)
        data["times"] = self.times(*fields[0]).value[mask]
        data["dates"] = self.dates(*fields[0])[mask]
        Table(data).write(filename, format='ascii')

    def write_states(self, filename, overwrite=False):
        """
        Write commanded states to an ASCII table file. An error will be thrown
        if there are no commanded states present.

        Parameters
        ----------
        filename : string
            The filename to write the states to.
        overwrite : boolean, optional
            If True, an existing file with the same name will be overwritten.
        """
        from astropy.table import Table
        if isinstance(self.states, EmptyTimeSeries):
            raise RuntimeError("There are no commanded states to be written!")
        if os.path.exists(filename) and not overwrite:
            raise IOError("File %s already exists, but overwrite=False!" % filename)
        Table(dict((k,v.value) for k, v in self.states.items())).write(filename, format='ascii')

class ArchiveData(DataContainer):
    def __init__(self, tstart, tstop, msid_keys=None, state_keys=None,
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
        >>> from acispy import ArchiveData
        >>> tstart = "2016:091:12:05:00.100"
        >>> tstop = "2016:100:13:07:45.234"
        >>> msids = ["1deamzt", "1pin1at"]
        >>> states = ["pitch", "ccd_count"]
        >>> dc = ArchiveData(tstart, tstop, msid_keys=msids, state_keys=states)
        """
        if msid_keys is not None:
            msids = MSIDs.from_database(msid_keys, tstart, tstop=tstop,
                                       filter_bad=filter_bad, stat=stat,
                                       interpolate=interpolate_msids)
        else:
            msids = EmptyTimeSeries()
        states = States.from_database(tstart, tstop, states=state_keys)
        model = EmptyTimeSeries()
        super(ArchiveData, self).__init__(msids, states, model)

class TracelogData(DataContainer):
    def __init__(self, filename, state_keys=None):
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
        >>> from acispy import TracelogData
        >>> states = ["ccd_count", "roll"]
        >>> dc = TracelogData("acisENG10d_00985114479.70.tl", state_keys=states)
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
        for v in msids.values():
            tmin = min(v.times[0].value, tmin)
            tmax = max(v.times[-1].value, tmax)
        states = States.from_database(secs2date(tmin), secs2date(tmax), states=state_keys)
        model = EmptyTimeSeries()
        super(TracelogData, self).__init__(msids, states, model)

class ModelDataFromLoad(DataContainer):
    def __init__(self, load, comps=None, get_msids=False, interpolate_msids=False):
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
        >>> from acispy import ModelDataFromLoad
        >>> comps = ["1deamzt", "1pdeaat", "fptemp_11"]
        >>> dc = ModelDataFromLoad("APR0416C", comps, get_msids=True)
        """
        if comps is None:
            comps = ["1deamzt","1dpamzt","1pdeaat","fptemp_11"]
        model = Model.from_load_page(load, comps)
        states = States.from_load_page(load)
        if get_msids:
            times = model[comps[0]].times.value
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
        super(ModelDataFromLoad, self).__init__(msids, states, model)

class ModelDataFromFiles(DataContainer):
    def __init__(self, temp_files, state_file, get_msids=False, interpolate_msids=False):
        """
        Fetch multiple temperature models and their associated commanded states
        from ASCII table files generated by xija or model check tools.

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
        >>> from acispy import ModelDataFromFiles
        >>> dc = ModelDataFromFiles(["old_model/temperatures.dat", "new_model/temperatures.dat"],
        ...                         "old_model/states.dat", get_msids=True)

        >>> from acispy import ModelDataFromFiles
        >>> dc = ModelDataFromFiles(["temperatures_dea.dat", "temperatures_dpa.dat"],
        ...                         "old_model/states.dat", get_msids=True)
        """
        temp_files = ensure_list(temp_files)
        if len(temp_files) == 1:
            models = Model.from_load_file(temp_files[0])
            comps = list(models.keys())
            times = models[comps[0]].times.value
        else:
            model_list = []
            comps = []
            for i, temp_file in enumerate(temp_files):
                m = Model.from_load_file(temp_file)
                model_list.append(m)
                comps.append(m.keys()[0])
                if i == 0:
                    times = m[comps[0]].times.value 
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
            tstart = secs2date(times[0]-700.0)
            tstop = secs2date(times[-1]+700.0)
            if interpolate_msids:
                interpolate_times = times
            else:
                interpolate_times = None
            msids = MSIDs.from_database(comps, tstart, tstop=tstop, filter_bad=True,
                                        interpolate=interpolate_msids, 
                                        interpolate_times=interpolate_times)
            if interpolate_msids and msids[comps[0]].times.size != times.size:
                raise RuntimeError("Lengths of time arrays for model data and MSIDs "
                                   "do not match. You probably ran a model past the "
                                   "end date in the engineering archive!")
        else:
            msids = EmptyTimeSeries()
        super(ModelDataFromFiles, self).__init__(msids, states, models)
