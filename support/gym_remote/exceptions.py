import gym_remote as gr


class GymRemoteErrorMeta(type):
    ID_MAX = 0
    ID_LIST = []

    def __new__(cls, name, bases, dictionary):
        dictionary['ID'] = cls.ID_MAX
        cls.ID_MAX += 1
        try:
            bases = (*bases, GymRemoteError)
        except NameError:
            assert name == 'GymRemoteError'
        newcls = super(GymRemoteErrorMeta, cls).__new__(cls, name, bases, dictionary)
        cls.ID_LIST.append(newcls)
        return newcls

    @classmethod
    def make(cls, id, *args, **kwargs):
        return cls.ID_LIST[id](*args, **kwargs)


class GymRemoteError(RuntimeError, metaclass=GymRemoteErrorMeta):
    pass


class TimestepTimeoutError(TimeoutError, metaclass=GymRemoteErrorMeta):
    pass


class WallClockTimeoutError(TimeoutError, metaclass=GymRemoteErrorMeta):
    pass


class ClientDisconnectError(gr.Bridge.Closed, metaclass=GymRemoteErrorMeta):
    pass


class ServerDisconnectError(gr.Bridge.Closed, metaclass=GymRemoteErrorMeta):
    pass


class ResetError(metaclass=GymRemoteErrorMeta):
    pass


def make(id, *args, **kwargs):
    return GymRemoteErrorMeta.make(id, *args, **kwargs)
