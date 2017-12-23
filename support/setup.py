from setuptools import setup
import sys
import os
import shutil

VERSION_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'VERSION')

if not os.path.exists(os.path.join(os.path.dirname(__file__), '.git')):
    use_scm_version = False
    shutil.copy('VERSION', 'gym_remote/VERSION.txt')
else:
    def version_scheme(version):
        with open(VERSION_PATH) as v:
            version_file = v.read()
        if version.distance:
            version_file += '.dev%d' % version.distance
        return version_file

    def local_scheme(version):
        v = ''
        if version.distance:
            v = '+' + version.node
        return v
    use_scm_version = {'write_to': 'gym_remote/VERSION.txt',
                       'version_scheme': version_scheme,
                       'local_scheme': local_scheme}


setup(
    name='retro-challenge-support',
    version=open(VERSION_PATH, 'r').read(),
    license='MIT',
    install_requires=[
        'gym',
    ],
    extras_require={
        'retro': 'retro',
        'docker': 'docker',
        'rest': ['docker', 'pyyaml', 'requests'],
    },
    entry_points={
        'console_scripts': [
            'retro-challenge-remote=retro_challenge.remote:main [retro]',
            'retro-challenge-agent=retro_challenge.agent:main',
            'retro-challenge=retro_challenge.__main__:main'
        ]
    },
    packages=['gym_remote', 'retro_challenge'],
    setup_requires=['pytest-runner'],
    use_scm_version=use_scm_version,
    zip_safe=True
)
