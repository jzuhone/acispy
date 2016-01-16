from __future__ import print_function
from six import string_types
import webbrowser

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

    def __contains__(self, item):
        return item in self.obsid

    def get(self, item, default=None):
        return self.obsid.get(item, default)

    def __getattr__(self, item):
        return self.obsid[item]

    def keys(self):
        return self.obsid.keys()

    def values(self):
        return self.obsid.values()

    def items(self):
        return self.obsid.items()

    def open_chaser(self):
        """
        Get the obsid information from ChaSeR in a web browser. 
        """
        url = "http://cda.cfa.harvard.edu/chaser/"
        url += "startViewer.do?menuItem=details&obsid=%s" % self.id
        webbrowser.open(url)

    def open_obscat_data_page(self):
        """
        Get the obsid information from ChaSeR in a web browser. 
        """
        url = 'https://icxc.harvard.edu/cgi-bin/mp/'
        url += "target_param.cgi?%s" % self.id
        webbrowser.open(url)

class Obscat(object):
    def __init__(self, ocat, subset=None):
        self.ocat = ocat
        self.subset = subset

    def keys(self):
        return self.ocat.keys()

    def items(self):
        return self.ocat.items()

    def values(self):
        return self.ocat.values()

    def __getitem__(self, obsid):
        if not isinstance(obsid, string_types):
            obsid = "%05d" % obsid
        return self.ocat[str(obsid)]

    def __contains__(self, obsid):
        return str(obsid) in self.ocat

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
        if item not in list(self.values())[0]:
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
            print("No ObsIDs with the criterion \"%s\" were found." % subset)
            return None
        else:
            return Obscat(new_ocat, subset=subset)
