import os
from acispy.dataset import ModelDataFromLoad
from acispy.plots import DatePlot, MultiDatePlot
from acispy.utils import get_time
from collections import defaultdict
from Chandra.Time import date2secs, secs2date
from Ska.Matplotlib import cxctime2plotdate
import numpy as np

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

offsets = {"sim_trans": 0.75}

cti_simodes = ["TE_007AC", "TE_00B26", "TE_007AE",
               "TE_00CA8", "TE_00C60", "TE_007AE",
               "TN_000B4", "TN_000B6"]

class LoadReviewEvent(object):
    def __init__(self, name, event):
        self.event = event
        self.name = name

    def __repr__(self):
        return self.name

    def __getattr__(self, item):
        return self.event[item]

class LoadReview(object):
    def __init__(self, load_name, get_msids=False,
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
        oflsdir = os.path.join(lr_root, self.load_year,
                               self.load_week, oflsdir)
        self.load_file = os.path.join(oflsdir, lr_file)
        self.load_letter = os.path.realpath(oflsdir)[-1]
        self.load_name = self.load_week + self.load_letter.upper()
        self.events = defaultdict(dict)
        self.start_status = self._get_start_status()
        self._populate_event_times()
        self.ds = ModelDataFromLoad(self.load_name, get_msids=get_msids,
                                    interpolate_msids=True, tl_file=tl_file,
                                    time_range=[self.first_time, self.last_time])
        self._find_cti_runs()

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
        status = status.strip("()").split(",")
        return status

    def _populate_event_times(self):
        with open(self.load_file, "r") as f:
            for i, line in enumerate(f.readlines()):
                words = line.strip().split()
                if len(words) > 0:
                    event = None
                    state = None
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
                        else:
                            time = words[0]
                        self.events[event]["times"].append(time)
                        if state is not None:
                            if "state" not in self.events[event]:
                                self.events[event]["state"] = []
                            self.events[event]["state"].append(state)

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

    def __getattr__(self, item):
        return LoadReviewEvent(item, self.events[item])

    def _add_annotations(self, plot, annotations, tbegin, tend):
        for i, line in enumerate(plot.ax.lines):
            line.set_zorder(100-i)
        plot_comms = False
        plot_belts = False
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
             colors=None, color2='magenta', fig=None, ax=None,
             tbegin=None, tend=None, annotations=None, ymin=None,
             ymax=None, ymin2=None, ymax2=None):
        dp = DatePlot(self.ds, fields, field2=field2, lw=lw,
                      fontsize=fontsize, colors=colors, color2=color2,
                      fig=fig, ax=ax)
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
            self._add_annotations(dp, annotations, tbegin, tend)
        dp.set_xlim(secs2date(tbegin), secs2date(tend))
        return dp
