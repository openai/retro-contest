import retro
import retro_contest
import gym


def make(game, state, discrete_actions=False, bk2dir=None):
    use_restricted_actions = retro.ACTIONS_FILTERED
    if discrete_actions:
        use_restricted_actions = retro.ACTIONS_DISCRETE
    try:
        env = retro.make(game, state, scenario='contest', use_restricted_actions=use_restricted_actions)
    except Exception:
        env = retro.make(game, state, use_restricted_actions=use_restricted_actions)
    if bk2dir:
        env.auto_record(bk2dir)
    env = retro_contest.StochasticFrameSkip(env, n=4, stickprob=0.25)
    env = gym.wrappers.TimeLimit(env, max_episode_steps=4500)
    return env
