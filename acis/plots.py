from Ska.Matplotlib import plot_cxctime
from matplotlib import font_manager
import matplotlib.pyplot as plt
from matplotlib.dates import num2date
from utils import state_labels, msid_units
from astropy.time import Time

class DatePlot(object):
    def __init__(self, field, field2=None, fig=None, ax=None, lw=2,
                 fontsize=18, plot_args={}, plot_args2={}):
        if fig is None:
            fig = plt.figure(figsize=(10, 8))
        src, fd = field
        if "color" not in plot_args:
            plot_args["color"] = 'b'
        ticklocs, fig, ax = plot_cxctime(src.time, src[fd], fig=fig,
                                         ax=ax, lw=lw, **plot_args)
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
        if fd in state_labels:
            self.set_ylabel(state_labels[fd])
        elif fd in msid_units:
            self.set_ylabel(fd.upper()+" (%s)" % msid_units[fd])
        else:
            self.set_ylabel(fd.upper())
        if field2 is not None:
            src2, fd2 = field2
            self.ax2 = self.ax.twinx()
            if "color" not in plot_args2:
                plot_args2["color"] = 'r'
            plot_cxctime(src2.time, src2[fd2], fig=fig, ax=self.ax2,
                         lw=lw, **plot_args2)
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

    def set_xlim(self, xmin, xmax):
        self.ax.set_xlim(Time(xmin).to_datetime(),
                         Time(xmax).to_datetime())

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
    def __init__(self, fields, fig=None, subplots=None,
                 fontsize=15):
        if fig is None:
            fig = plt.figure(figsize=(12, 12))
        if subplots is None:
            subplots = len(fields), 1
        self.plots = []
        for i, field in enumerate(fields):
            ax = fig.add_subplot(subplots[0], subplots[1], i+1)
            self.plots.append(DatePlot(field, fig=fig, ax=ax, lw=1.5))
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
