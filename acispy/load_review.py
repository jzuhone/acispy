import os
from collections import defaultdict

lr_root = "/data/acis/LoadReviews"
lr_file = "ACIS-LoadReview.txt"

class LoadReview(object):
    def __init__(self, load_name):
        self.load_name = load_name
        self.load_week = load_name[:-1]
        self.load_letter = load_name[-1].lower()
        self.load_file = os.path.join(lr_root, self.load_week,
                                      "ofls%s" % self.load_letter,
                                      lr_file)
        self.events = defaultdict(list)

