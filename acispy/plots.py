from Ska.Matplotlib import plot_cxctime
from matplotlib import font_manager
import matplotlib.pyplot as plt
from matplotlib.dates import num2date
from acispy.utils import state_labels, msid_units, \
    msid_list, msid_unit_labels, interpolate
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

type_map = {"deg_C": "Temperature",
            "V": "Voltage",
            "A": "Current"}

default_colors = ["b","r","g","k"]

class DatePlot(object):
    r""" Make a single-panel plot of a quantity (or multiple quantities) 
    vs. date and time. 

    Multiple quantities can be plotted on the left
    y-axis together if they have the same units, otherwise a quantity
    with different units can be plotted on the right y-axis. 

    Parameters
    ----------
    dc : :class:`~acispy.data_container.DataContainer`
        The DataContainer instance to get the data to plot from.
    fields : tuple of strings or list of tuples of strings
        A single field or list of fields to plot on the left y-axis.
    field2 : tuple of strings, optional
        A single field to plot on the right y-axis. Default: None
    fig : :class:`~matplotlib.figure.Figure`, optional
        A Figure instance to plot in. Default: None, one will be
        created if not provided.
    ax : :class:`~matplotlib.axes.Axes`, optional
        An Axes instance to plot in. Default: None, one will be
        created if not provided.
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

    Examples
    --------
    >>> from acispy import DatePlot
    >>> p1 = DatePlot(dc, ("msids", "1dpamzt"), field2=("states", "pitch"),
    ...               lw=2, colors="brown")

    >>> from acispy import DatePlot
    >>> fields = [("msids", "1dpamzt"), ("msids", "1deamzt"), ("msids", "1pdeaat")]
    >>> p2 = DatePlot(dc, fields, fontsize=12, colors=["brown","black","orange"])
    """
    def __init__(self, dc, fields, field2=None, fig=None, ax=None, lw=1.5,
                 fontsize=18, colors=None, color2='magenta'):
        if fig is None:
            fig = plt.figure(figsize=(10, 8))
        if colors is None:
            colors = default_colors
        if not isinstance(fields, list):
            fields = [fields]
        if not isinstance(colors, list):
            colors = [colors]
        for i, field in enumerate(fields):
            src_name, fd = field
            src = getattr(dc, src_name)
            drawstyle = drawstyles.get(fd, None)
            if src_name == "states":
                x = pointpair(src["tstart"], src["tstop"])
                y = pointpair(src[fd])
            elif src_name == "msids":
                x = src[fd+"_times"]
                y = src[fd]
            else:
                x = src["times"]
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
            src2 = getattr(dc, src_name2)
            self.ax2 = self.ax.twinx()
            drawstyle = drawstyles.get(fd2, None)
            if src_name2 == "states":
                x = pointpair(src2["tstart"], src2["tstop"])
                y = pointpair(src2[fd2])
            elif src_name2 == "msids":
                x = src2[fd+"_times"]
                y = src2[fd]
            else:
                x = src2["times"]
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
        """
        Set the limits on the x-axis of the plot to *xmin* and *xmax*,
        which must be in YYYY:DOY:HH:MM:SS format.
        """
        if not isinstance(xmin, datetime):
            xmin = datetime.strptime(DateTime(xmin).iso, "%Y-%m-%d %H:%M:%S.%f")
        if not isinstance(xmax, datetime):
            xmax = datetime.strptime(DateTime(xmax).iso, "%Y-%m-%d %H:%M:%S.%f")
        self.ax.set_xlim(xmin, xmax)

    def set_ylim(self, ymin, ymax):
        """
        Set the limits on the left y-axis of the plot to *ymin* and *ymax*.
        """
        self.ax.set_ylim(ymin, ymax)

    def set_ylim2(self, ymin, ymax):
        """
        Set the limits on the right y-axis of the plot to *ymin* and *ymax*.
        """
        self.ax2.set_ylim(ymin, ymax)

    def set_ylabel(self, ylabel, fontdict=None, **kwargs):
        """
        Set the label of the left y-axis of the plot.

        Parameters
        ----------
        ylabel : string
            The new label.
        fontdict : dict, optional
            A dict of font properties to use for the label. Default: None

        Examples
        --------
        >>> p1.set_ylabel("DPA Temperature", fontdict={"size": 15, "color": "blue"})
        """
        if fontdict is None:
            fontdict = {"size": 18, "family": "serif"}
        self.ax.set_ylabel(ylabel, fontdict=fontdict, **kwargs)

    def set_ylabel2(self, ylabel, fontdict=None, **kwargs):
        """
        Set the label of the right y-axis of the plot.

        Parameters
        ----------
        ylabel : string
            The new label.
        fontdict : dict, optional
            A dict of font properties to use for the label. Default: None

        Examples
        --------
        >>> p1.set_ylabel2("Pitch Angle in Degrees", fontdict={"size": 14, "family": "serif"})
        """
        if fontdict is None:
            fontdict = {"size": 18, "family": "serif"}
        self.ax2.set_ylabel(ylabel, fontdict=fontdict, **kwargs)

    def savefig(self, filename, **kwargs):
        """
        Save the figure to the file specified by *filename*.
        """
        self.fig.savefig(filename, **kwargs)

class MultiDatePlot(object):
    r""" Make a multi-panel plot of multiple quantities vs. date and time.

    Parameters
    ----------
    dc : :class:`~acispy.data_container.DataContainer`
        The DataContainer instance to get the data to plot from.
    fields : list of tuples of strings
        A list of fields to plot.
    fig : :class:`~matplotlib.figure.Figure`, optional
        A Figure instance to plot in. Default: None, one will be
        created if not provided.
    subplots : tuple of integers, optional
        The gridded layout of the plots, i.e. (num_x_plots, num_y_plots)
        The default is to have all plots stacked vertically.
    fontsize : integer, optional
        The font size for the labels in the plot. Default: 15 pt.
    lw : float, optional
        The width of the lines in the plots. Default: 1.5 px.

    Examples
    --------
    >>> from acispy import MultiDatePlot
    >>> fields = [("msids", "1deamzt"), ("model", "1deamzt"), ("states", "ccd_count")]
    >>> mp = MultiDatePlot(dc, fields, lw=2, subplots=(2, 2))
    """
    def __init__(self, dc, fields, fig=None, subplots=None,
                 fontsize=15, lw=1.5):
        if fig is None:
            fig = plt.figure(figsize=(12, 12))
        if subplots is None:
            subplots = len(fields), 1
        self.plots = []
        for i, field in enumerate(fields):
            ax = fig.add_subplot(subplots[0], subplots[1], i+1)
            self.plots.append(DatePlot(dc, field, fig=fig, ax=ax, lw=lw))
            ax.xaxis.label.set_size(fontsize)
            ax.yaxis.label.set_size(fontsize)
            ax.xaxis.set_tick_params(labelsize=fontsize)
            ax.yaxis.set_tick_params(labelsize=fontsize)
        self.fig = fig
        xmin, xmax = self.plots[0].ax.get_xlim()
        self.set_xlim(num2date(xmin), num2date(xmax))

    def set_xlim(self, xmin, xmax):
        """
        Set the limits on the x-axis of the plot to *xmin* and *xmax*,
        which must be in YYYY:DOY:HH:MM:SS format.
        """
        for plot in self.plots:
            plot.set_xlim(xmin, xmax)

    def savefig(self, filename, **kwargs):
        """
        Save the figure to the file specified by *filename*.
        """
        self.fig.savefig(filename, **kwargs)

class PhasePlot(object):
    r""" Make a single-panel plot of one quantity vs. another.

    The one restriction is that you cannot plot a state on the y-axis
    if the quantity on the x-axis is not a state. 

    Parameters
    ----------
    dc : :class:`~acispy.data_container.DataContainer`
        The DataContainer instance to get the data to plot from.
    x_field : tuple of strings
        The field to plot on the x-axis.
    y_field : tuple of strings
        The field to plot on the y-axis.
    fig : :class:`~matplotlib.figure.Figure`, optional
        A Figure instance to plot in. Default: None, one will be
        created if not provided.
    ax : :class:`~matplotlib.axes.Axes`, optional
        An Axes instance to plot in. Default: None, one will be
        created if not provided.
    fontsize : integer, optional
        The font size for the labels in the plot. Default: 18 pt.

    Examples
    --------
    >>> from acispy import PhasePlot
    >>> pp = PhasePlot(dc, ("msids", "1deamzt"), ("msids", "1dpamzt"))
    """
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
                times_in = y_src[y_fd+"_times"]
            else:
                times_in = y_src["times"]
            if x_src_name == "states":
                tstart_out = x_src["tstart"]
                tstop_out = x_src["tstop"]
                ok, idxs = interpolate(times_in, tstart_out, tstop_out)
                x = pointpair(x[ok])
                y = pointpair(y[idxs[0]], y[idxs[1]])
            else:
                if x_src_name == "msids":
                    times_out = x_src[x_fd+"_times"]
                else:
                    times_out = x_src["times"]
                ok, idxs = interpolate(times_in, times_out)
                x = x[ok]
                y = y[idxs]
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

    def set_xlim(self, xmin, xmax):
        """
        Set the limits on the x-axis of the plot to *xmin* and *xmax*.
        """
        self.ax.set_xlim(xmin, xmax)

    def set_ylim(self, ymin, ymax):
        """
        Set the limits on the y-axis of the plot to *ymin* and *ymax*.
        """
        self.ax.set_ylim(ymin, ymax)

    def set_xlabel(self, xlabel, fontdict=None, **kwargs):
        """
        Set the label of the x-axis of the plot.

        Parameters
        ----------
        xlabel : string
            The new label.
        fontdict : dict, optional
            A dict of font properties to use for the label. Default: None

        Examples
        --------
        >>> pp.set_ylabel("DEA Temperature", fontdict={"size": 15, "color": "blue"})
        """
        if fontdict is None:
            fontdict = {"size": 18, "family": "serif"}
        self.ax.set_xlabel(xlabel, fontdict=fontdict, **kwargs)

    def set_ylabel(self, ylabel, fontdict=None, **kwargs):
        """
        Set the label of the y-axis of the plot.

        Parameters
        ----------
        ylabel : string
            The new label.
        fontdict : dict, optional
            A dict of font properties to use for the label. Default: None

        Examples
        --------
        >>> pp.set_ylabel("DPA Temperature", fontdict={"size": 15, "color": "blue"})
        """
        if fontdict is None:
            fontdict = {"size": 18, "family": "serif"}
        self.ax.set_ylabel(ylabel, fontdict=fontdict, **kwargs)

    def savefig(self, filename, **kwargs):
        """
        Save the figure to the file specified by *filename*.
        """
        self.fig.savefig(filename, **kwargs)
