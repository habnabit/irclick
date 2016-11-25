import re


class Splut(object):

    def __init__(self, string, match, line):
        self.string = string
        self._match = match
        self._line = line

    @property
    def trailer(self):
        if self._match is None:
            return self.string
        else:
            return self._line[self._match.start():]

    @classmethod
    def args_of_line(cls, line):
        return [cls(m.group(0), m, line)
                for m in re.finditer(u'(?u)\\S+', line)]

    @classmethod
    def ensure(cls, obj):
        if isinstance(obj, cls):
            return obj
        else:
            return cls(obj, None, None)
