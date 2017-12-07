import gym
import gym.spaces
import json
import numpy as np
import os
import socket


class Channel:
    def __init__(self):
        self.sock = None
        self.dirty = False
        self._value = None
        self.annotations = {}

    def set_socket(self, sock):
        self.sock = sock

    def set_base(self, base):
        pass

    def parse(self, value):
        return value

    def unparse(self, value):
        return value

    @property
    def value(self):
        return self.unparse(self._value)

    @value.setter
    def value(self, value):
        self._value = self.parse(value)
        self.dirty = True

    def serialize(self):
        return self._value

    def deserialize(self, value):
        self._value = self.parse(value)
        self.dirty = False

    @staticmethod
    def make(type, shape, annotations):
        types = {
            'int': IntChannel,
            'float': FloatChannel,
            'bool': BoolChannel,
            'int_fold': IntFoldChannel,
            'np': NpChannel,
        }
        cls = types[type]
        if shape:
            ob = cls(*eval(shape, {}, {'dtype': np.dtype}))
        else:
            ob = cls()
        if annotations:
            for key, value in annotations.items():
                ob.annotate(key, value)
        return ob

    def annotate(self, name, value):
        self.annotations[name] = str(value)


class IntChannel(Channel):
    TYPE = 'int'
    SHAPE = None

    def parse(self, value):
        return int(value)


class FloatChannel(Channel):
    TYPE = 'float'
    SHAPE = None

    def parse(self, value):
        return float(value)


class BoolChannel(Channel):
    TYPE = 'bool'
    SHAPE = None

    def parse(self, value):
        return bool(value)


class IntFoldChannel(Channel):
    TYPE = 'int_fold'

    def __init__(self, folds):
        super(IntFoldChannel, self).__init__()
        self.folds = list(folds)
        self.SHAPE = str(folds) + ','

    def parse(self, value):
        folded = 0
        coeff = 1
        for fold, entry in zip(self.folds, value):
            folded += entry * coeff
            coeff *= fold
        return int(folded)

    def unparse(self, value):
        if value is None:
            return None
        unfolded = []
        coeff = 1
        for fold in self.folds:
            unfolded.append((value // coeff) % fold)
            coeff *= fold
        return unfolded

    def deserialize(self, value):
        self._value = int(value)
        self.dirty = False


class NpChannel(Channel):
    TYPE = 'np'

    def __init__(self, shape, dtype):
        super(NpChannel, self).__init__()
        self.SHAPE = '%s, %s' % (shape, 'dtype("%s")' % np.dtype(dtype).name)
        self.shape = shape
        self.dtype = dtype

    def set_base(self, base):
        self._value = np.memmap(base, mode='w+', dtype=self.dtype, shape=self.shape)

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        np.copyto(self._value, value)
        self.dirty = True

    def serialize(self):
        return True

    def deserialize(self, value):
        self.dirty = False


class Bridge:
    Timeout = socket.timeout
    Closed = BrokenPipeError

    def __init__(self, base):
        self.base = base
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

        def close(message):
            self.close()
            if 'exception' in message:
                import gym_remote.exceptions as gre
                exception = gre.make(message['exception'], message['reason'])
            else:
                exception = self.Closed(message['reason'])
            raise exception

        self._channels = {}
        self.connection = None
        self._buffer = []
        self._message_handlers = {
            'update': self.update_vars,
            'close': close
        }

    def __del__(self):
        self.close()

    def add_channel(self, name, channel):
        if name in self._channels:
            raise KeyError(name)
        self._channels[name] = channel
        return channel

    def wrap(self, name, space):
        channel = None
        if isinstance(space, gym.spaces.MultiBinary):
            if space.n < 64:
                channel = IntFoldChannel([2] * space.n)
            else:
                channel = NpChannel((space.n,), np.uint8)
            channel.annotate('n', space.n)
            channel.annotate('type', 'MultiBinary')
        elif isinstance(space, gym.spaces.Discrete):
            channel = IntChannel()
            channel.annotate('n', space.n)
            channel.annotate('type', 'Discrete')
        elif isinstance(space, gym.spaces.MultiDiscrete):
            if gym.version >= '0.9.5':
                channel = NpChannel(space.shape, np.int64)
                channel.annotate('shape', space.shape[0])
            else:
                channel = NpChannel((space.shape,), np.int64)
                channel.annotate('shape', space.shape)
            channel.annotate('type', 'MultiDiscrete')
        elif isinstance(space, gym.spaces.Box):
            channel = NpChannel(space.shape, np.uint8)
            channel.annotate('type', 'Box')
            channel.annotate('shape', space.shape)

        if not channel:
            raise NotImplementedError('Unsupported space')

        return self.add_channel(name, channel)

    def configure_channels(self, channel_info):
        for name, info in channel_info.items():
            self._channels[name] = Channel.make(*info)

    def describe_channels(self):
        description = {}
        for name, channel in self._channels.items():
            description[name] = (channel.TYPE, channel.SHAPE, channel.annotations)
        return description

    def listen(self):
        sock_path = os.path.join(self.base, 'sock')
        self.sock.bind(sock_path)
        self.sock.listen(1)

    def connect(self):
        sock_path = os.path.join(self.base, 'sock')
        self.sock.connect(sock_path)
        self.connection = self.sock

    def server_accept(self):
        self.connection, _ = self.sock.accept()
        for name, channel in self._channels.items():
            channel.set_socket(self.connection)
            channel.set_base(os.path.join(self.base, name))
        description = self.describe_channels()
        self._send_message('description', description)

    def configure_client(self):
        description = self._recv_message()
        assert description['type'] == 'description'
        self.configure_channels(description['content'])
        for name, channel in self._channels.items():
            channel.set_socket(self.connection)
            channel.set_base(os.path.join(self.base, name))
        return dict(self._channels)

    def _send_message(self, type, content):
        if not self.connection:
            raise self.Closed
        message = {
            'type': type,
            'content': content
        }
        # All messages end in a form feed
        message = json.dumps(message) + '\f'
        self.connection.sendall(message.encode('utf8'))

    def _recv_message(self):
        if not self.connection:
            raise self.Closed
        while len(self._buffer) < 2:
            # There are no fully buffered messages
            message = self.connection.recv(4096)
            if not message:
                raise self.Closed
            message = message.split(b'\f')
            if self._buffer:
                self._buffer[-1] += message.pop(0)
            self._buffer.extend(message)
        message = self._buffer.pop(0)
        return json.loads(message.decode('utf8'))

    def update_vars(self, vars):
        for name, value in vars.items():
            self._channels[name].deserialize(value)

    def send(self):
        content = {}
        for name, channel in self._channels.items():
            if channel.dirty:
                content[name] = channel.serialize()
        try:
            self._send_message('update', content)
        except self.Closed as e:
            try:
                while True:
                    self.recv()
            except self.Closed as f:
                e = f
            self.close()
            raise e

    def recv(self):
        message = self._recv_message()
        if not message:
            raise self.Closed
        self._message_handlers[message['type']](message['content'])
        return True

    def close(self, reason=None, exception=None):
        if self.sock:
            try:
                kwargs = {'reason': reason}
                if exception:
                    kwargs['exception'] = exception.ID
                self._send_message('close', kwargs)
            except self.Closed:
                pass
            self.sock.close()
        if self.connection and self.connection != self.sock:
            self.connection.close()
            try:
                os.unlink(os.path.join(self.base, 'sock'))
            except OSError:
                pass
            for name, channel in self._channels.items():
                try:
                    os.unlink(os.path.join(self.base, name))
                except OSError:
                    pass
        self.connection = None
        self.sock = None

    def settimeout(self, timeout):
        self.sock.settimeout(timeout)
        if self.connection:
            self.connection.settimeout(timeout)

    def __del__(self):
        self.close()
