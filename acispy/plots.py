from Ska.Matplotlib import plot_cxctime, pointpair
from matplotlib import font_manager
import matplotlib.pyplot as plt
from matplotlib.dates import num2date
from acispy.utils import unit_labels, interpolate_indexes
from Chandra.Time import DateTime
from datetime import datetime
from collections import OrderedDict
from matplotlib.backends.backend_agg import \
    FigureCanvasAgg
from io import BytesIO
import numpy as np

drawstyles = {"simpos": "steps",
              "pitch": "steps",
              "ccd_count": "steps",
              "fmt": "steps"}

units_map = {"deg_C": "Temperature",
             "V": "Voltage",
             "A": "Current"}

default_colors = ["b","r","g","k"]

class ACISPlot(object):
    def __init__(self, fig, ax):
        self.fig = fig
        self.ax = ax

    def _repr_png_(self):
        canvas = FigureCanvasAgg(self.fig)
        f = BytesIO()
        canvas.print_figure(f)
        f.seek(0)
        return f.read()

    def savefig(self, filename, **kwargs):
        """
        Save the figure to the file specified by *filename*.
        """
        self.fig.savefig(filename, **kwargs)

    def set_title(self, label, fontsize=18, loc='center', **kwargs):
        """
        Add a title to the top of the plot.

        Parameters
        ----------
        label : string
            The title itself.
        fontsize : integer, optional
            The size of the font. Default: 18 pt
        loc : string, optional
            The horizontal location of the title. Options are: 'left',
            'right', 'center'. Default: 'center'

        Examples
        --------
        >>> p.set_title("my awesome plot", fontsize=15, loc='left')
        """
        fontdict = {"family": "serif", "size": fontsize}
        self.ax.set_title(label, fontdict=fontdict, loc=loc, **kwargs)

    def set_grid(self, on):
        """
        Turn grid lines on or off on the plot. 

        Parameters
        ----------
        on : boolean
            Set to True to put the lines on, set to False to remove them.
        """
        self.ax.grid(on)

    def add_hline(self, y, lw=2, ls='-', color='green', **kwargs):
        """
        Add a horizontal line on the y-axis of the plot.

        Parameters
        ----------
        y : float
            The value to place the vertical line at.
        lw : integer, optional
            The width of the line. Default: 2
        ls : string, optional
            The style of the line. Can be one of:
            'solid', 'dashed', 'dashdot', 'dotted'.
            Default: 'solid'
        color : string, optional
            The color of the line. Default: 'green'

        Examples
        --------
        >>> p.add_hline(36., lw=3, ls='dashed', color='red')
        """
        self.ax.axhline(y=y, lw=lw, ls=ls, color=color, **kwargs)

    def add_hline(self, y, lw=2, ls='solid', color='green', **kwargs):
        """
        Add a horizontal line on the left y-axis of the plot.

        Parameters
        ----------
        y : float
            The value to place the vertical line at.
        lw : integer, optional
            The width of the line. Default: 2
        ls : string, optional
            The style of the line. Can be one of:
            'solid', 'dashed', 'dashdot', 'dotted'.
            Default: 'solid'
        color : string, optional
            The color of the line. Default: 'green'

        Examples
        --------
        >>> p.add_hline(36., lw=3, ls='dashed', color='red')
        """
        self.ax.axhline(y=y, lw=lw, ls=ls, color=color, **kwargs)

    def set_ylim(self, ymin, ymax):
        """
        Set the limits on the left y-axis of the plot to *ymin* and *ymax*.
        """
        self.ax.set_ylim(ymin, ymax)

    def set_ylabel(self, ylabel, fontsize=18, **kwargs):
        """
        Set the label of the left y-axis of the plot.

        Parameters
        ----------
        ylabel : string
            The new label.
        fontsize : integer, optional
            The size of the font. Default: 18 pt

        Examples
        --------
        >>> pp.set_ylabel("DPA Temperature", fontsize=15)
        """
        fontdict = {"size": fontsize, "family": "serif"}
        self.ax.set_ylabel(ylabel, fontdict=fontdict, **kwargs)

class DatePlot(ACISPlot):
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
    fig : :class:`~matplotlib.figure.Figure`, optional
        A Figure instance to plot in. Default: None, one will be
        created if not provided.
    ax : :class:`~matplotlib.axes.Axes`, optional
        An Axes instance to plot in. Default: None, one will be
        created if not provided.

    Examples
    --------
    >>> from acispy import DatePlot
    >>> p1 = DatePlot(dc, ("msids", "1dpamzt"), field2=("states", "pitch"),
    ...               lw=2, colors="brown")

    >>> from acispy import DatePlot
    >>> fields = [("msids", "1dpamzt"), ("msids", "1deamzt"), ("msids", "1pdeaat")]
    >>> p2 = DatePlot(dc, fields, fontsize=12, colors=["brown","black","orange"])
    """
    def __init__(self, dc, fields, field2=None, lw=1.5, fontsize=18,
                 colors=None, color2='magenta', fig=None, ax=None):
        if fig is None:
            fig = plt.figure(figsize=(10, 8))
        if colors is None:
            colors = default_colors
        if not isinstance(fields, list):
            fields = [fields]
        self.num_fields = len(fields)
        if not isinstance(colors, list):
            colors = [colors]
        for i, field in enumerate(fields):
            src_name, fd = field
            drawstyle = drawstyles.get(fd, None)
            if src_name == "states":
                tstart, tstop = dc.times(*field)
                x = pointpair(tstart.value, tstop.value)
                y = pointpair(dc[field])
            else:
                x = dc.times(*field).value
                y = dc[field]
            label = dc.fields[field].display_name
            ticklocs, fig, ax = plot_cxctime(x, y, fig=fig, lw=lw, ax=ax,
                                             color=colors[i],
                                             drawstyle=drawstyle, 
                                             label=label)
        super(DatePlot, self).__init__(fig, ax)
        self.ax.set_xlabel("Date", fontdict={"size": fontsize,
                                             "family": "serif"})
        if self.num_fields > 1:
            self.ax.legend(loc=0, prop={"family": "serif"})
        fontProperties = font_manager.FontProperties(family="serif",
                                                     size=fontsize)
        for label in self.ax.get_xticklabels():
            label.set_fontproperties(fontProperties)
        for label in self.ax.get_yticklabels():
            label.set_fontproperties(fontProperties)
        units = dc.fields[fields[0]].units
        if self.num_fields > 1:
            if units == '':
                ylabel = ''
            else:
                ylabel = '%s (%s)' % (units_map[units], unit_labels[units])
            self.set_ylabel(ylabel)
        else:
            ylabel = dc.fields[fields[0]].display_name
            if units != '':
                ylabel += ' (%s)' % unit_labels[units]
            self.set_ylabel(ylabel)
        if field2 is not None:
            src_name2, fd2 = field2
            self.ax2 = self.ax.twinx()
            drawstyle = drawstyles.get(fd2, None)
            if src_name2 == "states":
                tstart, tstop = dc.times(*field2)
                x = pointpair(tstart.value, tstop.value)
                y = pointpair(dc[field2])
            else:
                x = dc.times(*field2).value
                y = dc[field2]
            plot_cxctime(x, y, fig=fig, ax=self.ax2, lw=lw,
                         drawstyle=drawstyle, color=color2)
            for label in self.ax2.get_xticklabels():
                label.set_fontproperties(fontProperties)
            for label in self.ax2.get_yticklabels():
                label.set_fontproperties(fontProperties)
            units2 = dc.fields[field2].units
            ylabel2 = dc.fields[field2].display_name
            if units2 != '':
                ylabel2 += ' (%s)' % unit_labels[units2]
            self.set_ylabel2(ylabel2)

    def set_xlim(self, xmin, xmax):
        """
        Set the limits on the x-axis of the plot to *xmin* and *xmax*,
        which must be in YYYY:DOY:HH:MM:SS format.

        Examples
        --------
        >>> p.set_xlim("2016:050:12:45:47.324", "2016:056:22:32:01.123")
        """
        if not isinstance(xmin, datetime):
            xmin = datetime.strptime(DateTime(xmin).iso, "%Y-%m-%d %H:%M:%S.%f")
        if not isinstance(xmax, datetime):
            xmax = datetime.strptime(DateTime(xmax).iso, "%Y-%m-%d %H:%M:%S.%f")
        self.ax.set_xlim(xmin, xmax)

    def set_ylim2(self, ymin, ymax):
        """
        Set the limits on the right y-axis of the plot to *ymin* and *ymax*.
        """
        self.ax2.set_ylim(ymin, ymax)

    def set_ylabel2(self, ylabel, fontsize=18, **kwargs):
        """
        Set the label of the right y-axis of the plot.

        Parameters
        ----------
        ylabel : string
            The new label.
        fontsize : integer, optional
            The size of the font. Default: 18 pt

        Examples
        --------
        >>> p1.set_ylabel2("Pitch Angle in Degrees", fontsize=14)
        """
        fontdict = {"size": fontsize, "family": "serif"}
        self.ax2.set_ylabel(ylabel, fontdict=fontdict, **kwargs)

    def add_vline(self, time, lw=2, ls='solid', color='green', **kwargs):
        """
        Add a vertical line on the time axis of the plot.

        Parameters
        ----------
        time : string
            The time to place the vertical line at.
            Must be in YYYY:DOY:HH:MM:SS format.
        lw : integer, optional
            The width of the line. Default: 2
        ls : string, optional
            The style of the line. Can be one of:
            'solid', 'dashed', 'dashdot', 'dotted'.
            Default: 'solid'
        color : string, optional
            The color of the line. Default: 'green'

        Examples
        --------
        >>> p.add_vline("2016:101:12:36:10.102", lw=3, ls='dashed', color='red')
        """
        time = datetime.strptime(DateTime(time).iso, "%Y-%m-%d %H:%M:%S.%f")
        self.ax.axvline(x=time, lw=lw, ls=ls, color=color, **kwargs)

    def add_hline2(self, y2, lw=2, ls='solid', color='green', **kwargs):
        """
        Add a horizontal line on the right y-axis of the plot.

        Parameters
        ----------
        y2 : float
            The value to place the vertical line at.
        lw : integer, optional
            The width of the line. Default: 2
        ls : string, optional
            The style of the line. Can be one of:
            'solid', 'dashed', 'dashdot', 'dotted'.
            Default: 'solid'
        color : string, optional
            The color of the line. Default: 'green'

        Examples
        --------
        >>> p.add_hline2(105., lw=3, ls='dashed', color='red')
        """
        self.ax2.axhline(y=y2, lw=lw, ls=ls, color=color, **kwargs)

    def set_legend(self, loc='best', fontsize=16, **kwargs):
        """
        Adjust a legend on the plot.

        Parameters
        ----------
        loc : string, optional
            The location of the legend on the plot. Options are:
            'best'
            'upper right'
            'upper left'
            'lower left'
            'lower right'
            'right'
            'center left'
            'center right'
            'lower center'
            'upper center'
            'center'
            Default: 'best', which will try to find the best location for
            the legend, e.g. away from plotted data.
        fontsize : integer, optional
            The size of the legend text. Default: 16 pt.

        Examples
        --------
        >>> p.set_legend(loc='right', fontsize=18)
        """
        if self.num_fields == 1:
            raise RuntimeError("This plot does not have a legend because it"
                               "has only one set of data on the left y-axis!")
        prop = {"family": "serif", "size": fontsize}
        self.ax.legend(loc=loc, prop=prop, **kwargs)

class MultiDatePlot(object):
    r""" Make a multi-panel plot of multiple quantities vs. date and time.

    Parameters
    ----------
    dc : :class:`~acispy.data_container.DataContainer`
        The DataContainer instance to get the data to plot from.
    fields : list of tuples of strings
        A list of fields to plot.
    subplots : tuple of integers, optional
        The gridded layout of the plots, i.e. (num_x_plots, num_y_plots)
        The default is to have all plots stacked vertically.
    fontsize : integer, optional
        The font size for the labels in the plot. Default: 15 pt.
    lw : float, optional
        The width of the lines in the plots. Default: 1.5 px.
    fig : :class:`~matplotlib.figure.Figure`, optional
        A Figure instance to plot in. Default: None, one will be
        created if not provided.

    Examples
    --------
    >>> from acispy import MultiDatePlot
    >>> fields = [("msids", "1deamzt"), ("model", "1deamzt"), ("states", "ccd_count")]
    >>> mp = MultiDatePlot(dc, fields, lw=2, subplots=(2, 2))
    """
    def __init__(self, dc, fields, subplots=None,
                 fontsize=15, lw=1.5, fig=None):
        if fig is None:
            fig = plt.figure(figsize=(12, 12))
        if subplots is None:
            subplots = len(fields), 1
        self.plots = OrderedDict()
        for i, field in enumerate(fields):
            ax = fig.add_subplot(subplots[0], subplots[1], i+1)
            self.plots[field] = DatePlot(dc, field, fig=fig, ax=ax, lw=lw)
            ax.xaxis.label.set_size(fontsize)
            ax.yaxis.label.set_size(fontsize)
            ax.xaxis.set_tick_params(labelsize=fontsize)
            ax.yaxis.set_tick_params(labelsize=fontsize)
        self.fig = fig
        xmin, xmax = self.plots[fields[0]].ax.get_xlim()
        self.set_xlim(num2date(xmin), num2date(xmax))

    def __getitem__(self, item):
        return self.plots[item]

    def set_xlim(self, xmin, xmax):
        """
        Set the limits on the x-axis of the plot to *xmin* and *xmax*,
        which must be in YYYY:DOY:HH:MM:SS format.
        """
        for plot in self.plots.values():
            plot.set_xlim(xmin, xmax)

    def add_vline(self, x, lw=2, ls='-', color='green', **kwargs):
        """
        Add a vertical line on the time axis of the plot.

        Parameters
        ----------
        time : string
            The time to place the vertical line at.
            Must be in YYYY:DOY:HH:MM:SS format.
        lw : integer, optional
            The width of the line. Default: 2
        ls : string, optional
            The style of the line. Can be one of:
            'solid', 'dashed', 'dashdot', 'dotted'.
            Default: 'solid'
        color : string, optional
            The color of the line. Default: 'green'

        Examples
        --------
        >>> p.add_vline("2016:101:12:36:10.102", lw=3, ls='dashed', color='red')
        """
        for plot in self.plots.values():
            plot.add_vline(x, lw=lw, ls=ls, color=color, **kwargs)

    def set_title(self, label, fontsize=18, loc='center', **kwargs):
        """
        Add a title to the top of the plot.

        Parameters
        ----------
        label : string
            The title itself.
        fontsize : integer, optional
            The size of the font. Default: 18 pt
        loc : string, optional
            The horizontal location of the title. Options are: 'left',
            'right', 'center'. Default: 'center'

        Examples
        --------
        >>> p.set_title("my awesome plot", fontsize=15, loc='left')
        """
        self.plots.values()[0].set_title(label, fontsize=fontsize, loc=loc, **kwargs)

    def set_grid(self, on):
        """
        Turn grid lines on or off on the plot. 

        Parameters
        ----------
        on : boolean
            Set to True to put the lines on, set to False to remove them.
        """
        for plot in self.plots.values():
            plot.set_grid(on)

    def savefig(self, filename, **kwargs):
        """
        Save the figure to the file specified by *filename*.
        """
        self.fig.savefig(filename, **kwargs)

    def _repr_png_(self):
        canvas = FigureCanvasAgg(self.fig)
        f = BytesIO()
        canvas.print_figure(f)
        f.seek(0)
        return f.read()

class PhasePlot(ACISPlot):
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
    fontsize : integer, optional
        The font size for the labels in the plot. Default: 18 pt.
    fig : :class:`~matplotlib.figure.Figure`, optional
        A Figure instance to plot in. Default: None, one will be
        created if not provided.
    ax : :class:`~matplotlib.axes.Axes`, optional
        An Axes instance to plot in. Default: None, one will be
        created if not provided.

    Examples
    --------
    >>> from acispy import PhasePlot
    >>> pp = PhasePlot(dc, ("msids", "1deamzt"), ("msids", "1dpamzt"))
    """
    def __init__(self, dc, x_field, y_field, fontsize=18,
                 fig=None, ax=None):
        if fig is None:
            fig = plt.figure(figsize=(12, 12))
        if ax is None:
            ax = fig.add_subplot(111)
        x_src_name, x_fd = x_field
        y_src_name, y_fd = y_field
        xlabel = dc.fields[x_field].display_name
        ylabel = dc.fields[x_field].display_name
        xunit = dc.fields[x_field].units
        yunit = dc.fields[y_field].units
        if y_src_name == "states" and x_src_name != "states":
            raise RuntimeError("Cannot plot an MSID or model vs. a state, "
                               "put the state on the x-axis!")
        x = dc[x_field]
        y = dc[y_field]
        if x.size != y.size:
            # Interpolate the y-axis to the x-axis times
            times_in = dc.times(*y_field).value
            if x_src_name == "states":
                tstart_out, tstop_out = dc.times(*x_field)
                ok1, idxs1 = interpolate_indexes(times_in, tstart_out.value)
                ok2, idxs2 = interpolate_indexes(times_in, tstop_out.value)
                x = np.append(x[ok1], x[ok2])
                y = np.append(y[idxs1], y[idxs2])
            else:
                times_out = dc.times(*x_field).value
                ok, idxs = interpolate_indexes(times_in, times_out)
                x = x[ok]
                y = y[idxs]
        scp = ax.scatter(x, y)
        super(PhasePlot, self).__init__(fig, ax)
        self.scp = scp
        fontProperties = font_manager.FontProperties(family="serif",
                                                     size=fontsize)
        for label in self.ax.get_xticklabels():
            label.set_fontproperties(fontProperties)
        for label in self.ax.get_yticklabels():
            label.set_fontproperties(fontProperties)
        if xunit != '':
            xlabel += ' (%s)' % unit_labels[xunit]
        if yunit != '':
            ylabel += ' (%s)' % unit_labels[yunit]
        self.set_xlabel(xlabel)
        self.set_ylabel(ylabel)

    def set_xlim(self, xmin, xmax):
        """
        Set the limits on the x-axis of the plot to *xmin* and *xmax*.
        """
        self.ax.set_xlim(xmin, xmax)

    def set_xlabel(self, xlabel, fontsize=18, **kwargs):
        """
        Set the label of the x-axis of the plot.

        Parameters
        ----------
        xlabel : string
            The new label.
        fontsize : integer, optional
            The size of the font. Default: 18 pt

        Examples
        --------
        >>> pp.set_xlabel("DEA Temperature", fontsize=15)
        """
        fontdict = {"size": fontsize, "family": "serif"}
        self.ax.set_xlabel(xlabel, fontdict=fontdict, **kwargs)

    def add_vline(self, x, lw=2, ls='-', color='green', **kwargs):
        """
        Add a vertical line on the x-axis of the plot.

        Parameters
        ----------
        x : float
            The value to place the vertical line at.
        lw : integer, optional
            The width of the line. Default: 2
        ls : string, optional
            The style of the line. Can be one of:
            'solid', 'dashed', 'dashdot', 'dotted'.
            Default: 'solid'
        color : string, optional
            The color of the line. Default: 'green'

        Examples
        --------
        >>> p.add_vline(25., lw=3, ls='dashed', color='red')
        """
        self.ax.axvline(x=x, lw=lw, ls=ls, color=color, **kwargs)
