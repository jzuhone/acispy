from Ska.Matplotlib import plot_cxctime
from matplotlib import font_manager
import matplotlib.pyplot as plt
from matplotlib.dates import num2date
from acis.utils import state_labels, msid_units
from Chandra.Time import DateTime
from datetime import datetime
import numpy as np

def pointpair(x, y=None):
    if y is None:
        y = x
    return np.array([x, y]).reshape(-1, order='F')

drawstyles = {"simpos": "steps",
              "pitch": "steps",
              "ccd_count": "steps"}

type_map = {"$\mathrm{^\circ{C}}$": "Temperature",
            "V": "Voltage",
            "A": "Current"}

default_colors = ["b","r","g","k"]

class DatePlot(object):
    def __init__(self, ds, fields, field2=None, fig=None, ax=None, lw=2,
                 fontsize=18, colors=None, color2='magenta'):
        if fig is None:
            fig = plt.figure(figsize=(10, 8))
        if colors is None:
            colors = default_colors
        if not isinstance(fields, list):
            fields = [fields]
        for i, field in enumerate(fields):
            src_name, fd = field
            src = getattr(ds, src_name)
            drawstyle = drawstyles.get(fd, None)
            if src_name == "states":
                x = pointpair(src["tstart"], src["tstop"])
                y = pointpair(src[fd])
            else:
                x = src.time
                y = src[fd]
            ticklocs, fig, ax = plot_cxctime(x, y, fig=fig, lw=lw, ax=ax,
                                             color=colors[i],
                                             drawstyle=drawstyle, 
                                             label="%s %s" % (src_name, fd.upper()))
        if len(fields) > 1:
            ax.legend(prop={"family": "serif"})
        self.ticklocs = ticklocs
        self.fig = fig
        self.ax = ax
        self.ax.set_xlabel("Date", fontdict={"size": fontsize,
                                             "family": "serif"})
        fontProperties = font_manager.FontProperties(family="serif",
                                                     size=fontsize)
        for label in self.ax.get_xticklabels():
            label.set_fontproperties(fontProperties)
        for label in self.ax.get_yticklabels():
            label.set_fontproperties(fontProperties)
        if len(fields) > 1:
            self.set_ylabel(type_map[msid_units[fields[0][1]]]+" (%s)" % msid_units[fields[0][1]])
        else:
            if fd in state_labels:
                self.set_ylabel(state_labels[fd])
            elif fd in msid_units:
                self.set_ylabel(fd.upper()+" (%s)" % msid_units[fd])
            else:
                self.set_ylabel(fd.upper())
        if field2 is not None:
            src_name2, fd2 = field2
            src2 = getattr(ds, src_name2)
            self.ax2 = self.ax.twinx()
            drawstyle = drawstyles.get(fd2, None)
            if src_name2 == "states":
                x = pointpair(src2["tstart"], src2["tstop"])
                y = pointpair(src2[fd2])
            else:
                x = src2.time
                y = src2[fd2]
            plot_cxctime(x, y, fig=fig, ax=self.ax2, lw=lw,
                         drawstyle=drawstyle, color=color2)
            for label in self.ax2.get_xticklabels():
                label.set_fontproperties(fontProperties)
            for label in self.ax2.get_yticklabels():
                label.set_fontproperties(fontProperties)
            if fd2 in state_labels:
                self.set_ylabel2(state_labels[fd2])
            elif fd2 in msid_units:
                self.set_ylabel(fd2.upper()+" (%s)" % msid_units[fd])
            else:
                self.set_ylabel(fd2.upper())
        ymin, ymax = self.ax.get_ylim()
        self.set_ylim(ymin*0.9, ymax*1.1)
        if hasattr(self, 'ax2'):
            ymin2, ymax2 = self.ax2.get_ylim()
            self.set_ylim2(ymin2*0.9, ymax2*1.1)

    def set_xlim(self, xmin, xmax):
        if not isinstance(xmin, datetime):
            xmin = datetime.strptime(DateTime(xmin).iso, "%Y-%m-%d %H:%M:%S.%f")
        if not isinstance(xmax, datetime):
            xmax = datetime.strptime(DateTime(xmax).iso, "%Y-%m-%d %H:%M:%S.%f")
        self.ax.set_xlim(xmin, xmax)

    def set_ylim(self, ymin, ymax):
        self.ax.set_ylim(ymin, ymax)

    def set_ylim2(self, ymin, ymax):
        self.ax2.set_ylim(ymin, ymax)

    def set_ylabel(self, ylabel, fontdict=None, **kwargs):
        if fontdict is None:
            fontdict = {"size": 18, "family": "serif"}
        self.ax.set_ylabel(ylabel, fontdict=fontdict, **kwargs)

    def set_ylabel2(self, ylabel, fontdict=None, **kwargs):
        if fontdict is None:
            fontdict = {"size": 18, "family": "serif"}
        self.ax2.set_ylabel(ylabel, fontdict=fontdict, **kwargs)

    def savefig(self, filename, **kwargs):
        self.fig.savefig(filename, **kwargs)

class MultiDatePlot(object):
    def __init__(self, ds, fields, fig=None, subplots=None,
                 fontsize=15):
        if fig is None:
            fig = plt.figure(figsize=(12, 12))
        if subplots is None:
            subplots = len(fields), 1
        self.plots = []
        for i, field in enumerate(fields):
            ax = fig.add_subplot(subplots[0], subplots[1], i+1)
            self.plots.append(DatePlot(ds, field, fig=fig, ax=ax, lw=1.5))
            ax.xaxis.label.set_size(fontsize)
            ax.yaxis.label.set_size(fontsize)
            ax.xaxis.set_tick_params(labelsize=fontsize)
            ax.yaxis.set_tick_params(labelsize=fontsize)
        self.fig = fig
        xmin, xmax = self.plots[0].ax.get_xlim()
        self.set_xlim(num2date(xmin), num2date(xmax))

    def set_xlim(self, xmin, xmax):
        for plot in self.plots:
            plot.set_xlim(xmin, xmax)

    def savefig(self, filename, **kwargs):
        self.fig.savefig(filename, **kwargs)
