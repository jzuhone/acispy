from acispy.msids import MSIDs, CombinedMSIDs, ConcatenatedMSIDs
from acispy.states import States, cmd_state_codes
from acispy.model import Model
from acispy.units import APQuantity, APStringArray
from Chandra.Time import secs2date
from acispy.fields import create_builtin_derived_msids, \
    DerivedField, FieldContainer, OutputFieldFunction, \
    OutputFieldsNotFound, create_builtin_derived_states
from acispy.time_series import TimeSeriesData, EmptyTimeSeries
from acispy.utils import get_display_name, moving_average, \
    ensure_list, get_time
from acispy.units import get_units
import numpy as np
import os
from six import string_types
import Ska.engarchive.fetch_sci as fetch


class Dataset(object):
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
        if not isinstance(self.msids, EmptyTimeSeries):
            create_builtin_derived_msids(self)
        if not isinstance(self.states, EmptyTimeSeries):
            create_builtin_derived_states(self)
        self.data = {}
        self.state_codes = {}
        if hasattr(self.msids, "state_codes"):
            for k, v in self.msids.state_codes.items():
                self.state_codes["msids", k] = v
        self.state_codes.update(cmd_state_codes)
        self._times = {}
        self._dates = {}
        self._checked_fields = []

    def _populate_fields(self, ftype, obj):
        for fname in obj.keys():
            func = OutputFieldFunction(ftype, fname)
            unit = str(getattr(obj[fname], "unit", ""))
            display_name = get_display_name(ftype, fname)
            df = DerivedField(ftype, fname, func, unit,
                              display_name=display_name)
            self.fields.output_fields[ftype, fname] = df
            if ftype not in self.fields.types:
                self.fields.types.append(ftype)
            self.field_list.append((ftype, fname))

    def __getitem__(self, item):
        fd = self._determine_field(item)
        if fd not in self.data:
            self.data[fd] = self.fields[fd](self)
        return self.data[fd]

    def __contains__(self, item):
        fd = self._determine_field(item)
        return fd in self.fields

    def _determine_field(self, field):
        if field not in self._checked_fields:
            if isinstance(field, tuple):
                if len(field) != 2:
                    raise RuntimeError("Invalid field specification {}!".format(field))
                fd = (field[0].lower(), field[1].lower())
                if fd in self.fields:
                    checked_field = fd
                else:
                    raise RuntimeError("Cannot find field {}!".format(field))
            elif isinstance(field, string_types):
                fd = field.lower()
                candidates = []
                for ftype in self.fields.types:
                    if (ftype, fd) in self.fields:
                        candidates.append((ftype, fd))
                if len(candidates) > 1:
                    msg = "Multiple field types for field name %s!\n" % field
                    for c in candidates:
                        msg += "    {}\n".format(c)
                    raise RuntimeError(msg)
                elif len(candidates) == 0:
                    raise RuntimeError("Cannot find field {}!".format(field))
                else:
                    checked_field = candidates[0]
            else:
                raise RuntimeError("Invalid field specification {}!".format(field))
        else:
            checked_field = field
        return checked_field

    @property
    def derived_field_list(self):
        return list(self.fields.derived_fields.keys())

    def _check_derived_field(self, field, df):
        if df.depends is not None:
            dep_list = []
            for fd in df.depends:
                if fd not in self.fields.list_all_fields():
                    dep_list.append(fd)
            if len(dep_list) > 0:
                raise OutputFieldsNotFound(field, dep_list)

    @classmethod
    def from_hdf5(cls, filename):
        import h5py
        f = h5py.File(filename, "r")
        if "msids" in f:
            msids = MSIDs.from_hdf5(f["msids"])
        else:
            msids = EmptyTimeSeries()
        if "states" in f:
            states = States.from_hdf5(f["states"])
        else:
            states = EmptyTimeSeries()
        if "model" in f:
            model = Model.from_hdf5(f["model"])
        else:
            model = EmptyTimeSeries()
        f.close()
        return cls(msids, states, model)

    def write_hdf5(self, filename, overwrite=True):
        import h5py
        if os.path.exists(filename) and not overwrite:
            raise IOError("The file %s already exists and overwrite=False!!" % filename)
        f = h5py.File(filename, "w")
        if not self.msids._is_empty:
            gmsids = f.create_group("msids")
            for k, v in self.msids.items():
                d = gmsids.create_dataset(k, data=v.value)
                d.attrs["times"] = v.times
                if hasattr(v, "mask"):
                    d.attrs["mask"] = v.mask
                if hasattr(v, "unit"):
                    d.attrs["unit"] = v.unit
            gmsids.attrs["state_codes"] = self.msids.state_codes
            gmsids.attrs["derived_msids"] = self.msids.derived_msids
        if not self.states._is_empty:
            gstates = f.create_group("states")
            for k, v in self.states.items():
                d = gstates.create_dataset(k, data=v.value)
                d.attrs["times"] = v.times
                if hasattr(v, "unit"):
                    d.attrs["unit"] = v.unit
        if not self.model._is_empty:
            gmodel = f.create_group("model")
            for k, v in self.model.items():
                d = gmodel.create_dataset(k, data=v.value)
                d.attrs["times"] = v.times
                if hasattr(v, "mask"):
                    d.attrs["mask"] = v.mask
                d.attrs["unit"] = v.unit
        f.flush()
        f.close()

    def add_derived_field(self, ftype, fname, function, units,
                          display_name=None, depends=None):
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
        >>> def _dpaa_power(ds):
        ...     return (ds["msids", "1dp28avo"]*ds["msids", "1dpicacu"]).to("W")
        >>> ds.add_derived_field("msids", "dpa_a_power", _dpaa_power,
        ...                      "W", display_name="DPA-A Power")
        """
        df = DerivedField(ftype, fname, function, units,
                          display_name=display_name, 
                          depends=depends)
        self._check_derived_field((ftype, fname), df)
        self.fields.derived_fields[ftype, fname] = df
        if ftype not in self.fields.types:
            self.fields.types.append(ftype)

    def add_averaged_field(self, field, n=10):
        """
        Add a new field from an average of another.

        Parameters
        ----------
        field : string or (type, name) tuple
            The field to be averaged.
        n : integer, optional
            The number of samples to average over. Default: 5

        Examples
        --------
        >>> ds.add_averaged_field(("msids", "1dpicacu"), n=10)
        """
        ftype, fname = self._determine_field(field)
        def _avg(ds):
            v = ds[ftype, fname]
            return APQuantity(moving_average(v.value, n=n), v.times,
                              unit=v.unit, mask=v.mask)
        display_name = "Average %s" % self.fields[ftype, fname].display_name
        units = get_units(ftype, fname)
        self.add_derived_field(ftype, "avg_%s" % fname, _avg, units,
                               display_name=display_name, 
                               depends=[(ftype, fname)])

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
        >>> ds.map_state_to_msid("ccd_count", "1dpamzt")
        """
        state = state.lower()
        msid = msid.lower()
        ftype = ftype.lower()
        units = get_units("states", state)
        def _state(ds):
            msid_times = ds.times(ftype, msid)
            state_times = ds.times("states", state)[1]
            indexes = np.searchsorted(state_times, msid_times)
            v = ds["states", state][indexes].value
            if v.dtype.char in ['S', 'U']:
                return APStringArray(v, msid_times)
            else:
                return APQuantity(v, msid_times, unit=units)
        self.add_derived_field(ftype, state, _state, units,
                               display_name=self.fields["states", state].display_name,
                               depends=[(ftype, msid)])

    def add_diff_data_model_field(self, msid, ftype_model="model"):
        r"""

        Create a field which gives the difference between the data
        and the model for a particular MSID.

        Parameters
        ----------
        msid : string
            The MSID to take the diff of data and model of.
        ftype_model : string, optional
            The model type (e.g., "model", "model0", etc.) of
            the model field to be diffed with the MSID.
        """
        msid = msid.lower()
        ftype_model = ftype_model.lower()
        units = get_units("msids", msid)
        def _diff(ds):
            return ds["msids", msid]-ds[ftype_model, msid]
        display_name = self.fields["msids", msid].display_name.replace('_', '\_')
        self.add_derived_field(ftype_model, "diff_%s" % msid, _diff, units,
                               display_name="$\mathrm{\Delta(%s)}$" % display_name,
                               depends=[("msids", msid), (ftype_model, msid)])

    def times(self, *args):
        """
        Return the timing information in seconds from the beginning of the mission
        for a field.

        Examples
        --------
        >>> ds.times("msids", "1deamzt")
        """
        if len(args) > 1:
            field = args[0], args[1]
        else:
            field = args[0]
        ftype, fname = self._determine_field(field)
        if (ftype, fname) not in self._times:
            self._times[ftype, fname] = self[ftype, fname].times
        return self._times[ftype, fname]

    def dates(self, *args):
        """
        Return the timing information in date and time for a field.

        Examples
        --------
        >>> ds.dates("states", "pitch")
        """
        if len(args) > 1:
            field = args[0], args[1]
        else:
            field = args[0]
        ftype, fname = self._determine_field(field)
        if (ftype, fname) not in self._dates:
            self._dates[ftype, fname] = self[ftype, fname].dates
        return self._dates[ftype, fname]

    def write_msids(self, filename, fields, mask=None, overwrite=False):
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
        base_times = self.dates(*fields[0])
        if mask is None:
            mask = slice(None, None, None)
        if len(fields) > 1:
            for field in fields[1:]:
                if not np.all(base_times == self.dates(*field)):
                    raise RuntimeError("To write MSIDs, all of the times should be the same," +
                                       "but '%s', '%s' does not have the same " % field +
                                       "set of times as '%s', '%s'!" % (fields[0][0], fields[0][1]))
        data = dict(("_".join(k), self[k].value[mask]) for k in fields)
        data["times"] = self.times(*fields[0]).value[mask]
        data["dates"] = self.dates(*fields[0])[mask]
        Table(data).write(filename, format='ascii', overwrite=overwrite)

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
        Table(dict((k,v.value) for k, v in self.states.items())).write(filename, 
                                                                       format='ascii',
                                                                       overwrite=overwrite)

    def plot(self, fields, field2=None, lw=2, ls='-', ls2='-', lw2=2,
             fontsize=18, color=None, color2='magenta', figsize=(10, 8),
             plot=None, fig=None, subplot=None, plot_bad=False):
        r""" Make a single-panel plot of a quantity (or multiple quantities) 
        vs. date and time from this Dataset. 

        Multiple quantities can be plotted on the left
        y-axis together if they have the same units, otherwise a quantity
        with different units can be plotted on the right y-axis. 

        Parameters
        ----------
        fields : tuple of strings or list of tuples of strings
            A single field or list of fields to plot on the left y-axis.
        field2 : tuple of strings, optional
            A single field to plot on the right y-axis. Default: None
        lw : float or list of floats, optional
            The width of the lines in the plots. If a list, the length
            of a the list must be equal to the number of fields. If a
            single number, it will apply to all plots. Default: 2 px.
        ls : string, optional
            The line style of the lines plotted on the left y-axis. 
            Can be a single linestyle or more than one for each line. 
            Default: '-'
        ls2 : string, optional
            The line style of the line plotted on the right y-axis. 
            Can be a single linestyle or more than one for each line. 
            Default: '-'
        lw2 : float, optional
            The width of the line plotted on the right y-axis.
        fontsize : integer, optional
            The font size for the labels in the plot. Default: 18 pt.
        color : list of strings, optional
            The colors for the lines plotted on the left y-axis. Can
            be a single color or more than one in a list. Default: 
            Use the default Matplotlib order of colors. 
        color2 : string, optional
            The color for the line plotted on the right y-axis.
            Default: "magenta"
        fig : :class:`~matplotlib.figure.Figure`, optional
            A Figure instance to plot in. Default: None, one will be
            created if not provided.
        figsize : tuple of integers, optional
            The size of the plot in (width, height) in inches. Default: (10, 8)
        plot : :class:`~acispy.plots.DatePlot` or :class:`~acispy.plots.CustomDatePlot`, optional
            An existing DatePlot to add this plot to. Default: None, one 
            will be created if not provided.
        plot_bad : boolean, optional
            If True, "bad" values will be plotted but the ranges of bad values
            will be marked with translucent blue rectangles. If False, bad
            values will be removed from the plot. Default: False
        """
        from acispy.plots import DatePlot
        dp = DatePlot(self, fields, field2=field2, lw=lw, ls=ls, ls2=ls2,
                      lw2=lw2, fontsize=fontsize, color=color, color2=color2,
                      figsize=figsize, plot=plot, fig=fig, subplot=subplot,
                      plot_bad=plot_bad)
        return dp


class EngArchiveData(Dataset):
    """
    Fetch MSIDs from the engineering archive and states from the commanded
    states database.

    Parameters
    ----------
    tstart : string
        The start time in YYYY:DOY:HH:MM:SS format
    tstop : string
        The stop time in YYYY:DOY:HH:MM:SS format
    msids : list of strings, optional
        List of MSIDs to pull from the engineering archive.
    filter_bad : boolean, optional
        Whether or not to filter out bad values of MSIDs. Default: False.
    stat : string, optional
        return 5-minute or daily statistics ('5min' or 'daily') Default: '5min'
        If ``interpolate_msids=True`` this setting is ignored.
    interpolate_msids : boolean, optional
        If True, MSIDs are interpolated to a common time sequence with uniform
        timesteps of 328 seconds. Default: False
    server : string, optional
         DBI server or HDF5 file to grab states from. Default: None, which will
         grab the states from the main commanded states database.

    Examples
    --------
    >>> from acispy import EngArchiveData
    >>> tstart = "2016:091:12:05:00.100"
    >>> tstop = "2016:100:13:07:45.234"
    >>> msids = ["1deamzt", "1pin1at"]
    >>> ds = EngArchiveData(tstart, tstop, msids)
    """
    def __init__(self, tstart, tstop, msids, filter_bad=False, stat=None,
                 interpolate_msids=False, server=None):
        tstart = get_time(tstart)
        tstop = get_time(tstop)
        msids = MSIDs.from_database(msids, tstart, tstop=tstop,
                                    filter_bad=filter_bad, stat=stat,
                                    interpolate=interpolate_msids)
        states = States.from_database(tstart, tstop, server=server)
        model = EmptyTimeSeries()
        super(EngArchiveData, self).__init__(msids, states, model)


class MaudeData(Dataset):
    """
    Fetch MSID data from Maude.

    Parameters
    ----------
    tstart : string
        The start time in YYYY:DOY:HH:MM:SS format
    tstop : string
        The stop time in YYYY:DOY:HH:MM:SS format
    msids : list of strings, optional
        List of MSIDs to pull from the engineering archive.
    user : string, optional
        OCCWEB username to access the MAUDE database with. Default: None,
        which will use the username in the ${HOME}/.netrc file.
    password : string, optional
        OCCWEB password to access the MAUDE database with. Default: None,
        which will use the password in the ${HOME}/.netrc file.
    server : string, optional
        DBI server or HDF5 file to grab states from. Default: None, which will
        grab the states from the main commanded states database.
    """
    def __init__(self, tstart, tstop, msids, user=None, password=None, 
                 server=None, other_msids=None):
        tstart = get_time(tstart)
        tstop = get_time(tstop)
        msids = MSIDs.from_maude(msids, tstart, tstop=tstop, user=user,
                                 password=password)
        if other_msids is not None:
            msids2 = MSIDs.from_database(other_msids, tstart, tstop)
            msids = CombinedMSIDs([msids, msids2])
        states = States.from_database(tstart, tstop, server=server)
        model = EmptyTimeSeries()
        super(MaudeData, self).__init__(msids, states, model)


def _parse_tracelogs(tbegin, tend, filenames, other_msids):
    filenames = ensure_list(filenames)
    if tbegin is not None:
        tbegin = get_time(tbegin)
    if tend is not None:
        tend = get_time(tend)
    msid_objs = []
    for filename in filenames:
        # Figure out what kind of file this is
        f = open(filename, "r")
        line = f.readline()
        f.close()
        if line.startswith("TIME"):
            msids = MSIDs.from_tracelog(filename, tbegin=tbegin, tend=tend)
        elif line.startswith("#YEAR") or line.startswith("YEAR"):
            msids = MSIDs.from_mit_file(filename, tbegin=tbegin, tend=tend)
        else:
            raise RuntimeError("I cannot parse this file!")
        msid_objs.append(msids)
    if other_msids is not None:
        msid_objs.append(MSIDs.from_database(other_msids, tbegin, tend))
    all_msids = CombinedMSIDs(msid_objs)
    return all_msids


class TracelogData(Dataset):
    """
    Fetch MSIDs from a tracelog file and states from the commanded
    states database.

    Parameters
    ----------
    filenames : string or list of strings
        The path to the tracelog file or list of tracelog files
    tbegin : string
        The start time in YYYY:DOY:HH:MM:SS format. Default: None, which
        will read from the beginning of the tracelog.
    tend : string
        The stop time in YYYY:DOY:HH:MM:SS format.  Default: None, which
        will read from the beginning of the tracelog.
    server : string, optional
        DBI server or HDF5 file to grab states from. Default: None, which will
        grab the states from the main commanded states database.

    Examples
    --------
    >>> from acispy import TracelogData
    >>> ds = TracelogData("acisENG10d_00985114479.70.tl")
    """
    def __init__(self, filenames, tbegin=None, tend=None, server=None,
                 other_msids=None):
        msids = _parse_tracelogs(tbegin, tend, filenames, other_msids)
        tmin = 1.0e55
        tmax = -1.0e55
        for v in msids.values():
            tmin = min(v.times[0].value, tmin)
            tmax = max(v.times[-1].value, tmax)
        states = States.from_database(secs2date(tmin), secs2date(tmax), 
                                      server=server)
        model = EmptyTimeSeries()
        super(TracelogData, self).__init__(msids, states, model)


class EngineeringTracelogData(TracelogData):
    """
    Fetch MSIDs from the engineering tracelog file and states from
    the commanded states database.

    Parameters
    ----------
    tbegin : string
        The start time in YYYY:DOY:HH:MM:SS format. Default: None, which
        will read from the beginning of the tracelog.
    tend : string
        The stop time in YYYY:DOY:HH:MM:SS format.  Default: None, which
        will read from the beginning of the tracelog.
    server : string, optional
        DBI server or HDF5 file to grab states from. Default: None, which will
        grab the states from the main commanded states database.
    """
    def __init__(self, tbegin=None, tend=None, server=None, other_msids=None):
        filename = "/data/acis/eng_plots/acis_eng_10day.tl"
        super(EngineeringTracelogData, self).__init__(filename, tbegin=tbegin, tend=tend,
                                                      server=server, 
                                                      other_msids=other_msids)


class DEAHousekeepingTracelogData(TracelogData):
    """
    Fetch MSIDs from the DEA housekeeping tracelog file and states from
    the commanded states database.

    Parameters
    ----------
    tbegin : string
        The start time in YYYY:DOY:HH:MM:SS format. Default: None, which
        will read from the beginning of the tracelog.
    tend : string
        The stop time in YYYY:DOY:HH:MM:SS format.  Default: None, which
        will read from the beginning of the tracelog.
    server : string, optional
        DBI server or HDF5 file to grab states from. Default: None, which will
        grab the states from the main commanded states database.
    """
    def __init__(self, tbegin=None, tend=None, server=None, other_msids=None):
        filename = "/data/acis/eng_plots/acis_dea_10day.tl"
        super(DEAHousekeepingTracelogData, self).__init__(filename, tbegin=tbegin,
                                                          tend=tend, server=server,
                                                          other_msids=other_msids)


class TenDayTracelogData(TracelogData):
    """
    Fetch MSIDs from both the engineering and DEA housekeeping
    tracelog files in one dataset.

    Parameters
    ----------
    tbegin : string
        The start time in YYYY:DOY:HH:MM:SS format. Default: None, which
        will read from the beginning of the tracelog.
    tend : string
        The stop time in YYYY:DOY:HH:MM:SS format.  Default: None, which
        will read from the beginning of the tracelog.
    server : string, optional
        DBI server or HDF5 file to grab states from. Default: None, which will
        grab the states from the main commanded states database.
    """
    def __init__(self, tbegin=None, tend=None, server=None, other_msids=None):
        filenames = ["/data/acis/eng_plots/acis_eng_10day.tl",
                     "/data/acis/eng_plots/acis_dea_10day.tl"]
        super(TenDayTracelogData, self).__init__(filenames, tbegin=tbegin,
                                                 tend=tend, server=server,
                                                 other_msids=other_msids)


class TelemData(Dataset):
    """
    Fetch MSID data from the Ska engineering archive
    as well as either Maude or one of the tracelog
    files, in order to ensure the most recent data
    is obtained.

    Parameters
    ----------
    tstart : string
        The start time in YYYY:DOY:HH:MM:SS format
    tstop : string
        The stop time in YYYY:DOY:HH:MM:SS format
    msids : list of strings, optional
        List of MSIDs to pull from the engineering archive.
    recent_source : string, optional
        Which source to use to get the most recent tracelog data.
        Options are "maude" or "tracelog". Default: "tracelog"
    filter_bad : boolean, optional
        Whether or not to filter out bad values of MSIDs. Default: False.
    stat : string, optional
        return 5-minute or daily statistics ('5min' or 'daily') Default: '5min'
        If ``interpolate_msids=True`` this setting is ignored.
    interpolate_msids : boolean, optional
        If True, MSIDs are interpolated to a common time sequence with uniform
        timesteps of 328 seconds. Default: False
    user : string, optional
        OCCWEB username to access the MAUDE database with. Default: None,
        which will use the username in the ${HOME}/.netrc file.
    password : string, optional
        OCCWEB password to access the MAUDE database with. Default: None,
        which will use the password in the ${HOME}/.netrc file.
    server : string, optional
        DBI server or HDF5 file to grab states from. Default: None, which will
        grab the states from the main commanded states database.
    """
    def __init__(self, tstart, tstop, msids, recent_source="tracelog",
                 filter_bad=False, stat=None, interpolate_msids=False,
                 user=None, password=None, server=None):
        msids = ensure_list(msids)
        tstart = get_time(tstart, fmt='secs')
        tstop = get_time(tstop, fmt='secs')
        tmid = 1.0e99
        for msid in msids:
            tm = fetch.get_time_range(msid, format="secs")[-1]
            tmid = min(tmid, tm)
        tmid = get_time(tmid, fmt='secs')
        if tmid < tstop:
            msids1 = MSIDs.from_database(msids, tstart, tstop=tmid,
                                         filter_bad=filter_bad, stat=stat,
                                         interpolate=interpolate_msids)
            if recent_source == "maude":
                msids2 = MSIDs.from_maude(msids, tmid, tstop=tstop, user=user,
                                          password=password)
            elif recent_source == "tracelog":
                msids2 = _parse_tracelogs(tmid, tstop,
                                          ["/data/acis/eng_plots/acis_eng_10day.tl",
                                           "/data/acis/eng_plots/acis_dea_10day.tl"],
                                          None)
            msids = ConcatenatedMSIDs(msids1, msids2)
        else:
            msids = MSIDs.from_database(msids, tstart, tstop=tstop,
                                        filter_bad=filter_bad, stat=stat,
                                        interpolate=interpolate_msids)
        states = States.from_database(tstart, tstop, server=server)
        model = EmptyTimeSeries()
        super(TelemData, self).__init__(msids, states, model)
