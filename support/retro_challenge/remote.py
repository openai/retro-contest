import argparse
import gym
import gym_remote.server as grs
import numpy as np
import os
import retro
import sys


class StochasticFrameSkip(gym.Wrapper):
    def __init__(self, env, n, stickprob):
        gym.Wrapper.__init__(self, env)
        self.n = n
        self.stickprob = stickprob
        self.curac = None
        self.rng = np.random.RandomState()

    def _reset(self, **kwargs):
        self.curac = None
        return self.env.reset(**kwargs)

    def _step(self, ac):
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


def make(game, state, bk2dir=None, monitordir=None, discrete_actions=False, socketdir='tmp/sock'):
    if bk2dir:
        os.makedirs(bk2dir, exist_ok=True)
    use_restricted_actions = retro.ACTIONS_FILTERED
    if discrete_actions:
        use_restricted_actions = retro.ACTIONS_DISCRETE
    env = retro.make(game, state, record=bk2dir or False, use_restricted_actions=use_restricted_actions)
    env = StochasticFrameSkip(env, n=4, stickprob=0.25)
    env = gym.wrappers.TimeLimit(env, max_episode_steps=4500)
    env = grs.RemoteEnvWrapper(env, socketdir)
    return env


def run(game, state,
        wallclock_limit=None, timestep_limit=None,
        monitordir=None, bk2dir=None, socketdir='tmp/sock',
        discrete_actions=False, daemonize=False):
    if daemonize:
        pid = os.fork()
        if pid > 0:
            return

    env = make(game, state, bk2dir, monitordir, discrete_actions, socketdir)
    env.serve(timestep_limit=timestep_limit, wallclock_limit=wallclock_limit)


def run_args(args):
    run(args.game, args.state,
        wallclock_limit=args.wallclock_limit,
        timestep_limit=args.timestep_limit,
        bk2dir=args.bk2dir,
        monitordir=args.monitordir,
        discrete_actions=args.discrete_actions,
        daemonize=args.daemonize)


def list_games(args):
    games = retro.list_games()
    if args.system:
        games = [game for game in games if game.endswith('-' + args.system)]
    games.sort()
    print(*games, sep='\n')


def list_states(args):
    if args.game:
        games = args.game
    else:
        games = retro.list_games()
        games.sort()
    for game in games:
        states = retro.list_states(game)
        print(game + ':')
        states.sort()
        for state in states:
            print('  ' + state)


def main(argv=sys.argv[1:]):
    parser = argparse.ArgumentParser(description='Run support code for Retro Challenge remote environment')
    parser.set_defaults(func=lambda args: parser.print_help())
    subparsers = parser.add_subparsers()
    parser_run = subparsers.add_parser('run', description='Run Remote environment')
    parser_list = subparsers.add_parser('list', description='List information about environments')

    parser_run.set_defaults(func=run_args)
    parser_run.add_argument('game', type=str, help='Name of the game to run')
    parser_run.add_argument('state', type=str, default=None, nargs='?', help='Name of initial state')
    parser_run.add_argument('--monitordir', '-m', type=str, help='Directory to hold monitor files')
    parser_run.add_argument('--bk2dir', '-b', type=str, help='Directory to hold BK2 movies')
    parser_run.add_argument('--daemonize', '-d', action='store_true', default=False, help='Daemonize (background) the process')
    parser_run.add_argument('--wallclock-limit', '-W', type=float, default=None, help='Maximum time to run in seconds')
    parser_run.add_argument('--timestep-limit', '-T', type=int, default=None, help='Maximum time to run in timesteps')
    parser_run.add_argument('--discrete-actions', '-D', action='store_true', help='Use a discrete action space')

    parser_list.set_defaults(func=lambda args: parser_list.print_help())
    subparsers_list = parser_list.add_subparsers()
    parser_list_games = subparsers_list.add_parser('games', description='List games')
    parser_list_games.set_defaults(func=list_games)
    parser_list_games.add_argument('--system', '-s', type=str, help='List for a specific system only')

    parser_list_states = subparsers_list.add_parser('states', description='List')
    parser_list_states.set_defaults(func=list_states)
    parser_list_states.add_argument('game', type=str, default=None, nargs='*', help='List for specified games only')

    args = parser.parse_args(argv)
    args.func(args)


if __name__ == '__main__':
    main()
