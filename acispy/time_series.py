class TimeSeriesData(object):
    def __init__(self, table=None):
        if table is None:
            table = {}
        self.table = table

    def __getitem__(self, item):
        return self.table[item]

    def __contains__(self, item):
        return item in self.table

    def keys(self):
        return list(self.table.keys())

    def values(self):
        return list(self.table.values())

    def items(self):
        return list(self.table.items())


class EmptyTimeSeries(TimeSeriesData):
    def __init__(self):
        super(EmptyTimeSeries, self).__init__()
