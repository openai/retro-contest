import csv
import gym
import numpy as np
import time


class StochasticFrameSkip(gym.Wrapper):
    def __init__(self, env, n, stickprob):
        gym.Wrapper.__init__(self, env)
        self.n = n
        self.stickprob = stickprob
        self.curac = None
        self.rng = np.random.RandomState()

    def reset(self, **kwargs):
        self.curac = None
        return self.env.reset(**kwargs)

    def step(self, ac):
        done = False
        totrew = 0
        for i in range(self.n):
            # First step after reset, use action
            if self.curac is None:
                self.curac = ac
            # First substep, delay with probability=stickprob
            elif i == 0:
                if self.rng.rand() > self.stickprob:
                    self.curac = ac
            # Second substep, new action definitely kicks in
            elif i == 1:
                self.curac = ac
            ob, rew, done, info = self.env.step(self.curac)
            totrew += rew
            if done:
                break
        return ob, totrew, done, info


class Monitor(gym.Wrapper):
    def __init__(self, env, monitorfile, logfile=None):
        gym.Wrapper.__init__(self, env)
        self.file = open(monitorfile, 'w')
        self.csv = csv.DictWriter(self.file, ['r', 'l', 't'])
        self.log = open(logfile, 'w')
        self.logcsv = csv.DictWriter(self.log, ['l', 't'])
        self.episode_reward = 0
        self.episode_length = 0
        self.total_length = 0
        self.start = None
        self.csv.writeheader()
        self.file.flush()
        self.logcsv.writeheader()
        self.log.flush()

    def reset(self, **kwargs):
        if not self.start:
            self.start = time.time()
        else:
            self.csv.writerow({
                'r': self.episode_reward,
                'l': self.episode_length,
                't': time.time() - self.start
            })
            self.file.flush()
        self.episode_length = 0
        self.episode_reward = 0
        return self.env.reset(**kwargs)

    def step(self, ac):
        ob, rew, done, info = self.env.step(ac)
        self.episode_length += 1
        self.total_length += 1
        self.episode_reward += rew
        if self.total_length % 1000 == 0:
            self.logcsv.writerow({
                'l': self.total_length,
                't': time.time() - self.start
            })
            self.log.flush()
        return ob, rew, done, info

    def __del__(self):
        self.file.close()
