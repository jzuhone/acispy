class TimeSeriesData(object):
    def __init__(self, table, times):
        self.table = table
        self.times = times

    def __getitem__(self, item):
        return self.table[item]

    def __contains__(self, item):
        return item in self.table

    def keys(self):
        return list(self.table.keys())
