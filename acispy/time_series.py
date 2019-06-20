class TimeSeriesData(object):
    _is_empty = False

    def __init__(self, table=None):
        if table is None:
            table = {}
        self.table = table

    def __getitem__(self, item):
        return self.table[item]

    def __contains__(self, item):
        return item in self.table

    def __iter__(self):
        for k in self.table:
            yield k

    def keys(self):
        return self.table.keys()

    def values(self):
        return self.table.values()

    def items(self):
        return self.table.items()


class EmptyTimeSeries(TimeSeriesData):
    _is_empty = True

    def __init__(self):
        super(EmptyTimeSeries, self).__init__()
