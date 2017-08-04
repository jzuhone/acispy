import os
from acispy.dataset import ModelDataFromLoad
from acispy.plots import DatePlot, MultiDatePlot
from collections import defaultdict
from Chandra.Time import date2secs, secs2date
from Ska.Matplotlib import cxctime2plotdate
import numpy as np

lr_root = "/data/acis/LoadReviews"
lr_file = "ACIS-LoadReview.txt"

colors = {"perigee": "dodgerblue",
          "apogee": "fuchsia",
          "sim_trans": "brown",
          "radmon_disable": "orange",
          "radmon_enable": "orange"}

styles = {"perigee": "--",
          "apogee": "--",
          "sim_trans": "-",
          "radmon_enable": "--",
          "radmon_disable": "--"}

offsets = {"sim_trans": 0.75}

class LoadReviewEvent(object):
    def __init__(self, name, event):
        self.event = event
        self.name = name

    def __repr__(self):
        return self.name

    def __getattr__(self, item):
        return self.event[item]

class LoadReview(object):
    def __init__(self, load_name, get_msids=False):
        self.load_name = load_name
        self.load_week = load_name[:-1]
        self.load_year = "20%s" % self.load_week[5:7]
        self.load_letter = load_name[-1].lower()
        self.load_file = os.path.join(lr_root, self.load_year, 
                                      self.load_week,
                                      "ofls%s" % self.load_letter,
                                      lr_file)
        self.events = defaultdict(dict)
        self.first_time = 1.0e20
        self.last_time = 0.0
        self.start_status = self._get_start_status()
        self._populate_event_times()
        self.first_time = secs2date(self.first_time)
        self.last_time = secs2date(self.last_time)
        self.ds = ModelDataFromLoad(load_name, get_msids=get_msids,
                                    interpolate_msids=True,
                                    time_range=[self.first_time, 
                                                self.last_time])

    def _get_start_status(self):
        j = -1
        with open(self.load_file, "r") as f:
            for i, line in enumerate(f.readlines()):
                words = line.strip().split()
                if len(words) > 0:
                    if line.startswith("CHANDRA STATUS ARRAY"):
                        j = i+2
                    if i == j:
                        status = line.strip().split()[-1]
                        break
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
                        if event == "comm_begins":
                            time = secs2date(date2secs(words[0])+1800.0)
                        else:
                            time = words[0]
                        self.events[event]["times"].append(time)
                        time = date2secs(words[0])
                        if time < self.first_time:
                            self.first_time = time
                        if time > self.last_time:
                            self.last_time = time
                        if state is not None:
                            if "state" not in self.events[event]:
                                self.events[event]["state"] = []
                            self.events[event]["state"].append(state)

    def __getattr__(self, item):
        return LoadReviewEvent(item, self.events[item])

    def _add_annotations(self, plot, annotations, tbegin, tend):
        if hasattr(plot, "plots"):
            plots = list(plot.plots.values())
        else:
            plots = [plot]
        for p in plots:
            for i, line in enumerate(p.ax.lines):
                line.set_zorder(100-i)
        plot_comms = False
        for key in annotations:
            if key == "comms":
                plot_comms = True
                continue
            color = colors[key]
            ls = styles[key]
            for i, t in enumerate(self.events[key]["times"]):
                tt = date2secs(t)
                if tt < tbegin or tt > tend:
                    continue
                plot.add_vline(t, color=color, ls=ls)
                if "state" in self.events[key]:
                    text = self.events[key]["state"][i]
                    if isinstance(text, tuple):
                        text = text[-1]
                    tdt = secs2date(tt + 3600.0)
                    y = offsets[key]*np.sum(plots[0].ax.get_ylim())
                    plots[0].add_text(tdt, y, text,
                                      fontsize=15,
                                      rotation='vertical',
                                      color=color)
        if plot_comms:
            tc_start = list(self.events["comm_begins"]["times"])
            tc_end = list(self.events["comm_ends"]["times"])
            if tc_end[0] < tc_start[0]:
                tc_start.insert(0, self.first_time)
            if tc_start[-1] > tc_end[-1]:
                tc_end.append(self.last_time)
            assert len(tc_start) == len(tc_end)
            tc_start = date2secs(tc_start)
            tc_end = date2secs(tc_end)
            for p in plots:
                ybot, ytop = p.ax.get_ylim()
                t = np.linspace(tbegin, tend, 500)
                tplot = cxctime2plotdate(t)
                for tcs, tce in zip(tc_start, tc_end):
                    in_comm = (t >= tcs) & (t <= tce)
                    p.ax.fill_between(tplot, ybot, ytop, 
                                      where=in_comm, color='pink')

    def plot(self, fields, field2=None, lw=1.5, fontsize=18,
             colors=None, color2='magenta', fig=None, ax=None,
             tbegin=None, tend=None, annotations=None):
        dp = DatePlot(self.ds, fields, field2=field2, lw=lw,
                      fontsize=fontsize, colors=colors, color2=color2,
                      fig=fig, ax=ax)
        if tbegin is None:
            tbegin = self.first_time
        tbegin = date2secs(tbegin)
        if tend is None:
            tend = self.last_time
        tend = date2secs(tend)
        if annotations is not None:
            self._add_annotations(dp, annotations, tbegin, tend)
        return dp

    def multi_plot(self, fields, subplots=None,
                   fontsize=15, lw=1.5, fig=None,
                   tbegin=None, tend=None, annotations=None):
        mdp = MultiDatePlot(self.ds, fields, subplots=subplots,
                            fontsize=fontsize, lw=lw, fig=fig)
        if tbegin is None:
            tbegin = self.first_time
        tbegin = date2secs(tbegin)
        if tend is None:
            tend = self.last_time
        tend = date2secs(tend)
        if annotations is not None:
            self._add_annotations(mdp, annotations, tbegin, tend)
        return mdp