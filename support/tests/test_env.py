import gym
import gym.spaces
import gym_remote as gr
import gym_remote.exceptions as gre
import numpy as np
import os
import time

from . import process_wrapper


class BitEnv(gym.Env):
    def __init__(self):
        self.action_space = gym.spaces.Discrete(8)
        self.observation_space = gym.spaces.Discrete(2)

    def step(self, action):
        assert self.action_space.contains(action)
        observation = action & 1
        reward = float(action & 2)
        done = bool(action & 4)
        return observation, reward, done, {}

    def reset(self):
        return 0


class MultiBitEnv(gym.Env):
    def __init__(self):
        self.action_space = gym.spaces.MultiBinary(3)
        self.observation_space = gym.spaces.Discrete(2)

    def step(self, action):
        assert self.action_space.contains(action)
        observation = action[0]
        reward = float(action[1])
        done = bool(action[2])
        return observation, reward, done, {}

    def reset(self):
        return 0


class StepEnv(gym.Env):
    def __init__(self):
        self.action_space = gym.spaces.Discrete(2)
        self.observation_space = gym.spaces.Discrete(1)
        self.reward = 0
        self.done = False

    def step(self, action):
        if not self.done:
            self.reward += 1
        if action:
            self.done = True
        return 0, self.reward, self.done, {}

    def reset(self):
        self.reward = 0
        self.done = False
        return 0


def test_split(process_wrapper):
    env = process_wrapper(BitEnv)

    assert env.step(0) == (0, 0, False, {})
    assert env.step(1) == (1, 0, False, {})
    assert env.step(2) == (0, 2, False, {})
    assert env.step(3) == (1, 2, False, {})
    assert env.step(4) == (0, 0, True, {})


def test_multibinary_split(process_wrapper):
    env = process_wrapper(MultiBitEnv)

    assert env.step(np.array([0, 0, 0], np.int8)) == (0, 0, False, {})
    assert env.step(np.array([1, 0, 0], np.int8)) == (1, 0, False, {})
    assert env.step(np.array([0, 1, 0], np.int8)) == (0, 1, False, {})
    assert env.step(np.array([1, 1, 0], np.int8)) == (1, 1, False, {})
    assert env.step(np.array([0, 0, 1], np.int8)) == (0, 0, True, {})


def test_reset(process_wrapper):
    env = process_wrapper(StepEnv)

    assert env.reset() == 0
    assert env.step(0) == (0, 1, False, {})
    assert env.step(0) == (0, 2, False, {})
    assert env.step(1) == (0, 3, True, {})
    assert env.step(0) == (0, 3, True, {})
    assert env.reset() == 0
    assert env.step(0) == (0, 1, False, {})
    assert env.step(0) == (0, 2, False, {})
    assert env.step(1) == (0, 3, True, {})
    assert env.step(0) == (0, 3, True, {})


def test_reset_exception(process_wrapper):
    env = process_wrapper(StepEnv, ignore_reset=True)

    assert env.reset() == 0
    assert env.step(0) == (0, 1, False, {})
    assert env.step(0) == (0, 2, False, {})
    assert env.step(1) == (0, 3, True, {})
    assert env.reset() == 0
    assert env.step(0) == (0, 1, False, {})
    assert env.step(0) == (0, 2, False, {})
    assert env.step(1) == (0, 3, True, {})
    try:
        assert env.step(0) == (0, 3, True, {})
    except gre.ResetError:
        return
    except:
        assert False, 'Incorrect exception'
    assert False, 'No exception'


def test_ts_limit(process_wrapper):
    env = process_wrapper(StepEnv, timestep_limit=5)

    assert env.step(0) == (0, 1, False, {})
    assert env.step(0) == (0, 2, False, {})
    assert env.step(0) == (0, 3, False, {})
    assert env.step(0) == (0, 4, False, {})
    assert env.step(0) == (0, 5, False, {})
    try:
        env.step(0)
    except gre.TimestepTimeoutError as e:
        return
    except:
        assert False, 'Incorrect exception'
    assert False, 'Remote did not shut down'


def test_wc_limit(process_wrapper):
    env = process_wrapper(StepEnv, wallclock_limit=0.1)

    assert env.step(0) == (0, 1, False, {})
    time.sleep(0.2)
    try:
        env.step(0)
    except gre.WallClockTimeoutError as e:
        return
    except:
        assert False, 'Incorrect exception'
    assert False, 'Remote did not shut down'


def test_cleanup(process_wrapper):
    env = process_wrapper(BitEnv)

    assert os.path.exists(os.path.join(env.bridge.base, 'sock'))

    env.close()
    time.sleep(0.1)

    assert not os.path.exists(os.path.join(env.bridge.base, 'sock'))
