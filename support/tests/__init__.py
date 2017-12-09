import multiprocessing
import pytest
import tempfile
from gym_remote.client import RemoteEnv
from gym_remote.server import RemoteEnvWrapper


@pytest.fixture(scope='function')
def tempdir():
    with tempfile.TemporaryDirectory() as dir:
        yield dir


@pytest.fixture(scope='function')
def process_wrapper():
    with tempfile.TemporaryDirectory() as dir:
        def serve(pipe):
            make_env = pipe.recv()
            env = RemoteEnvWrapper(make_env(), dir)
            pipe.send('ok')

            args = pipe.recv()
            kwargs = pipe.recv()
            env.serve(*args, **kwargs)

        parent_pipe, child_pipe = multiprocessing.Pipe()
        proc = multiprocessing.Process(target=serve, args=(child_pipe,))
        proc.start()

        def call(env, *args, **kwargs):
            parent_pipe.send(env)
            assert parent_pipe.recv() == 'ok'
            parent_pipe.send(args)
            parent_pipe.send(kwargs)
            return RemoteEnv(dir)

        yield call
        proc.terminate()
