from collections import namedtuple

_EventBase = namedtuple("Event", "type, src, user, msg")


class Message(_EventBase):
    __slots__ = ()

    def __new__(cls, src, user, msg):
        self = super(Message, cls).__new__(cls, cls, src=src, user=user, msg=msg)
        return self


class Join(_EventBase):
    __slots__ = ()

    def __new__(cls, src, user):
        self = super(Join, cls).__new__(cls, cls, src=src, user=user, msg=None)
        return self


class Part(_EventBase):
    __slots__ = ()
    def __new__(cls, src, user):
        self = super(Part, cls).__new__(cls, cls, src=src, user=user, msg=None)
        return self


class Kick(_EventBase):
    __slots__ = ()

    def __new__(cls, src, user, msg):
        self = super(Kick, cls).__new__(cls, cls, src=src, user=user, msg=msg)
        return self


class Topic(_EventBase):
    __slots__ = ()

    def __new__(cls, src, user, msg):
        self = super(Topic, cls).__new__(cls, cls, src=src, user=user, msg=msg)
        return self


class Action(_EventBase):
    __slots__ = ()

    def __new__(cls, src, user, msg):
        self = super(Action, cls).__new__(cls, cls, src=src, user=user, msg=msg)
        return self

