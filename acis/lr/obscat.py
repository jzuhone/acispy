from __future__ import print_function

options = ["instrument", "grating", "subarray", "duty_cycle",
           "onchip_summing", "event_filter", "window_filter", "dither",
           "exposure_time","chips_turned_on"]

criteria_map = {"==":"__eq__",
                "!=":"__ne__",
                ">=":"__ge__",
                "<=":"__le__",
                ">":"__gt__",
                "<":"__lt__",
                "in":"__contains__"}

class ObsID(object):
    def __init__(self, id):
        self.obsid = {}
        self.id = id

    def __str__(self):
        return self.id

    def __repr__(self):
        return "ObsID %s" % self.id

    def __getitem__(self, item):
        return self.obsid[item]

    def __setitem__(self, item, value):
        self.obsid[item] = value

    def get(self, item, default=None):
        return self.obsid.get(item, default)

    def __getattr__(self, item):
        return self.obsid[item]

class LoadReviewObscat(object):
    def __init__(self, lr_id, ocat, subset=None):
        self.ocat = ocat
        self.lr_id = lr_id
        self.subset = subset

    @classmethod
    def from_file(cls, fn):

        f = open(fn, "r")
        lines = f.readlines()
        f.close()

        in_ocat = False
        ocat = {}
        lr_id = None

        for i, line in enumerate(lines):
            if line.startswith("USING"):
                words = line.split("/")
                lr_id = words[5]+words[6][-1].upper()
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
                        this_obsid["dither"] = "ON"
                elif line.startswith("Cycle"):
                    this_obsid["cycle"] = words[1]
                    this_obsid["obj_flag"] = words[-1]
                    in_ocat = False

        if lr_id is None:
            raise RuntimeError("Was not able to determine the ID for the load review!")
        if len(ocat) == 0:
            raise RuntimeError("There were no ObsIDs found in this load review!")

        return cls(lr_id, ocat, subset="all")

    def keys(self):
        return self.ocat.keys()

    def items(self):
        return self.ocat.items()

    def values(self):
        return self.ocat.values()

    def __getitem__(self, obsid):
        return self.ocat[obsid]

    def __contains__(self, obsid):
        return obsid in self.ocat

    def __repr__(self):
        s = "Load Review %s ObsIDs" % self.lr_id
        if self.subset != "all":
            s += " where %s." % self.subset
        return s

    def __str__(self):
        return self.lr_id

    def __iter__(self):
        for obsid in self.ocat:
            yield obsid

    def __len__(self):
        return len(self.keys())

    def find_obsids_with(self, item, criterion, value):
        if criterion == "in":
            subset = "%s %s %s" % (value, criterion, item)
        else:
            subset = "%s %s %s" % (item, criterion, value)
        if item not in options:
            s = "Cannot create a subset of ObsIDs with this criterion: %s." % subset
            raise RuntimeError(s)
        criterion = criteria_map[criterion]
        new_ocat = {}
        for k, v in self.ocat.items():
            if v.get(item) is None:
                matches = False
            else:
                func_to_eval = getattr(v[item], criterion)
                if isinstance(value, (list, tuple)):
                    matches = all([func_to_eval(vv) for vv in value])
                else:
                    matches = func_to_eval(value)
            if matches:
                new_ocat[k] = v
        if len(new_ocat) == 0:
            s = "No ObsIDs with the criterion \"%s\" were found." % subset
            raise RuntimeError(s)
        else:
            return LoadReviewObscat(self.lr_id, new_ocat, subset=subset)
