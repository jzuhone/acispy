from __future__ import print_function

class LoadReviewObscat(object):
    def __init__(self, fn):
        f = open(fn, "r")
        lines = f.readlines()
        f.close()

        in_ocat = False
        ocat = {}

        for line in lines:
            if line.startswith("LATEST OCAT INFO"):
                words = line.strip().split()
                obsid = words[-1]
                ocat[obsid] = {}
                in_ocat = True
                continue
            if in_ocat:
                words = line.strip().split()
                num_words = len(words)
                this_obsid = ocat[obsid]
                if line.startswith("Target name"):
                    idx_si = words.find("SI")
                    this_obsid["target_name"] = " ".join(words[2:idx_si])
                    this_obsid["si_mode"] = words[-1]
                elif line.startswith("Instrument"):
                    this_obsid["instrument"] = words[1]
                    this_obsid["grating"] = words[3]
                    this_obsid["type"] = words[5]
                elif line.startswith("Exposure"):
                    this_obsid["exposure_time"] = words[2]
                    this_obsid["remaining_exposure_time"] = words[6]
                elif line.startswith("Offset"):
                    this_obsid["offset"] = {}
                    this_obsid["offset"]["y"] = float(words[2])
                    this_obsid["offset"]["z"] = float(words[4])
                    if num_words == 7:
                        this_obsid["offset"]["z-sim"] = float(words[-1])
                    else:
                        this_obsid["offset"]["z-sim"] = 0.0
                elif line.startswith("ACIS Exposure"):
                    this_obsid["exposure_mode"] = words[3]
                    this_obsid["event_tm_format"] = words[7]
                    if num_words > 10:
                        this_obsid["frame_time"] = words[-1]
                    else:
                        this_obsid["frame_time"] = None
                elif line.startswith("Duty Cycle"):
                    if words[2] == "Y":
                        pass
                    else:
                        this_obsid["duty_cycle"] = None
                elif line.startswith("Onchip Summing"):
                    if words[2] == "Y":
                        this_obsid["onchip_summing"]["rows"] = words[4]
                        this_obsid["onchip_summing"]["columns"] = words[6]
                    else:
                        this_obsid["onchip_summing"] = None
                elif line.startswith("Event Filter"):
                    pass
                elif line.startswith("Window Filter"):
                    pass
                elif line.startswith("Height"):
                    pass
                elif line.startswith("Lower Energy"):
                    pass
                elif line.startswith("Dither"):
                    pass
                elif line.startswith("Cycle"):
                    this_obsid["cycle"] = words[2]
                    this_obsid["obj_flag"] = words[-1]
                    in_ocat = False

        self.ocat = ocat

    def __getitem__(self, key):
        return self.ocat[key]

    def __contains__(self, item):
        return item in self.ocat
