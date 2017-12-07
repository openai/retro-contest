import gym
import time

from gym_remote import Bridge, FloatChannel, BoolChannel

class RemoteEnvWrapper(gym.Wrapper):
    def __init__(self, env, directory):
        gym.Wrapper.__init__(self, env)
        self.bridge = Bridge(directory)
        self.ch_ac = self.bridge.wrap('ac', env.action_space)
        self.ch_ob = self.bridge.wrap('ob', env.observation_space)
        self.ch_reward = self.bridge.add_channel('reward', FloatChannel())
        self.ch_done = self.bridge.add_channel('done', BoolChannel())
        self.ch_reset = self.bridge.add_channel('reset', BoolChannel())
        self.bridge.listen()

    def serve(self, timestep_limit=None, wallclock_limit=None):
        if wallclock_limit is not None:
            end = time.time() + wallclock_limit
            self.bridge.settimeout(wallclock_limit)
        else:
            end = None
        ts = 0

        try:
            self.bridge.server_accept()
        except Bridge.Timeout:
            return ts

        while timestep_limit is None or ts < timestep_limit:
            if wallclock_limit:
                t = time.time()
                if t >= end:
                    break
                self.bridge.settimeout(end - t)
            try:
                self.bridge.recv()
            except (Bridge.Timeout, Bridge.Closed):
                break

            if self.ch_reset.value:
                self.ch_ob.value = self.env.reset()
                self.ch_reset.value = False
                self.ch_reward.value = 0
                self.ch_done.value = False
            else:
                ob, rew, done, _ = self.env.step(self.ch_ac.value)
                self.ch_ob.value = ob
                self.ch_reward.value = rew
                self.ch_done.value = done
            self.bridge.send()
            ts += 1

        self.bridge.close()
        return ts

    def _close(self):
        self.bridge.close()
        self.env.close()
