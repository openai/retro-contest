import gym

from gym_remote import Bridge, FloatChannel, BoolChannel

class RemoteEnvWrapper(gym.Wrapper):
    def __init__(self, env, directory):
        gym.Wrapper.__init__(self, env)
        self.bridge = Bridge(directory)
        self.action_space = self.bridge.wrap('ac', env.action_space)
        self.observation_space = self.bridge.wrap('ob', env.observation_space)
        self.reward = self.bridge.add_channel('reward', FloatChannel())
        self.done = self.bridge.add_channel('done', BoolChannel())
        self.bridge.listen()

    def serve(self, timestep_limit=None):
        self.bridge.server_accept()
        ts = 0
        while timestep_limit is None or ts < timestep_limit:
            self.bridge.recv()
            ob, rew, done, _ = self.env.step(self.action_space.value)
            self.observation_space.value = ob
            self.reward.value = rew
            self.done.value = done
            self.bridge.send()
            ts += 1
