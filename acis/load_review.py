from __future__ import print_function
from acis.obscat import Obscat, ObsID

def _check_for_lr_id(lines):
    for i, line in enumerate(lines):
        if line.startswith("USING"):
            words = line.split("/")
            lr_id = words[5]+words[6][-1].upper()
            return lr_id
    raise RuntimeError("Was not able to determine the ID for the load review!")

class LoadReview(object):
    def __init__(self, fn):
        f = open(fn, "r")
        self.txt = f.readlines()
        f.close()
        self.id = _check_for_lr_id(self.txt)
        self.obscat = LoadReviewObscat.from_load_review(self)

    def check_for_errors(self):
        for i, line in enumerate(self.txt):
            if line.startswith(">>>ERROR"):
                print("Line %d: %s" % (i, line[3:].strip()))

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
                this_obsid["exposure_time"] = float(words[2])
                this_obsid["remaining_exposure_time"] = float(words[6])
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
                    this_obsid["frame_time"] = float(words[-1])
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
                    this_obsid["duty_cycle_tprimary"] = float(words[6])
                    this_obsid["duty_cycle_tsecondary"] = float(words[8])
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
        ocat = _parse_lines_ocat(lr.txt)
        return cls(lr.id, ocat)

    @classmethod
    def from_file(cls, fn):
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