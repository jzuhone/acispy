import os
from acispy.dataset import ModelDataFromLoad
from acispy.plots import DatePlot, MultiDatePlot
from collections import defaultdict
from Chandra.Time import date2secs, secs2date

lr_root = "/data/acis/LoadReviews"
lr_file = "ACIS-LoadReview.txt"

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
                                    interpolate_msids=True)

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
                        event = "sim_translation"
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
                        self.events[event]["times"].append(words[0])
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

    def plot(self, fields, field2=None, lw=1.5, fontsize=18,
             colors=None, color2='magenta', fig=None, ax=None):
        dp = DatePlot(self.ds, fields, field2=field2, lw=lw,
                      fontsize=fontsize, colors=colors, color2=color2,
                      fig=fig, ax=ax)
        return dp

    def multi_plot(self, fields, subplots=None,
                   fontsize=15, lw=1.5, fig=None):
        mdp = MultiDatePlot(self.ds, fields, subplots=subplots,
                            fontsize=fontsize, lw=lw, fig=fig)
        return mdp