import gym
import time

from gym_remote import Bridge, FloatChannel, BoolChannel
import gym_remote.exceptions as gre


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

    def serve(self, timestep_limit=None, wallclock_limit=None, ignore_reset=False):
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

        done = True

        while timestep_limit is None or ts < timestep_limit:
            if wallclock_limit:
                t = time.time()
                if t >= end:
                    self.bridge.close(exception=gre.WallClockTimeoutError)
                    break
                self.bridge.settimeout(end - t)
            try:
                self.bridge.recv()
            except Bridge.Timeout:
                self.bridge.close(exception=gre.WallClockTimeoutError)
                break
            except Bridge.Closed:
                self.bridge.close(exception=gre.ClientDisconnectError)
                break

            if self.ch_reset.value:
                if ignore_reset and not done:
                    self.bridge.exception(gre.ResetError)
                    self.bridge.send()
                    continue
                self.ch_ob.value = self.env.reset()
                self.ch_reset.value = False
                self.ch_reward.value = 0
                self.ch_done.value = False
                done = False
            else:
                if ignore_reset and done:
                    self.bridge.exception(gre.ResetError)
                    self.bridge.send()
                    continue
                ob, rew, done, _ = self.env.step(self.ch_ac.value)
                self.ch_ob.value = ob
                self.ch_reward.value = rew
                self.ch_done.value = done
            self.bridge.send()
            ts += 1

        if timestep_limit and ts >= timestep_limit:
            self.bridge.close(exception=gre.TimestepTimeoutError)
        return ts

    def close(self):
        self.bridge.close()
        self.env.close()
