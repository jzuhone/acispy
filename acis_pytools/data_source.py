from acis_pytools.msids import MSIDs
from acis_pytools.states import States
from acis_pytools.model import Model

def setup_method(obj, att, method):
    def _method(*args, **kwargs):
        setattr(obj, att, method(*args, **kwargs))
    return _method

class FetchObject(object):
    def __init__(self, ds, att, obj_class):
        self.ds = ds
        for name in obj_class.__dict__.keys():
            if name.startswith("from"):
                cm = setup_method(self.ds, att, getattr(obj_class, name))
                setattr(self, name, cm)

class DataSource(object):
    def __init__(self):
        self.msids = None
        self.states = None
        self.model = None
        self.get_msids = FetchObject(self, "msids", MSIDs)
        self.get_states = FetchObject(self, "states", States)
        self.get_model = FetchObject(self, "model", Model)

    def __getitem__(self, item):
        src = getattr(self, item[0])
        return src[item[1]]