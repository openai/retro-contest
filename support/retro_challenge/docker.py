import argparse
import docker
import os
import random
import requests.exceptions
import sys


def run(game, state=None, entry=None, **kwargs):
    client = docker.from_env()
    remote_command = ['retro-challenge-remote', 'run', game, state, '-b', 'results/bk2', '-m', 'results']
    agent_command = []

    if kwargs.get('wallclock_limit') is not None:
        remote_command.extend(['-W', str(kwargs['wallclock_limit'])])
    if kwargs.get('timestep_limit') is not None:
        remote_command.extend(['-T', str(kwargs['timestep_limit'])])
    if kwargs.get('discrete_actions'):
        remote_command.extend(['-D'])

    if entry:
        agent_command.append(entry)
        if kwargs.get('entry_args'):
            agent_command.extend(kwargs['entry_args'])

    if kwargs.get('resultsdir'):
        results = os.path.realpath(kwargs['resultsdir'])
    else:
        results = kwargs.get('resultsvol', 'compo-results')
    os.makedirs(results, exist_ok=True)

    container_kwargs = {'detach': True, 'network_disabled': True}

    rand = ''.join(random.sample('abcdefghijklmnopqrstuvwxyz0123456789', 8))
    bridge = client.volumes.create('compo-tmp-vol-%s' % rand, driver='local', driver_opts={'type': 'tmpfs', 'device': 'tmpfs'})
    remote = client.containers.run('remote-env', remote_command,
                                   volumes={'compo-tmp-vol-%s' % rand: {'bind': '/root/compo/tmp'},
                                            results: {'bind': '/root/compo/results'}},
                                   **container_kwargs)

    try:
        agent = client.containers.run('agent', agent_command,
                                      volumes={'compo-tmp-vol-%s' % rand: {'bind': '/root/compo/tmp'}},
                                      runtime=kwargs.get('runtime', 'nvidia'),
                                      **container_kwargs)
    except:
        remote.kill()
        raise

    a_exit = None

    try:
        # Wait to make sure agent doesn't die immediately
        a_exit = agent.wait(timeout=5)
        remote.kill()
    except requests.exceptions.RequestException:
        pass

    r_exit = None
    try:
        r_exit = remote.wait()
    except KeyboardInterrupt:
        remote.kill()
    try:
        a_exit = agent.wait(timeout=5)
    except requests.exceptions.RequestException:
        agent.kill()

    logs = {
        'remote': (r_exit, remote.logs(stdout=True), remote.logs(stderr=True)),
        'agent': (a_exit, agent.logs(stdout=True), agent.logs(stderr=True))
    }

    remote.remove()
    agent.remove()
    bridge.remove()
    if 'resultsdir' in kwargs:
        with open(os.path.join(results, 'remote-stdout.txt'), 'w') as f:
            f.write(logs['remote'][1].decode('utf-8'))
        with open(os.path.join(results, 'remote-stderr.txt'), 'w') as f:
            f.write(logs['remote'][2].decode('utf-8'))
        with open(os.path.join(results, 'agent-stdout.txt'), 'w') as f:
            f.write(logs['agent'][1].decode('utf-8'))
        with open(os.path.join(results, 'agent-stderr.txt'), 'w') as f:
            f.write(logs['agent'][2].decode('utf-8'))
    return logs


def run_args(args):
    kwargs = {
        'entry_args': args.args,
        'wallclock_limit': args.wallclock_limit,
        'timestep_limit': args.timestep_limit,
        'discrete_actions': args.discrete_actions,
        'resultsdir': args.results_dir,
    }

    if args.no_nv:
        kwargs['runtime'] = None

    results = run(args.game, args.state, args.entry, **kwargs)
    if results['remote'][0] or results['agent'][0]:
        sys.exit(1)


def init_parser(parser):
    parser.set_defaults(func=run_args)
    parser.add_argument('game', type=str, help='Name of the game to run')
    parser.add_argument('state', type=str, default=None, nargs='?', help='Name of initial state')
    parser.add_argument('--entry', '-e', type=str, help='Name of agent entry point')
    parser.add_argument('--args', '-A', type=str, nargs='+', help='Extra agent entry arguments')
    parser.add_argument('--wallclock-limit', '-W', type=float, default=None, help='Maximum time to run in seconds')
    parser.add_argument('--timestep-limit', '-T', type=int, default=None, help='Maximum time to run in timesteps')
    parser.add_argument('--no-nv', '-N', action='store_true', help='Disable Nvidia runtime')
    parser.add_argument('--results-dir', '-r', type=str, help='Path to output results')
    parser.add_argument('--discrete-actions', '-D', action='store_true', help='Use a discrete action space')


def main(argv=sys.argv[1:]):
    parser = argparse.ArgumentParser(description='Run Retro Challenge support code')
    init_parser(parser)
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == '__main__':
    main()
