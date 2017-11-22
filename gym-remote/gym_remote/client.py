import gym

from gym_remote import Bridge

class RemoteEnv(gym.Env):
    def __init__(self, directory):
        self.bridge = Bridge(directory)
        self.bridge.connect()
        self.bridge.configure_client()
        self._ac = self.bridge._channels['ac']
        self._ob = self.bridge._channels['ob']
        self._reward = self.bridge._channels['reward']
        self._done = self.bridge._channels['done']
        self.action_space = self.unwrap(self._ac)
        self.observation_space = self.unwrap(self._ob)

    def unwrap(self, space):
        if space.annotations['type'] == 'MultiBinary':
            return gym.spaces.MultiBinary(space.annotations['n'])
        if space.annotations['type'] == 'Discrete':
            return gym.spaces.Discrete(space.annotations['n'])
        if space.annotations['type'] == 'MultiDiscrete':
            return gym.spaces.MultiDiscrete(space.shape)
        if space.annotations['type'] == 'Box':
            return gym.spaces.Box(low=0, high=255, shape=space.shape)

    def _step(self, action):
        self._ac.value = action
        self.bridge.send()
        self.bridge.recv()
        return self._ob.value, self._reward.value, self._done.value, {}
