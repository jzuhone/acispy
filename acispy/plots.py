from Ska.Matplotlib import plot_cxctime, pointpair, \
    cxctime2plotdate
from matplotlib import font_manager
import matplotlib.pyplot as plt
from matplotlib.dates import num2date
from acispy.utils import ensure_list
from cxotime import CxoTime
from datetime import datetime
from collections import OrderedDict
from matplotlib.backends.backend_agg import \
    FigureCanvasAgg
from io import BytesIO
from mpl_toolkits.axes_grid1 import make_axes_locatable
from acispy.utils import convert_state_code
import numpy as np
from astropy.units import Quantity

datefmt = "%Y-%m-%d %H:%M:%S.%f"

drawstyles = {"simpos": "steps",
              "pitch": "steps",
              "ccd_count": "steps",
              "ccsdstmf": "steps"}

units_map = {"deg_C": "Temperature",
             "deg_F": "Temperature",
             "V": "Voltage",
             "A": "Current",
             "W": "Power",
             "deg": 'Angle',
             "deg**2": "Solid Angle"}

unit_labels = {"V": 'V',
               "A": 'A',
               "deg_C": '$\mathrm{^\circ{C}}$',
               "deg_F": '$\mathrm{^\circ{F}}$',
               "W": "W",
               "s": "s",
               "deg": "deg"}


class ACISPlot(object):
    def __init__(self, fig, ax, lines, ax2, lines2):
        self.fig = fig
        self.ax = ax
        self.legend = None
        self.lines = lines
        self.ax2 = ax2
        self.lines2 = lines2

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
        fontdict = {"size": fontsize}
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
        self.ax.axhline(y=y, lw=lw, ls=ls, color=color, 
                        label='_nolegend_', **kwargs)

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
        self.ax.axvline(x=x, lw=lw, ls=ls, color=color, **kwargs,
                        label='_nolegend_')

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
        fontdict = {"size": fontsize}
        self.ax.set_ylabel(ylabel, fontdict=fontdict, **kwargs)

    def redraw(self):
        """
        Re-draw the plot.
        """
        self.fig.canvas.draw()

    def tight_layout(self, *args, **kwargs):
        self.fig.tight_layout(*args, **kwargs)


def get_figure(plot, fig, subplot, figsize):
    ax2 = None
    lines2 = []
    if plot is None:
        if fig is None:
            fig = plt.figure(figsize=figsize)
        if subplot is None:
            subplot = 111
        if not isinstance(subplot, tuple):
            subplot = (subplot,)
        ax = fig.add_subplot(*subplot)
        lines = []
    else:
        fig = plot.fig
        if subplot is None:
            ax = plot.ax
        else:
            ax = fig.add_subplot(subplot)
        lines = plot.lines
        if hasattr(plot, "ax2"):
            ax2 = plot.ax2
            lines2 = plot.lines2
    for axis in ['top', 'bottom', 'left', 'right']:
        ax.spines[axis].set_linewidth(2)
    return fig, ax, lines, ax2, lines2


class CustomDatePlot(ACISPlot):
    r"""
    Make a custom date vs. value plot.

    Parameters
    ----------
    dates : array of strings
        The dates to be plotted.
    values : array
        The values to be plotted.
    lw : float, optional
        The width of the lines in the plots. Default: 2 px.
    ls : string, optional
        The line style of the line. Default: '-'
    fontsize : integer, optional
        The font size for the labels in the plot. Default: 18 pt.
    figsize : tuple of integers, optional
        The size of the plot in (width, height) in inches. Default: (10, 8)
    plot : :class:`~acispy.plots.DatePlot` or :class:`~acispy.plots.CustomDatePlot`, optional
        An existing DatePlot to add this plot to. Default: None, one 
        will be created if not provided.
    """
    def __init__(self, dates, values, fmt='-b', lw=2, fontsize=18, ls='-',
                 figsize=(10, 8), color=None, plot=None, fig=None, 
                 subplot=None, **kwargs):
        fig, ax, lines, ax2, lines2 = get_figure(plot, fig, subplot, figsize)
        dates = CxoTime(dates).secs
        if len(dates.shape) == 2:
            tstart, tstop = np.asarray(dates)
            x = pointpair(tstart, tstop)
            y = pointpair(np.asarray(values))
        else:
            x = np.asarray(dates)
            y = np.asarray(values)
        if color is None:
            color = f"C{len(lines)}"
        ticklocs, fig, ax = plot_cxctime(x, y, fmt=fmt, fig=fig, ax=ax, 
                                         lw=lw, ls=ls, color=color, **kwargs)
        super(CustomDatePlot, self).__init__(fig, ax, lines, ax2, lines2)
        self.ax.tick_params(which="major", width=2, length=6)
        self.ax.tick_params(which="minor", width=2, length=3)
        self.lines.append(ax.lines[-1])
        self.ax.set_xlabel("Date", fontdict={"size": fontsize})
        fontProperties = font_manager.FontProperties(size=fontsize)
        for label in self.ax.get_xticklabels():
            label.set_fontproperties(fontProperties)
        for label in self.ax.get_yticklabels():
            label.set_fontproperties(fontProperties)
        self.times = dates
        self.y = values

    def plot_right(self, dates, values, fmt='-b', lw=2, fontsize=18,
                   ls='-', color="magenta", **kwargs):
        """
        Plot a quantity on the right x-axis of this plot.

        Parameters
        ----------
        dates : array of strings
            The dates to be plotted.
        values : array
            The values to be plotted.
        lw : float, optional
            The width of the lines in the plots. Default: 2 px.
        ls : string, optional
            The line style of the line. Default: '-'
        fontsize : integer, optional
            The font size for the labels in the plot. Default: 18 pt.
        figsize : tuple of integers, optional
            The size of the plot in (width, height) in inches. Default: (10, 8)
        plot : :class:`~acispy.plots.DatePlot` or :class:`~acispy.plots.CustomDatePlot`, optional
            An existing DatePlot to add this plot to. Default: None, one 
            will be created if not provided.
        """
        dates = CxoTime(dates).secs
        if self.ax2 is None:
            self.ax2 = self.ax.twinx()
            self.ax2.set_zorder(-10)
            self.ax.patch.set_visible(False)
        if len(dates.shape) == 2:
            tstart, tstop = np.asarray(dates)
            x = pointpair(tstart, tstop)
            y = pointpair(np.asarray(values))
        else:
            x = np.asarray(dates)
            y = np.asarray(values)
        plot_cxctime(x, y, fmt=fmt, fig=self.fig,
                     ax=self.ax2, ls=ls, color=color, lw=lw, **kwargs)
        self.ax2.tick_params(which="major", width=2, length=6)
        self.ax2.tick_params(which="minor", width=2, length=3)
        fontProperties = font_manager.FontProperties(size=fontsize)
        for label in self.ax2.get_xticklabels():
            label.set_fontproperties(fontProperties)
        for label in self.ax2.get_yticklabels():
            label.set_fontproperties(fontProperties)

    def set_xlim(self, xmin, xmax):
        """
        Set the limits on the x-axis of the plot to *xmin* and *xmax*,
        which must be in YYYY:DOY:HH:MM:SS format.

        Examples
        --------
        >>> p.set_xlim("2016:050:12:45:47.324", "2016:056:22:32:01.123")
        """
        if not isinstance(xmin, datetime):
            xmin = datetime.strptime(CxoTime(xmin).iso, datefmt)
        if not isinstance(xmax, datetime):
            xmax = datetime.strptime(CxoTime(xmax).iso, datefmt)
        self.ax.set_xlim(xmin, xmax)

    def add_hline(self, y, lw=2, ls='-', color='green', 
                  xmin=None, xmax=None, **kwargs):
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
        if xmin is None:
            xmin = 0
        else:
            xmin = datetime.strptime(CxoTime(xmin).iso, datefmt)
        if xmax is None:
            xmax = 1
        else:
            xmax = datetime.strptime(CxoTime(xmax).iso, datefmt)
        self.ax.axhline(y=y, lw=lw, ls=ls, color=color, xmin=xmin,
                        xmax=xmax, label='_nolegend_', **kwargs)

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
        time = datetime.strptime(CxoTime(time).iso, datefmt)
        self.ax.axvline(x=time, lw=lw, ls=ls, color=color, **kwargs, 
                        label='_nolegend_')

    def add_text(self, time, y, text, fontsize=18, color='black',
                 rotation='horizontal', **kwargs):
        """
        Add text to a DatePlot.

        Parameters
        ----------
        time : string
            The time to place the text at.
            Must be in YYYY:DOY:HH:MM:SS format.
        y : float
            The y-value to place the text at.
        text : string
            The text itself.
        fontsize : integer, optional
            The size of the font. Default: 18 pt.
        color : string, optional
            The color of the font. Default: black.
        rotation : string or float, optional
            The rotation of the text. Default: Horizontal

        Examples
        --------
        >>> dp.add_text("2016:101:12:36:10.102", 35., "Something happened here!",
        ...             fontsize=15, color='magenta')
        """
        time = datetime.strptime(CxoTime(time).iso, datefmt)
        self.ax.text(time, y, text, fontsize=fontsize, color=color,
                     rotation=rotation, **kwargs)

    def set_line_label(self, line, label):
        """
        Change the field label in the legend.

        Parameters
        ----------
        line : integer
            The line whose label to change given by its number, assuming
            a starting index of 0.
        label :
            The label to set it to.

        Examples
        --------
        >>> dp.set_line_label(1, "DEA Temperature")
        """
        self.lines[line].set_label(label)
        self.set_legend()

    def set_legend(self, loc='best', fontsize=16, zorder=None, **kwargs):
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
        prop = {"size": fontsize}
        self.legend = self.ax.legend(loc=loc, prop=prop, **kwargs)
        if zorder is not None:
            self.legend.set_zorder(zorder)

    def fill_between(self, datestart, datestop, color, alpha=1.0):
        """
        Fill a shaded region between two times on the plot. 

        Parameters
        ----------
        datestart : string
            The beginning time of the shaded region. Must be in the
            YYYY:DOY:HH:MM:SS format.
        datestop : string
            The ending time of the shaded region. Must be in the
            YYYY:DOY:HH:MM:SS format.
        color : string
            The color of the shaded region.
        alpha : float, optional
            The transparency of the shaded region. Default is 1.0,
            which is opaque.
        """
        tmin, tmax = self.ax.get_xlim()
        ybot, ytop = self.ax.get_ylim()
        t = np.linspace(tmin, tmax, 1000)
        tbegin, tend = cxctime2plotdate(CxoTime([datestart, datestop]).secs)
        where = (t >= tbegin) & (t <= tend)
        self.ax.fill_between(t, ybot, ytop, where=where, 
                             color=color, alpha=alpha)

    def annotate_obsids(self, ypos, ds=None, show_manuvrs=False, ywidth=2.0,
                        txtheight=1.0, lw=2.0, fontsize=16, datestart=None,
                        datestop=None, color='red', manuvr_color='blue',
                        txtloc=0.5):
        """
        Annotate obsids on a :class:`~acispy.plots.CustomDatePlot` or 
        :class:`~acispy.plots.DatePlot` instance. They will be annotated
        using lines to mark the beginning and end of obsids, and the 
        actual obsid numbers will be marked on the plot.

        Parameters
        ----------
        ypos : float
            The location on the y-axis at which the obsid lines will be 
            annotated.
        ds : :class:`~acispy.dataset.Dataset`, optional
            If this is a :class:`~acispy.plots.CustomDatePlot` object,
            you will need to pass in a Dataset object to obtain the
            obsid information. Default: None
        show_manuvrs : boolean, optional
            If True, obsid changes associated with maneuvers will 
            be shown. Default: False
        ywidth : float, optional
            The height of the lines marking obsid changes.
        txtheight : float, optional 
            The height in points where to place the text above the obsids
            line.
        lw : float, optional
            The linewidth of the lines. Default: 2.0
        fontsize : integer, optional
            The font size of the text.
        datestart : string, optional
            Only show obsids after this date and time. Must be in the 
            YYYY:DOY:HH:MM:SS format. Default is to show from the
            beginning of the plot. 
        datestop : string, optional
            Only show obsids before this date and time. Must be in the 
            YYYY:DOY:HH:MM:SS format. Default is to show up to the
            end of the plot.
        color : string, optional
            The color of the lines. Default: 'red'
        manuvr_color : string, optional 
            The color of the lines for maneuver obsids. Default: 'blue'
        txtloc : float, optional
            A float between 0 and 1 to mark the location between
            the start and stop of the obsid where the obsid number is
            annotated.
        """
        tmin, tmax = self.ax.get_xlim()
        if datestart is not None:
            tmin = cxctime2plotdate(CxoTime(datestart).secs)
        if datestop is not None:
            tmax = cxctime2plotdate(CxoTime(datestop).secs)
        if ds is None:
            ds = getattr(self, "ds", None)
        states = getattr(ds, "states", None)
        if states is None:
            raise RuntimeError("The dataset associated with or provided to this plot "
                               "does not include commanded states! Provide a dataset "
                               "using the keyword argument 'ds' to 'annotate_obsids'!")
        idxs = np.char.count(states["trans_keys"].value, "obsid").astype("bool")
        obsids = np.insert(states["obsid"][idxs].value, 0, states["obsid"][0].value)
        tstart = cxctime2plotdate(np.insert(states["obsid"].times[0, idxs].value,
                                  0, states["obsid"].times[0, 0].value))
        endstop = cxctime2plotdate([states["obsid"].times[1, -1].value])
        tstop = np.concatenate([tstart[:-1]+np.diff(tstart), endstop])
        endcapstart = ypos-0.5*ywidth
        endcapstop = ypos+0.5*ywidth
        textypos = ypos+txtheight
        num_obsids = obsids.size
        for i, (ti, tf, obsid) in enumerate(zip(tstart, tstop, obsids)):
            clr = color if obsid <= 40000 else manuvr_color
            if obsid <= 40000 or show_manuvrs:
                self.ax.hlines(ypos, ti, tf, linestyle='-',
                               color=clr, lw=lw)
                if i > 0:
                    self.ax.vlines(ti, endcapstart, endcapstop,
                                   color=clr, lw=lw, zorder=100)
                if i < num_obsids-1:
                    self.ax.vlines(tf, endcapstart, endcapstop,
                                   color=clr, lw=lw, zorder=100)
                tmid = ti + txtloc*(tf - ti)
                if tmin <= tmid <= tmax:
                    self.ax.text(tmid, textypos, obsid, color=clr,
                                 rotation=90, va='bottom', fontsize=fontsize)


class DatePlot(CustomDatePlot):
    r""" Make a single-panel plot of a quantity (or multiple quantities) 
    vs. date and time. 

    Multiple quantities can be plotted on the left
    y-axis together if they have the same units, otherwise a quantity
    with different units can be plotted on the right y-axis. 

    Parameters
    ----------
    ds : :class:`~acispy.dataset.Dataset`
        The Dataset instance to get the data to plot from.
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

    Examples
    --------
    >>> from acispy import DatePlot
    >>> p1 = DatePlot(ds, ("msids", "1dpamzt"), field2=("states", "pitch"),
    ...               lw=2, color="brown")

    >>> from acispy import DatePlot
    >>> fields = [("msids", "1dpamzt"), ("msids", "1deamzt"), ("msids", "1pdeaat")]
    >>> p2 = DatePlot(ds, fields, fontsize=12, color=["brown","black","orange"])
    """
    def __init__(self, ds, fields, field2=None, fmt='-b', lw=2, ls='-',
                 ls2='-', lw2=2, fontsize=18, color=None, color2='magenta',
                 figsize=(10, 8), plot=None, fig=None, subplot=None,
                 plot_bad=False):
        fig, ax, lines, ax2, lines2 = get_figure(plot, fig, subplot, figsize)
        super(CustomDatePlot, self).__init__(fig, ax, lines, ax2, lines2)
        fields = ensure_list(fields)
        lw = ensure_list(lw)
        self.num_fields = len(fields)
        if len(lw) == 1 and len(fields) > 1:
            lw = lw*self.num_fields
        if color is None:
            color = [None]*len(fields)
        color = ensure_list(color)
        ls = ensure_list(ls)
        if len(ls) != len(fields): 
            if len(ls) == 1:
                ls = ls*len(fields)
            else:
                raise RuntimeError("The number of linestyles must equal the number "
                                   "of fields or must be only one style!")
        self.times = {}
        self.y = {}
        self.fields = []
        for i, field in enumerate(fields):
            field = ds._determine_field(field)
            self.fields.append(field)
            src_name, fd = field
            drawstyle = drawstyles.get(fd, None)
            state_codes = ds.state_codes.get(field, None)
            if not plot_bad:
                mask = ds[field].mask
            else:
                mask = slice(None, None, None)
            if state_codes is None:
                y = ds[field].value[mask]
            else:
                state_codes = [(v, k) for k, v in state_codes.items()]
                y = convert_state_code(ds, field)[mask]
            if src_name == "states":
                tstart, tstop = ds[field].times
                x = pointpair(tstart.value[mask], tstop.value[mask])
                y = pointpair(y[mask])
            else:
                x = ds[field].times.value[mask]
            label = ds.fields[field].display_name
            _, fig, ax = plot_cxctime(x, y, fmt=fmt, fig=fig, lw=lw[i],
                                      ax=ax, color=color[i], ls=ls[i],
                                      state_codes=state_codes,
                                      drawstyle=drawstyle,
                                      label=label)
            self.lines.append(ax.lines[-1])
            self.y[field] = ds[field][mask]
            self.times[field] = ds[field][mask].times
        self.fig = fig
        self.ax = ax
        self.ds = ds
        self.ax.set_xlabel("Date", fontdict={"size": fontsize})
        if self.num_fields > 1:
            self.ax.legend(loc=0)
        fontProperties = font_manager.FontProperties(size=fontsize)
        for label in self.ax.get_xticklabels():
            label.set_fontproperties(fontProperties)
        for label in self.ax.get_yticklabels():
            label.set_fontproperties(fontProperties)
        ymin, ymax = self.ax.get_ylim()
        if ymin > 0:
            ymin *= 0.95
        else:
            ymin *= 1.05
        if ymax > 0:
            ymax *= 1.05
        else:
            ymax *= 0.95
        self.ax.set_ylim(ymin, ymax)
        if self.num_fields > 0:
            units = ds.fields[self.fields[0]].units
            ulabel = unit_labels.get(units, units)
            if self.num_fields > 1:
                if units == '':
                    ylabel = ''
                else:
                    ylabel = f"{units_map[units]} ({ulabel})"
                self.set_ylabel(ylabel)
            else:
                ylabel = ds.fields[self.fields[0]].display_name
                if units != '':
                    ylabel += f" ({ulabel})"
                self.set_ylabel(ylabel)
        self.ax.tick_params(which="major", width=2, length=6)
        self.ax.tick_params(which="minor", width=2, length=3)
        if field2 is not None:
            field2 = ds._determine_field(field2)
            self.field2 = field2
            src_name2, fd2 = field2
            if self.ax2 is None:
                self.ax2 = self.ax.twinx()
                self.ax2.set_zorder(-10)
                self.ax.patch.set_visible(False)
            self.ax2.tick_params(which="major", width=2, length=6)
            self.ax2.tick_params(which="minor", width=2, length=3)
            drawstyle = drawstyles.get(fd2, None)
            state_codes = ds.state_codes.get(field2, None)
            if not plot_bad:
                mask2 = ds[field2].mask
            else:
                mask2 = slice(None, None, None)
            if state_codes is None:
                y2 = ds[field2].value[mask2]
            else:
                state_codes = [(v, k) for k, v in state_codes.items()]
                y2 = convert_state_code(ds, field2)[mask2]
            if src_name2 == "states":
                tstart, tstop = ds[field2].times
                x2 = pointpair(tstart.value[mask2], tstop.value[mask2])
                y2 = pointpair(y2[mask2])
            else:
                x2 = ds[field2].times.value[mask2]
            plot_cxctime(x2, y2, fig=fig, ax=self.ax2, ls=ls2,
                         lw=lw2, drawstyle=drawstyle, color=color2,
                         state_codes=state_codes)
            self.lines2.append(self.ax2.lines[-1])
            self.times[field2] = ds[field2][mask2].times
            self.y[field2] = ds[field2][mask2]
            for label in self.ax2.get_xticklabels():
                label.set_fontproperties(fontProperties)
            for label in self.ax2.get_yticklabels():
                label.set_fontproperties(fontProperties)
            ymin2, ymax2 = self.ax2.get_ylim()
            if ymin2 > 0:
                ymin2 *= 0.95
            else:
                ymin2 *= 1.05
            if ymax2 > 0:
                ymax2 *= 1.05
            else:
                ymax2 *= 0.95
            self.ax2.set_ylim(ymin2, ymax2)
            units2 = ds.fields[field2].units
            ylabel2 = ds.fields[field2].display_name
            ulabel2 = unit_labels.get(units2, units2)
            if units2 != '':
                ylabel2 += f" ({ulabel2})"
            self.set_ylabel2(ylabel2)
        else:
            self.field2 = None
        if plot_bad:
            self._fill_bad_times()

    def _fill_bad_times(self):
        masks = []
        times = []
        for field in self.fields:
            if field[0] != "states":
                times.append(self.times[field])
                masks.append(self.y[field].mask)
        axes = [self.ax]*len(times)
        if self.field2 and self.field2[0] != "states":
            axes.append(self.ax2)
            times.append(self.times[self.field2])
            masks.append(self.y[self.field2].mask)
        for mask, ax, x in zip(masks, axes, times):
            if np.any(~mask):
                ybot, ytop = ax.get_ylim()
                all_time = cxctime2plotdate(x.value)
                bad = np.concatenate([[False], ~mask, [False]])
                bad_int = np.flatnonzero(bad[1:] != bad[:-1]).reshape(-1, 2)
                for ii, jj in bad_int:
                    ax.fill_between(all_time[ii:jj], ybot, ytop, 
                                    where=~mask[ii:jj], color='cyan', alpha=0.5)

    def set_ylim(self, ymin, ymax):
        """
        Set the limits on the left y-axis of the plot to *ymin* and *ymax*.
        """
        self.ax.set_ylim(ymin, ymax)
        self._fill_bad_times()

    def set_ylim2(self, ymin, ymax):
        """
        Set the limits on the right y-axis of the plot to *ymin* and *ymax*.
        """
        self.ax2.set_ylim(ymin, ymax)
        self._fill_bad_times()

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
        fontdict = {"size": fontsize}
        self.ax2.set_ylabel(ylabel, fontdict=fontdict, **kwargs)

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
        self.ax2.axhline(y=y2, lw=lw, ls=ls, color=color, **kwargs,
                         label='_nolegend_')

    def set_field_label(self, field, label):
        """
        Change the field label in the legend.

        Parameters
        ----------
        field : (type, name) tuple
            The field whose label to change.
        label :
            The label to set it to.

        Examples
        --------
        >>> dp.set_field_label(("msids","1deamzt"), "DEA Temperature")
        """
        fd = self.ds._determine_field(field)
        idx = self.fields.index(fd)
        self.set_line_label(idx, label)


class DummyDatePlot(object):
    def __init__(self, fig, ax):
        self.fig = fig
        self.ax = ax
        self.lines = []


def make_dateplots(*args, **kwargs):
    fig, axes = plt.subplots(*args, **kwargs)
    if not hasattr(axes, "shape"):
        return DummyDatePlot(fig, axes)
    elif len(axes.shape) == 1:
        return np.array([DummyDatePlot(fig, ax) for ax in axes])
    elif len(axes.shape) == 2:
        plots = np.empty(axes.shape, dtype=DummyDatePlot)
        nx, ny = axes.shape
        for i in range(nx):
            for j in range(ny):
                plots[i][j] = DummyDatePlot(fig, axes[i][j])
        return plots


class MultiDatePlot(object):
    r""" Make a multi-panel plot of multiple quantities vs. date and time.

    Parameters
    ----------
    ds : :class:`~acispy.dataset.Dataset`
        The Dataset instance to get the data to plot from.
    fields : list of tuples of strings
        A list of fields to plot.
    subplots : tuple of integers, optional
        The gridded layout of the plots, i.e. (num_x_plots, num_y_plots)
        The default is to have all plots stacked vertically.
    fontsize : integer, optional
        The font size for the labels in the plot. Default: 15 pt.
    lw : float, optional
        The width of the lines in the plots. Default: 2 px.
    color : string, optional
        The color of the lines in the plots. Can be a single color or
        one color for each plot. Default is to use a single color, which
        is the Matplotlib default.
    figsize : tuple of integers, optional
        The size of the plot in (width, height) in inches. Default: (12, 12)
    plot_bad : boolean, optional
        If True, "bad" values will be plotted but the ranges of bad values
        will be marked with translucent blue rectangles. If False, bad
        values will be removed from the plot. Default: False

    Examples
    --------
    >>> from acispy import MultiDatePlot
    >>> fields = [("msids", "1deamzt"), ("model", "1deamzt"), ("states", "ccd_count")]
    >>> mp = MultiDatePlot(ds, fields, lw=2, subplots=(2, 2))

    >>> from acispy import MultiDatePlot
    >>> fields = [[("msids", "1deamzt"), ("model", "1deamzt")], ("states", "ccd_count")]
    >>> mp = MultiDatePlot(ds, fields, lw=2)
    """
    def __init__(self, ds, fields, subplots=None,
                 fontsize=15, lw=2, figsize=(12, 12),
                 color=None, plot_bad=False):
        fig = plt.figure(figsize=figsize)
        if subplots is None:
            subplots = len(fields), 1
        self.plots = OrderedDict()
        if color is None:
            color = [None]*len(fields)
        color = ensure_list(color)
        for i, field in enumerate(fields):
            ax = fig.add_subplot(subplots[0], subplots[1], i+1)
            ddp = DummyDatePlot(fig, ax)
            if isinstance(field, list):
                fd = field[0]
            else:
                fd = field
            # This next line is to raise an error if we have
            # multiple field types with the same name
            ds._determine_field(fd)
            self.plots[fd] = DatePlot(ds, field, plot=ddp, lw=lw, 
                                      color=color[i], plot_bad=plot_bad)
            ax.xaxis.label.set_size(fontsize)
            ax.yaxis.label.set_size(fontsize)
            ax.xaxis.set_tick_params(labelsize=fontsize)
            ax.yaxis.set_tick_params(labelsize=fontsize)
        self.fig = fig
        xmin, xmax = self.plots[list(self.plots.keys())[0]].ax.get_xlim()
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
        list(self.plots.values())[0].set_title(label, fontsize=fontsize, loc=loc, **kwargs)

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

    def redraw(self):
        """
        Re-draw the plot.
        """
        self.fig.canvas.draw()


class HistogramPlot(ACISPlot):
    def __init__(self, ds, field, bins=None, range=None, tstart=None,
                 tstop=None, cumulative=False, density=None,
                 figsize=(12, 12), fontsize=18, plot=None, **kwargs):
        self.field = ds._determine_field(field)
        self.xlabel = ds.fields[self.field].display_name
        self.unit = ds.fields[self.field].units
        slc = slice(tstart, tstop)
        self.xx = ds[field][slc]

        if plot is None:
            fig = plt.figure(figsize=figsize)
            ax = fig.add_subplot(111)
        else:
            fig = plot.fig
            ax = plot.ax
        super(HistogramPlot, self).__init__(fig, ax, [], None, [])

        if self.field[0] == "states":
            self.weights = (ds.states["tstop"][slc] -
                            ds.states["tstart"][slc]).to("ks")
        else:
            weights = np.diff(self.xx.times.to_value("ks"))
            self.weights = Quantity(np.concatenate([weights[0],
                                                    0.5*(weights[:-1] +
                                                         weights[1:]),
                                                    weights[-1]]), "ks")

        hist, bins, patches = self.ax.hist(self.xx.value, bins=bins,
                                           range=range, density=density,
                                           cumulative=cumulative,
                                           weights=self.weights.value, **kwargs)

        self.hist = hist
        self.bins = bins
        self.patches = patches

        self._annotate_plot(fontsize, density, cumulative)

    def _annotate_plot(self, fontsize, density, cumulative):
        fontProperties = font_manager.FontProperties(size=fontsize)
        for label in self.ax.get_xticklabels():
            label.set_fontproperties(fontProperties)
        for label in self.ax.get_yticklabels():
            label.set_fontproperties(fontProperties)
        ulabel = unit_labels.get(self.unit, self.unit)
        if self.unit != '':
            self.xlabel += f" ({ulabel})" 
        self.ax.set_xlabel(self.xlabel, fontsize=18)
        if density:
            self.ylabel = "Fraction of Time"
        else:
            if cumulative:
                self.ylabel = "Cumulative Time (ks)"
            else:
                self.ylabel = "Time (ks)"
        self.ax.set_ylabel(self.ylabel, fontsize=18)


class PhasePlot(ACISPlot):
    def __init__(self, ds, x_field, y_field, figsize=(12, 12), plot=None):
        if plot is None:
            fig = plt.figure(figsize=figsize)
            ax = fig.add_subplot(111)
        else:
            fig = plot.fig
            ax = plot.ax
        self.x_field = ds._determine_field(x_field)
        self.y_field = ds._determine_field(y_field)
        self.xlabel = ds.fields[self.x_field].display_name
        self.ylabel = ds.fields[self.y_field].display_name
        self.xunit = ds.fields[self.x_field].units
        self.yunit = ds.fields[self.y_field].units

        self.xx = ds[x_field]
        self.yy = ds[y_field]

        self.ds = ds

        super(PhasePlot, self).__init__(fig, ax, [], None, [])

    def _annotate_plot(self, fontsize):
        fontProperties = font_manager.FontProperties(size=fontsize)
        for label in self.ax.get_xticklabels():
            label.set_fontproperties(fontProperties)
        for label in self.ax.get_yticklabels():
            label.set_fontproperties(fontProperties)
        uxlabel = unit_labels.get(self.xunit, self.xunit)
        uylabel = unit_labels.get(self.yunit, self.yunit)
        if self.xunit != '':
            self.xlabel += f" ({uxlabel})"
        if self.yunit != '':
            self.ylabel += f" ({uylabel})"
        self.set_xlabel(self.xlabel)
        self.set_ylabel(self.ylabel)
        return fontProperties

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
        fontdict = {"size": fontsize}
        self.ax.set_xlabel(xlabel, fontdict=fontdict, **kwargs)

    def add_line(self, x, y, lw=2, ls='-', color=None, **kwargs):
        """
        Add an arbitrary line to the plot.

        Parameters
        ----------
        x : float
            The x-values of the line.
        y : float
            The y-values of the line.
        lw : integer, optional
            The width of the line. Default: 2
        ls : string, optional
            The style of the line. Can be one of:
            'solid', 'dashed', 'dashdot', 'dotted'.
            Default: 'solid'
        color : string, optional
            The color of the line. Default is to use
            the default Matplotlib color.

        Examples
        --------
        >>> x = np.linspace(0.0, 50.0, 100)
        >>> y = x.copy()
        >>> p.add_line(x, y, lw=3, ls='dashed', color='red')
        """
        self.ax.plot(x, y, lw=lw, ls=ls, color=color, **kwargs)

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
        self.ax.axvline(x=x, lw=lw, ls=ls, color=color, **kwargs,
                        label='_nolegend_')

    def add_text(self, x, y, text, fontsize=18, color='black',
                 rotation='horizontal', **kwargs):
        """
        Add text to a PhasePlot.

        Parameters
        ----------
        x : string
            The x-value to place the text at.
        y : float
            The y-value to place the text at.
        text : string
            The text itself.
        fontsize : integer, optional
            The size of the font. Default: 18 pt.
        color : string, optional
            The color of the font. Default: black.
        rotation : string or float, optional
            The rotation of the text. Default: Horizontal

        Examples
        --------
        >>> dp.add_text(32.7, 35., "This spot is interesting",
        ...             fontsize=15, color='magenta')
        """
        self.ax.text(x, y, text, fontsize=fontsize, color=color,
                     rotation=rotation, **kwargs)


class PhaseScatterPlot(PhasePlot):
    r""" Make a single-panel phase scatter plot of one quantity vs. another.

    The one restriction is that the two fields must have an equal amount
    of samples, achievable by interoplating one field to another's times
    or creating a fake MSID field from a state field using
    :meth:`~acispy.dataset.Dataset.map_state_to_msid`.

    Parameters
    ----------
    ds : :class:`~acispy.dataset.Dataset`
        The Dataset instance to get the data to plot from.
    x_field : tuple of strings
        The field to plot on the x-axis.
    y_field : tuple of strings
        The field to plot on the y-axis.
    c_field : tuple of strings, optional
        The field to use to color the dots on the plot. Default: None
    fontsize : integer, optional
        The font size for the labels in the plot. Default: 18 pt.
    color : string, optional
        The color of the dots on the phase plot. Only used if a
        color field is not provided. Default: 'blue'
    cmap : string, optional
        The colormap for the dots if a color field has been provided.
        Default: 'heat'
    figsize : tuple of integers, optional
        The size of the plot in (width, height) in inches. Default: (12, 12)
    plot : :class:`~acispy.plots.PhasePlot`, optional
        An existing PhasePlot to add this plot to. Default: None, one 
        will be created if not provided.

    Examples
    --------
    >>> from acispy import PhaseScatterPlot
    >>> pp = PhaseScatterPlot(ds, ("msids", "1deamzt"), ("msids", "1dpamzt"))
    """
    def __init__(self, ds, x_field, y_field, c_field=None,
                 fontsize=18, color='blue', cmap='hot',
                 figsize=(12, 12), plot=None, **kwargs):

        super(PhaseScatterPlot, self).__init__(ds, x_field, y_field, 
                                               figsize=figsize, plot=plot)

        if c_field is None:
            self.cc = color
        else:
            self.cc = np.array(ds[c_field])

        cm = plt.cm.get_cmap(cmap)
        pp = self.ax.scatter(np.array(self.xx), np.array(self.yy),
                             c=self.cc, cmap=cm, **kwargs)

        self.pp = pp

        fontProperties = self._annotate_plot(fontsize)

        if c_field is not None:
            clabel = self.ds.fields[c_field].display_name
            cunit = self.ds.fields[c_field].units
            if cunit != '':
                uclabel = unit_labels.get(cunit, cunit)
                clabel += f" ({uclabel})"
            divider = make_axes_locatable(self.ax)
            cax = divider.append_axes("right", size="5%", pad=0.05)
            cb = plt.colorbar(self.pp, cax=cax)
            fontdict = {"size": fontsize}
            cb.set_label(clabel, fontdict=fontdict)
            for label in cb.ax.get_yticklabels():
                label.set_fontproperties(fontProperties)
            self.cb = cb


class PhaseHistogramPlot(PhasePlot):
    r""" Make a single-panel 2D binned histogram plot of one quantity 
    vs. another.

    The one restriction is that the two fields must have an equal amount
    of samples, achievable by interoplating one field to another's times
    or creating a fake MSID field from a state field using
    :meth:`~acispy.dataset.Dataset.map_state_to_msid`.

    Parameters
    ----------
    ds : :class:`~acispy.dataset.Dataset`
        The Dataset instance to get the data to plot from.
    x_field : tuple of strings
        The field to plot on the x-axis.
    y_field : tuple of strings
        The field to plot on the y-axis.
    x_bins : int or NumPy array
        The bins for the x-axis of the histogram. If an int, it will
        make that many bins between the minimum and maximum values.
        If a NumPy array, it will use it as the bin edges.
    y_bins : int or NumPy array
        The bins for the y-axis of the histogram. If an int, it will
        make that many bins between the minimum and maximum values.
        If a NumPy array, it will use it as the bin edges.
    scale : string, optional
        The scaling of the plot. "linear" or "log". Default: "linear"
    cmap : string, optional
        The colormap for the histogram. Default: 'heat'
    fontsize : integer, optional
        The font size for the labels in the plot. Default: 18 pt.
    figsize : tuple of integers, optional
        The size of the plot in (width, height) in inches. Default: (12, 12)
    plot : :class:`~acispy.plots.PhasePlot`, optional
        An existing PhasePlot to add this plot to. Default: None, one 
        will be created if not provided.

    Examples
    --------
    >>> from acispy import PhaseHistogramPlot
    >>> pp = PhaseHistogramPlot(ds, "1deamzt", "1dpamzt", 100, 100)
    """
    def __init__(self, ds, x_field, y_field, x_bins, y_bins, scale='linear',
                 cmap='hot', fontsize=18, figsize=(12, 12), plot=None, **kwargs):
        from matplotlib.colors import LogNorm, Normalize
        super(PhaseHistogramPlot, self).__init__(ds, x_field, y_field, 
                                                 figsize=figsize, plot=plot)

        cm = plt.cm.get_cmap(cmap)
        if scale == "log":
            norm = LogNorm()
        else:
            norm = Normalize()
        counts, xedges, yedges, pp = self.ax.hist2d(np.asarray(self.xx), np.asarray(self.yy), 
                                                    [x_bins, y_bins], cmap=cm, norm=norm, **kwargs)
        self.pp = pp
        self.counts = counts
        self.xedges = xedges
        self.yedges = yedges

        fontProperties = self._annotate_plot(fontsize)

        divider = make_axes_locatable(self.ax)
        cax = divider.append_axes("right", size="5%", pad=0.05)
        cb = plt.colorbar(self.pp, cax=cax)
        fontdict = {"size": fontsize}
        cb.set_label("Counts", fontdict=fontdict)
        for label in cb.ax.get_yticklabels():
            label.set_fontproperties(fontProperties)
        self.cb = cb
