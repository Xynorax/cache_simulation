class Line:
    """Class representing a line within a processor's main cache."""

    def __init__(self, size):
        self.use = 0
        self.modified = 0
        self.valid = 0
        self.tag = 0
        self.data = [0] * size
        self.age_counter = 0
        self.hits = 0
        self.hit = 0
        self.age_priority = 0
        self.preuse_distance = 0
        self.rrpv = 3
        self.r = 0
        self.signature = 0
        self.level = 0
        self.lazy_updated = 0
