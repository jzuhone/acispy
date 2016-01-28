from __future__ import print_function
from six import string_types
from acis.obscat import Obscat, ObsID
from acis.utils import get_time, convert_decyear_to_yday
from acis.states import TemperatureModel, States
from astropy.time import Time, TimeDelta
import astropy.units as u
import requests
from bs4 import BeautifulSoup
import numpy as np
from collections import defaultdict
import os

def _check_for_lr_id(lines):
    for i, line in enumerate(lines):
        if line.startswith("USING"):
            words = line.split("/")
            lr_id = words[5]+words[6][-1].upper()
            return lr_id
    raise RuntimeError("Was not able to determine the ID for the load review!")

def make_two_lists():
    return [[],[]]

class LoadReview(object):
    """
    Create a ``LoadReview`` from its HTML version or a file.
    :param lr_id: The identifier for the load review in standard format, e.g. "DEC2815C", or the text
        file containing the load review.
    :return: the ``LoadReview`` object.
    """
    def __init__(self, load_review):
        if os.path.exists(load_review):
            f = open(load_review, "r")
            self.txt = f.readlines()
            f.close()
        else:
            yr = "20%s" % load_review[5:7]
            url = "http://cxc.cfa.harvard.edu/acis/lr_texts/%s/%s_lr.html" % (yr, load_review.upper())
            u = requests.get(url)
            soup = BeautifulSoup(u.content, "lxml")
            self.txt = soup.body.pre.text.split("\n")
        self.id = _check_for_lr_id(self.txt)
        self.obscat = LoadReviewObscat.from_load_review(self)
        self.errors = []
        start_time, status = self._get_start_time_and_status()
        # To define *the* start time, take the first time entry
        # and then subtract half a second
        start_time -= TimeDelta(0.5,format="sec")
        start_time = start_time.decimalyear
        self.event_times = defaultdict(make_two_lists)
        self.event_times["instrument"][0].append(start_time)
        self.event_times["instrument"][1].append(status[0])
        self.event_times["hetg"][0].append(start_time)
        if status[1].endswith("IN"):
            self.event_times["hetg"][1].append(True)
        else:
            self.event_times["hetg"][1].append(False)
        self.event_times["letg"][0].append(start_time)
        if status[2].endswith("IN"):
            self.event_times["letg"][1].append(True)
        else:
            self.event_times["letg"][1].append(False)
        self.event_times["obsid"][0].append(start_time)
        self.event_times["obsid"][1].append(status[3])
        self.event_times["radmon_enabled"][0].append(start_time)
        if status[4].endswith("DS"):
            self.event_times["radmon_enabled"][1].append(False)
        else:
            self.event_times["radmon_enabled"][1].append(True)
        self.event_times["format"][0].append(start_time)
        self.event_times["format"][1].append(int(status[5][-1]))
        self._populate_event_times()
        # Now we fix the initial entries for comm and belts
        self.event_times["in_comm"][0].insert(0, start_time)
        self.event_times["in_comm"][1].insert(0, not self.event_times["in_comm"][1][0])
        self.event_times["in_belts"][0].insert(0, start_time)
        self.event_times["in_belts"][1].insert(0, not self.event_times["in_belts"][1][0])
        self.fptemp = TemperatureModel.from_webpage("fp", self.id)
        self.states = States.from_webpage("fp", self.id)

    def _get_start_time_and_status(self):
        for i, line in enumerate(self.txt):
            words = line.strip().split()
            if len(words) > 0:
                try:
                    time = Time(words[0])
                    break
                except:
                    pass
                if line.startswith("CHANDRA STATUS ARRAY"):
                    status = self.txt[i+2].strip().split()[-1]
                    continue
        status = status.strip("()").split(",")
        return time, status

    def _populate_event_times(self):
        for i, line in enumerate(self.txt):
            words = line.strip().split()
            if len(words) > 0:
                try:
                    time = Time(words[0]).decimalyear
                    self.event_times["line"][0].append(time)
                    self.event_times["line"][1].append(i)
                    if "MP_OBSID" in line:
                        self.event_times["obsid"][0].append(time)
                        self.event_times["obsid"][1].append(words[-1])
                    if "SIMTRANS" in line:
                        self.event_times["instrument"][0].append(time)
                        self.event_times["instrument"][1].append(words[-1].strip("()"))
                    if "HETGIN" in line:
                        self.event_times["hetg"][0].append(time)
                        self.event_times["hetg"][1].append(True)
                    if "HETGRE" in line:
                        self.event_times["hetg"][0].append(time)
                        self.event_times["hetg"][1].append(False)
                    if "LETGIN" in line:
                        self.event_times["letg"][0].append(time)
                        self.event_times["letg"][1].append(True)
                    if "LETGRE" in line:
                        self.event_times["letg"][0].append(time)
                        self.event_times["letg"][1].append(False)
                    if "CSELFMT" in line:
                        self.event_times["format"][0].append(time)
                        self.event_times["format"][1].append(int(words[-1][-1]))
                    if "EPERIGEE" in line:
                        self.event_times["perigee"][0].append(time)
                    if "APOGEE" in line:
                        self.event_times["apogee"][0].append(time)
                    if "COMM BEGINS" in line:
                        self.event_times["in_comm"][0].append(time)
                        self.event_times["in_comm"][1].append(True)
                    if "COMM ENDS" in line:
                        self.event_times["in_comm"][0].append(time)
                        self.event_times["in_comm"][1].append(False)
                    if "EEF1000" in line:
                        self.event_times["in_belts"][0].append(time)
                        self.event_times["in_belts"][1].append(True)
                    if "XEF1000" in line:
                        self.event_times["in_belts"][0].append(time)
                        self.event_times["in_belts"][1].append(False)
                    if "OORMPDS" in line:
                        self.event_times["radmon_enabled"][0].append(time)
                        self.event_times["radmon_enabled"][1].append(False)
                    if "OORMPEN" in line:
                        self.event_times["radmon_enabled"][0].append(time)
                        self.event_times["radmon_enabled"][1].append(True)
                except ValueError:
                    pass

    def _search_for_status(self, key, time):
        list = self.event_times[key]
        # We have this if we need it
        err = "The time %s is not within the time frame for this load review!" % time
        if time.decimalyear < list[0][0]:
            raise RuntimeError(err)
        idx = np.searchsorted(list[0], time.decimalyear)
        if key != "line":
            idx -= 1
        try:
            stat = list[1][idx]
        except IndexError:
            raise RuntimeError(err)
        return stat

    def check_for_errors_and_warnings(self):
        """Check the ``LoadReview`` for error and warning messages."""
        # Lazy-evaluate errors
        if len(self.errors) == 0:
            for i, line in enumerate(self.txt):
                if line.startswith(">>>ERROR") or line.startswith(">>>WARNING"):
                    self.errors.append("Line %d: %s" % (i, line[3:].strip()))
            if len(self.errors) == 0:
                self.errors.append("No errors or warnings were found in this load review.")
        for error in self.errors:
            print(error)

    def jump_to_time(self, time, n=10):
        """
        Jump to a particular time in the load review and print
        a number of lines.
        :param time: The time to start printing from. Can be in yday format, 
            an AstroPy Time object, or "now".
        :param n: The number of lines to print, default 10.
        """
        time = get_time(time)
        lineno = self._search_for_status("line", time)
        self.jump_to_line(lineno, n=n)

    def jump_to_line(self, lineno, n=10):
        """
        Jump to a particular line number in the load review and print
        a number of lines.
        :param lineno: The line number to start printing from.
        :param n: The number of lines to print, default 10.
        """
        ct = 0
        i = lineno
        while ct <= n:
            line = self.txt[i]
            if line.strip() != "":
                print("Line %d: %s" % (i, line.strip()))
                ct += 1
            i += 1

    def get_status(self, time):
        time = get_time(time)
        status = {}
        for k,v in self.event_times.items():
            if k not in ["line","perigee","apogee"]:
                status[k] = self._search_for_status(k, time)
        status["fptemp"] = self.fptemp.get_temp_at_time(time)
        states = self.states.get_state(time)
        for state in ["ra","dec","roll","dither","pitch","power_cmd","si_mode"]:
            status[state] = states[state]
        status["sim_z"] = states["simpos"]
        status["sim_focus"] = states["simfa_pos"]
        return status

    @property
    def current_status(self):
        self.get_status("now")

    def get_time_for_obsid_change(self, obsid):
        """
        Return the time for an ``obsid`` change. 
        :param obsid: the ObsID to return the time for. 
        :return: AstroPy Time object for the time of the obsid change.
        """
        if not isinstance(obsid, string_types):
            obsid = "%05d" % obsid
        idx = self.event_times["obsid"][1].index(obsid)
        return convert_decyear_to_yday(self.event_times["obsid"][0][idx])

    def get_times_for_event(self, event, filter=None):
        if filter is None:
            times = self.event_times[event][0]
        else:
            filter = np.array(self.event_times[event][1]) == filter
            times = np.array(self.event_times[event][0])[filter]
        return convert_decyear_to_yday(times)

    def __repr__(self):
        return "Load Review %s" % self.id

    def __str__(self):
        return self.id

def _parse_lines_ocat(lines):

    in_ocat = False
    ocat = {}

    for i, line in enumerate(lines):
        if line.startswith("LATEST OCAT INFO"):
            if not lines[i+1].startswith("No"):
                words = line.strip().split()
                obsid = words[-1][:-1]
                ocat[obsid] = ObsID(obsid)
                this_obsid = ocat[obsid] # pointer for convenience
                in_ocat = True
            continue
        if in_ocat:
            words = line.strip().split()
            num_words = len(words)
            if line.startswith("Target Name"):
                idx_si = words.index("SI")
                this_obsid["target_name"] = " ".join(words[2:idx_si])
                this_obsid["simode"] = words[-1]
            elif line.startswith("Instrument"):
                this_obsid["instrument"] = words[1]
                this_obsid["grating"] = words[3]
                this_obsid["type"] = words[5]
            elif line.startswith("Exposure"):
                this_obsid["exposure_time"] = float(words[2])*u.ks
                this_obsid["remaining_exposure_time"] = float(words[6])*u.ks
            elif line.startswith("Offset"):
                this_obsid["offset_y"] = float(words[2])
                this_obsid["offset_z"] = float(words[4])
                if num_words == 7:
                    this_obsid["offset_zsim"] = float(words[-1])
                else:
                    this_obsid["offset_zsim"] = 0.0
            elif line.startswith("ACIS Exposure"):
                this_obsid["exposure_mode"] = words[3]
                this_obsid["event_tm_format"] = words[7]
                if num_words > 10:
                    this_obsid["frame_time"] = float(words[-1])*u.s
                else:
                    this_obsid["frame_time"] = None
            elif line.startswith("Chips Turned"):
                chips = words[3]+words[4]
                this_obsid["chips_turned_on"] = [i for i, c in enumerate(chips) if c == "Y"]
            elif line.startswith("Subarray Type"):
                if words[2] == "NONE":
                    this_obsid["subarray"] = "NONE"
                else:
                    this_obsid["subarray"] = words[2]
                    this_obsid["subarray_start"] = int(words[4])
                    this_obsid["subarray_rows"] = int(words[6])
            elif line.startswith("Duty Cycle"):
                if words[2] == "Y":
                    this_obsid["duty_cycle"] = "Y"
                    this_obsid["duty_cycle_number"] = int(words[4])
                    this_obsid["duty_cycle_tprimary"] = float(words[6])*u.s
                    this_obsid["duty_cycle_tsecondary"] = float(words[8])*u.s
                else:
                    this_obsid["duty_cycle"] = "N"
            elif line.startswith("Onchip Summing"):
                if words[2] == "Y":
                    this_obsid["onchip_summing"] = "Y"
                    this_obsid["onchip_summing_rows"] = int(words[4])
                    this_obsid["onchip_summing_columns"] = int(words[6])
                else:
                    this_obsid["onchip_summing"] = "N"
            elif line.startswith("Event Filter"):
                pass
            elif line.startswith("Window Filter"):
                pass
            elif line.startswith("Height"):
                pass
            elif line.startswith("Lower Energy"):
                pass
            elif line.startswith("Dither"):
                if num_words > 1:
                    this_obsid["dither"] = words[-1]
                else:
                    this_obsid["dither"] = "NORMAL"
            elif line.startswith("Cycle"):
                this_obsid["cycle"] = words[1]
                this_obsid["obj_flag"] = words[-1]
                in_ocat = False

    if len(ocat) == 0:
        raise RuntimeError("There were no ObsIDs found in this load review!")

    return ocat

class LoadReviewObscat(Obscat):
    def __init__(self, lr_id, ocat, subset=None):
        self.lr_id = lr_id
        super(LoadReviewObscat, self).__init__(ocat, subset=subset)

    @classmethod
    def from_load_review(cls, lr):
        """
        Return a ``LoadReviewObscat`` from a ``LoadReview`` object.
        :param lr: the ``LoadReview`` object from which to extract the catalog.
        :return: the ``LoadReviewObscat`` object.
        """
        ocat = _parse_lines_ocat(lr.txt)
        return cls(lr.id, ocat)

    @classmethod
    def from_file(cls, fn):
        """
        Return a ``LoadReviewObscat`` from a load review file.
        :param fn: the load review file from which to extract the catalog.
        :return: the ``LoadReviewObscat`` object.
        """
        f = open(fn, "r")
        lines = f.readlines()
        f.close()
        lr_id = _check_for_lr_id(lines)
        ocat = _parse_lines_ocat(lines)
        return cls(lr_id, ocat)

    def __repr__(self):
        s = "Load Review %s Obscat" % self.lr_id
        if self.subset is not None:
            s += " (%s)" % self.subset
        return s

    def __str__(self):
        return self.lr_id

    def find_obsids_with(self, item, criterion, value):
        ocat = super(LoadReviewObscat, self).find_obsids_with(item, criterion, value)
        if ocat is None:
            return None
        else:
            return LoadReviewObscat(self.lr_id, ocat.ocat, subset=ocat.subset)