import argparse
import docker
import os
import sys


def run(game, state=None, entry=None, **kwargs):
    client = docker.from_env()
    remote_command = ['retro-challenge-remote', 'run', game, state, '-b', 'results/bk2', '-m', 'results/monitor']
    agent_command = ['retro-challenge-agent']

    if 'wallclock_limit' in kwargs:
        remote_command.extend(['-W', str(kwargs['wallclock_limit'])])
    if 'timestep_limit' is kwargs:
        remote_command.extend(['-T', str(kwargs['timestep_limit'])])

    if entry:
        agent_command.append(entry)
        if 'entry_args' in kwargs:
            agent_command.extend(kwargs['entry_args'])

    if 'resultsdir' in kwargs:
        results = os.path.realpath(kwargs['resultsdir'])
        os.makedirs(results, exist_ok=True)
    else:
        results = kwargs.get('resultsvol', 'compo-results')

    container_kwargs = {'detach': True, 'network_disabled': True}

    client.volumes.create('compo-tmp-vol', driver='local', driver_opts={'type': 'tmpfs', 'device': 'tmpfs'})
    remote = client.containers.run('remote-env', remote_command,
                                   volumes={'compo-tmp-vol': {'bind': '/root/compo/tmp'},
                                            results: {'bind': '/root/compo/results'}},
                                   **container_kwargs)

    agent = client.containers.run('compo-agent', agent_command,
                                  volumes={'compo-tmp-vol': {'bind': '/root/compo/tmp'}},
                                  runtime=kwargs.get('runtime', 'nvidia'),
                                  **container_kwargs)

    remote.wait()
    try:
        agent.wait(timeout=5)
    except requests.exceptions.ReadTimeout:
        agent.kill()

    logs = {
        'remote': (remote.logs(stdout=True), remote.logs(stderr=True)),
        'agent': (agent.logs(stdout=True), agent.logs(stderr=True))
    }

    remote.remove()
    agent.remove()
    return logs


def main(argv=sys.argv[1:]):
    parser = argparse.ArgumentParser(description='Run Retro Challenge Docker containers')
    parser.add_argument('game', type=str, help='Name of the game to run')
    parser.add_argument('state', type=str, default=None, nargs='?', help='Name of initial state')
    parser.add_argument('--entry', '-e', type=str, help='Name of agent entry point')
    parser.add_argument('--args', '-A', type=str, nargs='+', help='Extra agent entry arguments')
    parser.add_argument('--wallclock-limit', '-W', type=float, default=None, help='Maximum time to run in seconds')
    parser.add_argument('--timestep-limit', '-T', type=int, default=None, help='Maximum time to run in timesteps')
    parser.add_argument('--no-nv', '-N', action='store_true', help='Disable Nvidia runtime')
    parser.add_argument('--results-dir', '-r', type=str, help='Path to output results')

    args = parser.parse_args(argv)
    kwargs = {
        'entry_args': args.args,
        'wallclock_limit': args.wallclock_limit,
        'timestep_limit': args.timestep_limit,
    }

    if args.no_nv:
        kwargs['runtime'] = None

    if args.results_dir:
        kwargs['resultsdir'] = args.results_dir

    run(args.game, args.state, args.entry, **kwargs)


if __name__ == '__main__':
    main()
