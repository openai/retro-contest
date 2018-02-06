import retro
import retro_challenge.remote
import gym


def make(game, state, discrete_actions=False):
    use_restricted_actions = retro.ACTIONS_FILTERED
    if discrete_actions:
        use_restricted_actions = retro.ACTIONS_DISCRETE
    env = retro.make(game, state, scenario='contest', use_restricted_actions=use_restricted_actions)
    env = retro_challenge.remote.StochasticFrameSkip(env, n=4, stickprob=0.25)
    env = gym.wrappers.TimeLimit(env, max_episode_steps=4500)
    return env
