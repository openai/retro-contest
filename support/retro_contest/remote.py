import argparse
import gym
import gym_remote.server as grs
import os
import retro
import retro_contest
import retro_contest.local
import sys


def make(game, state=retro.STATE_DEFAULT, bk2dir=None, monitordir=None, discrete_actions=False, socketdir=None):
    if bk2dir:
        os.makedirs(bk2dir, exist_ok=True)
    env = retro_contest.local.make(game, state, discrete_actions=discrete_actions, bk2dir=bk2dir)
    if monitordir:
        env = retro_contest.Monitor(env, os.path.join(monitordir, 'monitor.csv'), os.path.join(monitordir, 'log.csv'))
    env = grs.RemoteEnvWrapper(env, socketdir)
    return env


def run(game, state,
        wallclock_limit=None, timestep_limit=None,
        monitordir=None, bk2dir=None, socketdir=None,
        discrete_actions=False, daemonize=False):
    if daemonize:
        pid = os.fork()
        if pid > 0:
            return

    env = make(game, state, bk2dir, monitordir, discrete_actions, socketdir)
    env.serve(timestep_limit=timestep_limit, wallclock_limit=wallclock_limit, ignore_reset=True)


def run_args(args):
    run(args.game, args.state,
        wallclock_limit=args.wallclock_limit,
        timestep_limit=args.timestep_limit,
        bk2dir=args.bk2dir,
        monitordir=args.monitordir,
        socketdir=args.socketdir,
        discrete_actions=args.discrete_actions,
        daemonize=args.daemonize)


def list_games(args):
    games = retro.data.list_games()
    if args.system:
        games = [game for game in games if game.endswith('-' + args.system)]
    games.sort()
    print(*games, sep='\n')


def list_states(args):
    if args.game:
        games = args.game
    else:
        games = retro.data.list_games()
        games.sort()
    for game in games:
        states = retro.data.list_states(game)
        print(game + ':')
        states.sort()
        for state in states:
            print('  ' + state)


def main(argv=sys.argv[1:]):
    parser = argparse.ArgumentParser(description='Run support code for OpenAI Retro Contest remote environment')
    parser.set_defaults(func=lambda args: parser.print_help())
    parser.add_argument('--data-dir', type=str, help='Use a custom data directory (must be named `data`)')

    subparsers = parser.add_subparsers()
    parser_run = subparsers.add_parser('run', description='Run Remote environment')
    parser_list = subparsers.add_parser('list', description='List information about environments')

    parser_run.set_defaults(func=run_args)
    parser_run.add_argument('game', type=str, help='Name of the game to run')
    parser_run.add_argument('state', type=str, default=retro.State.DEFAULT, nargs='?', help='Name of initial state')
    parser_run.add_argument('--monitordir', '-m', type=str, help='Directory to hold monitor files')
    parser_run.add_argument('--bk2dir', '-b', type=str, help='Directory to hold BK2 movies')
    parser_run.add_argument('--socketdir', '-s', type=str, default='tmp/sock', help='Directory to hold sockets')
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
    if args.data_dir:
        retro.data.path(args.data_dir)
    args.func(args)


if __name__ == '__main__':
    main()
