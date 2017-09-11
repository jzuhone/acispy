from __future__ import print_function
import os
from acispy.dataset import ModelDataFromLoad
from acispy.plots import DatePlot
from acispy.utils import get_time
from collections import defaultdict
from Chandra.Time import date2secs, secs2date
from Ska.Matplotlib import cxctime2plotdate
import numpy as np
from datetime import datetime, timezone
import bisect

lr_root = "/data/acis/LoadReviews"
lr_file = "ACIS-LoadReview.txt"

colors = {"perigee": "dodgerblue",
          "apogee": "dodgerblue",
          "sim_trans": "brown",
          "radmon_disable": "orange",
          "radmon_enable": "orange",
          "start_cti": "darkgreen",
          "end_cti": "darkgreen"}

styles = {"perigee": "--",
          "apogee": ":",
          "sim_trans": "-",
          "radmon_enable": "--",
          "radmon_disable": "--",
          "start_cti": '--',
          "end_cti": '--'}

pretty_names = {"comm_ends": "End of Comm",
                "comm_begins": "Beginning of Comm",
                "perigee": "Perigee",
                "apogee": "Apogee",
                "letg_in": "LETG Inserted",
                "letg_out": "LETG Retracted",
                "hetg_in": "HETG Inserted",
                "hetg_out": "HETG Retracted",
                "radmon_enable": "Enable Radiation Monitor",
                "radmon_disable": "Disable Radiation Monitor",
                "start_cti": "Start CTI Run",
                "end_cti": "End CTI Run",
                "obsid_change": "Change of OBSID",
                "sim_trans": "SIM Translation",
                "enter_belts": "Enter Radiation Belts",
                "exit_belts": "Exit Radiation Belts",
                "fmt_change": "Change of Telemetry Format"}

offsets = {"sim_trans": 0.75}

cti_simodes = ["TE_007AC", "TE_00B26", "TE_007AE",
               "TE_00CA8", "TE_00C60", "TE_007AE",
               "TN_000B4", "TN_000B6"]

class LoadReviewEvent(object):
    def __init__(self, name, event):
        self.event = event
        self.name = name

    def __str__(self):
        return self.name

    def __repr__(self):
        return pretty_names[self.name]

    def __getattr__(self, item):
        return self.event[item]

class ACISLoadReview(object):
    """
    Parse data from a particular load review for 
    access and plotting of data.

    Parameters
    ----------
    load_name : string
        The name of the load to examine. Can be the full
        load specification, e.g. "AUG2717A", or the last
        letter can be omitted for the latest iteration,
        e.g. "MAY0216".
    get_msids : boolean, optional
        Whether or not to load MSID data as well as model
        data for temperatures. Default: False
    tl_file : string, optional
        If MSID data is to be loaded, load from this 
        tracelog file rather than the engineering archive.
        Default: None
    """
    def __init__(self, load_name, get_msids=True,
                 tl_file=None):
        self.load_name = load_name
        if len(load_name) == 7:
            self.load_week = load_name
            oflsdir = "ofls"
        else:
            self.load_week = load_name[:-1]
            oflsdir = "ofls%s" % load_name[-1].lower()
        self.load_year = "20%s" % self.load_week[5:7]
        self.next_year = str(int(self.load_year)+1)
        loaddir = os.path.join(lr_root, self.load_year, self.load_week)
        oflsdir = os.path.join(loaddir, oflsdir)
        self.load_file = os.path.join(oflsdir, lr_file)
        self.load_letter = sorted(os.listdir(loaddir))[-1][-1].upper()
        self.load_name = self.load_week + self.load_letter
        self.events = defaultdict(dict)
        self.start_status = self._get_start_status()
        self.begin_radzone = int(self.start_status['radmon_status'] == "OORMPDS")
        self.lines, self.line_times = self._populate_event_times()
        self.ds = ModelDataFromLoad(self.load_name, get_msids=get_msids,
                                    interpolate_msids=True, tl_file=tl_file,
                                    time_range=[self.first_time, self.last_time])
        self._find_cti_runs()

    def __repr__(self):
        return self.load_name

    def __str__(self):
        return self.load_name

    def _get_start_status(self):
        j = -1
        find_first_time = True
        time = None
        with open(self.load_file, "r") as f:
            for i, line in enumerate(f.readlines()):
                words = line.strip().split()
                if len(words) > 0:
                    if (line.startswith(self.load_year) or
                        line.startswith(self.next_year)):
                        time = words[0]
                    if find_first_time and time is not None:
                        self.first_time = time
                        find_first_time = False
                    if line.startswith("CHANDRA STATUS ARRAY"):
                        j = i+2
                    if i == j:
                        status = line.strip().split()[-1]
        self.last_time = time
        status_values = status.strip("()").split(",")
        status = {"instrument": status_values[0],
                  "hetg_status": status_values[1],
                  "letg_status": status_values[2],
                  "current_obsid": status_values[3],
                  "radmon_status": status_values[4],
                  "telemetry_format": status_values[5],
                  "dither_status": status_values[6]}
        return status

    def _populate_event_times(self):
        lines = []
        line_times = []
        time = self.first_time
        comm_durations = []
        with open(self.load_file, "r") as f:
            for i, line in enumerate(f.readlines()):
                words = line.strip().split()
                if len(words) > 0:
                    event = None
                    state = None
                    if line.startswith(self.load_year) or \
                        line.startswith(self.next_year):
                        time = words[0]
                    if "MP_OBSID" in line:
                        event = "obsid_change"
                        state = words[-1]
                    if "SIMTRANS" in line:
                        event = "sim_trans"
                        state = (int(words[-2]), words[-1].strip("()"))
                    if "HETGIN" in line:
                        event = "hetg_in"
                    if "HETGRE" in line:
                        event = "hetg_out"
                    if "LETGIN" in line:
                        event = "letg_in"
                    if "LETGRE" in line:
                        event = "letg_out"
                    if "CSELFMT" in line and "COMMAND_HW" in line:
                        event = "fmt_change"
                        state = int(words[-1][-1])
                    if "EPERIGEE" in line and "ORBPOINT" in line:
                        event = "perigee"
                    if "APOGEE" in line and "ORBPOINT" in line:
                        event = "apogee"
                    if "COMM BEGINS" in line:
                        event = "comm_begins"
                    if "COMM ENDS" in line:
                        event = "comm_ends"
                    if "EEF1000" in line and "ORBPOINT" in line:
                        event = "enter_belts"
                    if "XEF1000" in line and "ORBPOINT" in line:
                        event = "exit_belts"
                    if "OORMPDS" in line and "COMMAND_SW" in line:
                        event = "radmon_disable"
                    if "OORMPEN" in line and "COMMAND_SW" in line:
                        event = "radmon_enable"
                    if event is not None:
                        if event not in self.events:
                            self.events[event] = {"times": []}
                        if event == "comm_ends":
                            time = secs2date(date2secs(words[0])-1800.0)
                        self.events[event]["times"].append(time)
                        if state is not None:
                            if "state" not in self.events[event]:
                                self.events[event]["state"] = []
                            self.events[event]["state"].append(state)
                    if "REAL-TIME COMM" in line:
                        continue
                    if "COMM DURATION" in line:
                        comm_durations.append(float(words[-2])-30.0)
                        continue
                    if line.startswith(self.load_year) or \
                        line.startswith(self.next_year) or \
                        "WSPOW COMMAND LOADS" in line or \
                        "CHANDRA STATUS ARRAY" in line or \
                        "ACIS integration time" in line or \
                        "requested time" in line or \
                        "ObsID change" in line or \
                        "THERE IS A Z-SIM" in line or \
                        "==> DITHER" in line:
                        lines.append(line)
                        line_times.append(time)
        line_times = date2secs(line_times)
        lines, line_times = self._fix_comm_times(lines, line_times, comm_durations)
        return lines, line_times

    def _find_cti_runs(self):
        self.events["start_cti"] = {"times": [], "state": []}
        self.events["end_cti"] = {"times": [], "state": []}
        si_modes = self.ds["si_mode"]
        power_cmds = self.ds["power_cmd"]
        for mode in cti_simodes:
            where_mode = np.logical_and(si_modes == mode, 
                                        power_cmds == "XTZ0000005")
            idxs = np.concatenate([[False], where_mode, [False]])
            idxs = np.flatnonzero(idxs[1:] != idxs[:-1]).reshape(-1, 2)
            for ii, jj in idxs:
                self.events["start_cti"]["times"].append(si_modes.dates[0,ii])
                self.events["end_cti"]["times"].append(si_modes.dates[0,jj+1])
                self.events["start_cti"]["state"].append(mode)
                self.events["end_cti"]["state"].append(mode)

    def list_attributes(self):
        for key in self.events.keys():
            print("%s: %s" % (key, pretty_names[key]))

    def get_updated_dsn_comms(self):
        dsnfile = "/data/acis/dsn_summary.dat"
        tstart = date2secs(self.first_time)
        tstop = date2secs(self.last_time)
        bots = []
        eots = []
        new_durations = []
        with open(dsnfile) as f:
            for line in f.readlines()[2:]:
                words = line.strip().split()
                bot = datetime.strptime("%s:%s:00:00:00" % (words[-4], words[-3][:3]), "%Y:%j:%H:%M:%S")
                eot = datetime.strptime("%s:%s:00:00:00" % (words[-2], words[-1][:3]), "%Y:%j:%H:%M:%S")
                time_bot = date2secs(bot.strftime("%Y:%j:%H:%M:%S"))+86400.0*(float(words[-3]) % 1)
                time_eot = date2secs(eot.strftime("%Y:%j:%H:%M:%S"))+86400.0*(float(words[-1]) % 1)
                new_durations.append((time_eot-time_bot)/60.0)
                if tstart <= time_bot <= tstop:
                    bots.append(time_bot)
                if tstart <= time_eot <= tstop:
                    eots.append(time_eot)
        self.events["comm_begins"]["times"] = secs2date(bots)
        self.events["comm_ends"]["times"] = secs2date(eots)
        self.lines, self.line_times = self._fix_comm_times(self.lines, self.line_times, new_durations)

    def _fix_comm_times(self, lines, line_times, comm_durations):
        new_lines = []
        new_times = []
        for i, line in enumerate(lines):
            if not "REAL-TIME COMM" in line and not "COMM DURATION" in line:
                new_lines.append(line)
                new_times.append(line_times[i])
        for time in self.events["comm_begins"]["times"]:
            local_time = datetime.strptime(time, "%Y:%j:%H:%M:%S.%f").replace(tzinfo=timezone.utc).astimezone(tz=None)
            t = date2secs(time)
            idx = bisect.bisect_right(new_times, t)
            new_times.insert(idx, t)
            new_lines.insert(idx, "%s   REAL-TIME COMM BEGINS   %s  EDT" % (time, local_time.strftime("%Y:%j:%H:%M:%S")))
        for i, time in enumerate(self.events["comm_ends"]["times"]):
            local_time = datetime.strptime(time, "%Y:%j:%H:%M:%S.%f").replace(tzinfo=timezone.utc).astimezone(tz=None)
            t = date2secs(time)
            idx = bisect.bisect_right(new_times, t)
            new_times.insert(idx, t)
            new_lines.insert(idx, "%s   REAL-TIME COMM ENDS     %s  EDT" % (time, local_time.strftime("%Y:%j:%H:%M:%S")))
            new_times.insert(idx+1, t)
            new_lines.insert(idx+1, "==> COMM DURATION:  %g mins." % comm_durations[i])
        return new_lines, new_times

    def __getattr__(self, item):
        if item in self.events:
            return LoadReviewEvent(item, self.events[item])
        else:
            raise AttributeError("'LoadReview' object has no attribute '%s'" % item)

    def _add_annotations(self, plot, annotations, tbegin, tend):
        for i, line in enumerate(plot.ax.lines):
            line.set_zorder(100-i)
        plot_comms = False
        plot_belts = False
        if "cti_runs" in annotations:
            annotations.append("start_cti")
            annotations.append("end_cti")
            annotations.remove("cti_runs")
        for key in annotations:
            if key == "comms":
                plot_comms = True
                continue
            if key == "belts":
                plot_belts = True
                continue
            color = colors[key]
            ls = styles[key]
            for i, t in enumerate(self.events[key]["times"]):
                tt = date2secs(t)
                if tt < tbegin or tt > tend:
                    continue
                plot.add_vline(t, color=color, ls=ls)
                if "state" in self.events[key] and key in offsets:
                    text = self.events[key]["state"][i]
                    if isinstance(text, tuple):
                        text = text[-1]
                    tdt = secs2date(tt + 1800.0)
                    ymin, ymax = plot.ax.get_ylim()
                    y = (1.0-offsets[key])*ymin+offsets[key]*ymax
                    plot.add_text(tdt, y, text, fontsize=15,
                                  rotation='vertical', color=color)

        if plot_belts:
            self._plot_bands(tbegin, tend, plot,
                             ["radmon_disable", "radmon_enable"], 
                             "mediumpurple", alpha=0.333333)

        if plot_comms:
            self._plot_bands(tbegin, tend, plot,
                             ["comm_begins", "comm_ends"], "pink",
                             alpha=1.0)


    def _plot_bands(self, tbegin, tend, plot, events, color, alpha=1.0):
        tc_start = list(self.events[events[0]]["times"])
        tc_end = list(self.events[events[1]]["times"])
        if tc_end[0] < tc_start[0]:
            tc_start.insert(0, self.first_time)
        if tc_start[-1] > tc_end[-1]:
            tc_end.append(self.last_time)
        assert len(tc_start) == len(tc_end)
        tc_start = date2secs(tc_start)
        tc_end = date2secs(tc_end)
        ybot, ytop = plot.ax.get_ylim()
        t = np.linspace(tbegin, tend, 500)
        tplot = cxctime2plotdate(t)
        for tcs, tce in zip(tc_start, tc_end):
            in_evt = (t >= tcs) & (t <= tce)
            plot.ax.fill_between(tplot, ybot, ytop,
                                 where=in_evt, color=color,
                                 alpha=alpha)

    def plot(self, fields, field2=None, lw=1.5, fontsize=18,
             colors=None, color2='magenta', figsize=(10, 8), 
             plot=None, tbegin=None, tend=None, annotations=None, 
             ymin=None, ymax=None, ymin2=None, ymax2=None):
        """
        Plot temperature and state data from a load review.

        Parameters
        ----------
        fields : tuple of strings or list of tuples of strings
            A single field or list of fields to plot on the left y-axis.
        field2 : tuple of strings, optional
            A single field to plot on the right y-axis. Default: None
        lw : float, optional
            The width of the lines in the plots. Default: 1.5 px.
        fontsize : integer, optional
            The font size for the labels in the plot. Default: 18 pt.
        colors : list of strings, optional
            The colors for the lines plotted on the left y-axis.
            Default: ["blue", "red", "green", "black"]
        color2 : string, optional
            The color for the line plotted on the right y-axis.
            Default: "magenta"
        figsize : tuple of integers, optional
            The size of the plot in (width, height) in inches. Default: (10, 8)
        plot : :class:`~acispy.plots.DatePlot` or :class:`~acispy.plots.CustomDatePlot`, optional
            An existing DatePlot to add this plot to. Default: None, one 
            will be created if not provided.
        tbegin : string, optional
            The start time of the plot. Default is to plot from the
            beginning of the load. 
        tend : string, optional
            The end time of the plot. Default is to plot to the
            ending of the load.
        annotations : list of strings, optional
            Additional annotations to add to the plot. Available options
            are "cti_runs", "comms", "belts", "perigee", "sim_trans",
            and "apogee". Default: None
        ymin : float, optional
            Set the minimum value of the y-axis on the left side of the 
            plot.
        ymax : float, optional
            Set the maximum value of the y-axis on the left side of the 
            plot.
        ymin2 : float, optional
            Set the minimum value of the y-axis on the right side of the 
            plot.
        ymax2 : float, optional
            Set the maximum value of the y-axis on the right side of the 
            plot.
        """
        dp = DatePlot(self.ds, fields, field2=field2, lw=lw,
                      fontsize=fontsize, colors=colors, color2=color2,
                      figsize=figsize, plot=plot)
        ylimits = dp.ax.get_ylim()
        if ymin is None:
            ymin = ylimits[0]
        if ymax is None:
            ymax = ylimits[1]
        dp.set_ylim(ymin, ymax)
        if field2 is not None:
            ylimits2 = dp.ax2.get_ylim()
            if ymin2 is None:
                ymin2 = ylimits2[0]
            if ymax2 is None:
                ymax2 = ylimits2[1]
            dp.set_ylim2(ymin2, ymax2)
        if tbegin is None:
            tbegin = self.first_time
        if tend is None:
            tend = self.last_time
        tbegin = get_time(tbegin).secs
        tend = get_time(tend).secs
        if annotations is not None:
            self._add_annotations(dp, annotations.copy(), tbegin, tend)
        dp.set_xlim(secs2date(tbegin), secs2date(tend))
        return dp
