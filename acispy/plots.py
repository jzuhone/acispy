from Ska.Matplotlib import plot_cxctime
from matplotlib import font_manager
import matplotlib.pyplot as plt
from matplotlib.dates import num2date
from acispy.utils import state_labels, msid_units, msid_list, msid_unit_labels
from Chandra.Time import DateTime
from datetime import datetime
import numpy as np
import Ska.Numpy

def pointpair(x, y=None):
    if y is None:
        y = x
    return np.array([x, y]).reshape(-1, order='F')

drawstyles = {"simpos": "steps",
              "pitch": "steps",
              "ccd_count": "steps"}

type_map = {"deg_C": "Temperature",
            "V": "Voltage",
            "A": "Current"}

default_colors = ["b","r","g","k"]

class DatePlot(object):
    def __init__(self, ds, fields, field2=None, fig=None, ax=None, lw=1.5,
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
            elif src_name == "msids":
                x = src.times[fd]
                y = src[fd]
            else:
                x = src.times
                y = src[fd]
            ticklocs, fig, ax = plot_cxctime(x, y, fig=fig, lw=lw, ax=ax,
                                             color=colors[i],
                                             drawstyle=drawstyle, 
                                             label="%s" % fd.upper())
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
            self.set_ylabel(type_map[msid_units[fields[0][1]]]+" (%s)" % 
                            msid_unit_labels[msid_units[fields[0][1]]])
        else:
            if fd in state_labels:
                self.set_ylabel(state_labels[fd])
            elif fd in msid_list:
                self.set_ylabel(fd.upper()+" (%s)" % msid_unit_labels[msid_units[fd]])
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
            elif src_name2 == "msids":
                x = src2.times[fd]
                y = src2[fd]
            else:
                x = src2.times
                y = src2[fd]
            plot_cxctime(x, y, fig=fig, ax=self.ax2, lw=lw,
                         drawstyle=drawstyle, color=color2)
            for label in self.ax2.get_xticklabels():
                label.set_fontproperties(fontProperties)
            for label in self.ax2.get_yticklabels():
                label.set_fontproperties(fontProperties)
            if fd2 in state_labels:
                self.set_ylabel2(state_labels[fd2])
            elif fd2 in msid_list:
                self.set_ylabel(fd2.upper()+" (%s)" % msid_unit_labels[msid_units[fd]])
            else:
                self.set_ylabel(fd2.upper())

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

class PhasePlot(object):
    def __init__(self, ds, x_field, y_field, fig=None, ax=None,
                 fontsize=18):
        if fig is None:
            fig = plt.figure(figsize=(12, 12))
        if ax is None:
            ax = fig.add_subplot(111)
        x_src_name, x_fd = x_field
        y_src_name, y_fd = y_field
        if y_src_name == "states" and x_src_name != "states":
            raise RuntimeError("Cannot plot an MSID or model vs. a state, "
                               "put the state on the x-axis!")
        x_src = getattr(ds, x_src_name)
        y_src = getattr(ds, y_src_name)
        x = x_src[x_fd]
        y = y_src[y_fd]
        if x.size != y.size:
            # Interpolate the y-axis to the x-axis times
            if y_src_name == "msids":
                times_in = y_src.times[y_fd]
            else:
                times_in = y_src.times
            if x_src_name == "states":
                tstart_out = x_src.tstart
                tstop_out = x_src.tstop
                ok_start = (tstart_out >= times_in[0]) & (tstart_out <= times_in[-1])
                ok_stop = (tstop_out >= times_in[0]) & (tstop_out <= times_in[-1])
                ok = ok_start & ok_stop
                tstart_out = tstart_out[ok]
                tstop_out = tstop_out[ok]
                idx_start = Ska.Numpy.interpolate(np.arange(len(times_in)),
                                                  times_in, tstart_out,
                                                  method='nearest', sorted=True)
                idx_stop = Ska.Numpy.interpolate(np.arange(len(times_in)),
                                                 times_in, tstop_out,
                                                 method='nearest', sorted=True)
                x = pointpair(x[ok])
                y = pointpair(y[idx_start], y[idx_stop])
            else:
                if x_src_name == "msids":
                    times_out = x_src.times[x_fd]
                else:
                    times_out = x_src.times
                ok = (times_out >= times_in[0]) & (times_out <= times_in[-1])
                times_out = times_out[ok]
                indexes = Ska.Numpy.interpolate(np.arange(len(times_in)),
                                                times_in, times_out,
                                                method='nearest', sorted=True)
                x = x[ok]
                y = y[indexes]
        scp = ax.scatter(x, y)
        self.fig = fig
        self.ax = ax
        self.scp = scp
        fontProperties = font_manager.FontProperties(family="serif",
                                                     size=fontsize)
        for label in self.ax.get_xticklabels():
            label.set_fontproperties(fontProperties)
        for label in self.ax.get_yticklabels():
            label.set_fontproperties(fontProperties)
        if x_fd in state_labels:
            self.set_xlabel(state_labels[x_fd])
        elif x_fd in msid_list:
            self.set_xlabel(x_fd.upper()+" (%s)" % msid_unit_labels[msid_units[x_fd]])
        else:
            self.set_xlabel(x_fd.upper())
        if y_fd in state_labels:
            self.set_ylabel(state_labels[y_fd])
        elif y_fd in msid_list:
            self.set_ylabel(y_fd.upper()+" (%s)" % msid_unit_labels[msid_units[y_fd]])
        else:
            self.set_ylabel(y_fd.upper())

    def set_xlabel(self, xlabel, fontdict=None, **kwargs):
        if fontdict is None:
            fontdict = {"size": 18, "family": "serif"}
        self.ax.set_xlabel(xlabel, fontdict=fontdict, **kwargs)

    def set_ylabel(self, ylabel, fontdict=None, **kwargs):
        if fontdict is None:
            fontdict = {"size": 18, "family": "serif"}
        self.ax.set_ylabel(ylabel, fontdict=fontdict, **kwargs)
