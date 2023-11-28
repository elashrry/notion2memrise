"""Error classes"""
class MinNumberOfLevels(Exception):
    def __init__(self):
        self.message = "The course must have at least two levels"
        super().__init__(self.message)