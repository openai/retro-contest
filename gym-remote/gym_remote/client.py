import gym

from gym_remote import Bridge

class RemoteEnv(gym.Env):
    def __init__(self, directory):
        self.bridge = Bridge(directory)
        self.bridge.connect()
        self.bridge.configure_client()
        self.ch_ac = self.bridge._channels['ac']
        self.ch_ob = self.bridge._channels['ob']
        self.ch_reward = self.bridge._channels['reward']
        self.ch_done = self.bridge._channels['done']
        self.ch_reset = self.bridge._channels['reset']
        self.action_space = self.unwrap(self.ch_ac)
        self.observation_space = self.unwrap(self.ch_ob)

    def unwrap(self, space):
        if space.annotations['type'] == 'MultiBinary':
            return gym.spaces.MultiBinary(space.annotations['n'])
        if space.annotations['type'] == 'Discrete':
            return gym.spaces.Discrete(space.annotations['n'])
        if space.annotations['type'] == 'MultiDiscrete':
            if gym.version >= '0.9.5':
                return gym.spaces.MultiDiscrete(space.shape[0])
            else:
                return gym.spaces.MultiDiscrete(space.shape)
        if space.annotations['type'] == 'Box':
            return gym.spaces.Box(low=0, high=255, shape=space.shape)

    def _step(self, action):
        self.ch_ac.value = action
        self.bridge.send()
        if not self.bridge.recv():
            self.close()
            raise BrokenPipeError('Remote has shut down')

        return self.ch_ob.value, self.ch_reward.value, self.ch_done.value, {}

    def _reset(self):
        self.ch_reset.value = True
        self.bridge.send()
        self.bridge.recv()
        return self.ch_ob.value
