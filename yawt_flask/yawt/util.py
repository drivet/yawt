import yaml

class Date(object):
    def __init__(self, year, month, day):
        self.year = year
        self.month = month
        self.day = day
        
    def __str__(self):
        dl = [str(self.year)]
        if self.month is not None: dl.append(str(self.month))
        if self.day is not None: dl.append(str(self.day))
        return '/'.join(dl)
    
def has_method(obj, method):
    return hasattr(obj,method) and callable(getattr(obj, method))
    
def load_yaml(filename):
    f = open(filename, 'r')
    obj = yaml.load(f)
    f.close()
    return obj
