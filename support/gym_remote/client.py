import gym
import time

from gym_remote import Bridge


class RemoteEnv(gym.Env):
    def __init__(self, directory, tries=8):
        self.bridge = Bridge(directory)

        # Try a few times to connect
        backoff = 2
        for x in range(tries):
            try:
                self.bridge.connect()
                break
            except FileNotFoundError:
                if x + 1 == tries:
                    raise
                time.sleep(backoff)
                backoff *= 2

        self.bridge.configure_client()
        self.ch_ac = self.bridge._channels['ac']
        self.ch_ob = self.bridge._channels['ob']
        self.ch_reward = self.bridge._channels['reward']
        self.ch_done = self.bridge._channels['done']
        self.ch_reset = self.bridge._channels['reset']
        self.action_space = self.bridge.unwrap(self.ch_ac)
        self.observation_space = self.bridge.unwrap(self.ch_ob)

    def step(self, action):
        self.ch_ac.value = action
        self.bridge.send()
        self.bridge.recv()

        return self.ch_ob.value, self.ch_reward.value, self.ch_done.value, {}

    def reset(self):
        self.ch_reset.value = True
        self.bridge.send()
        self.bridge.recv()
        return self.ch_ob.value

    def close(self):
        self.bridge.close()
