import os
import setuptools


class CleanCommand(setuptools.Command):
    """
    Custom clean command to tidy up the project root, because even
        python setup.py clean --all
    doesn't remove build/dist and egg-info directories, which can and have caused
    install problems in the past.
    """
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        os.system('rm -vrf ./build ./dist ./*.pyc ./*.tgz ./*.egg-info')


with open('README.md', 'r') as f:
    long_description = f.read()


setuptools.setup(
    name='gryphon',
    packages=setuptools.find_packages(),
    version='0.11',
    author='MacLeod & Robinson, Inc.',
    author_email='hello@tinkercorp.com',
    description='A framework for running algorithmic trading strategies on cryptocurrency markets.',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='http://www.gryphonframework.org',
    classifiers=(
        'Programming Language :: Python :: 2.7',
        'Operating System :: OS Independent',
        'License :: Other/Proprietary License',
    ),
    entry_points={
        'console_scripts': [
            'gryphon-runtests=gryphon.tests.runtests:main',
            'gryphon-execute=gryphon.execution.app:main',
            'gryphon-cli=gryphon.execution.console:main',
            'gryphon-dashboards=gryphon.dashboards.app:main',
        ],
    },
    include_package_data=True,
    install_requires=[
        'alembic==0.6.0',
        'Babel==2.6.0',
        'backports.shutil-get-terminal-size==1.0.0',
        'cement==2.10.12',
        'certifi==2018.4.16',
        'chardet==3.0.4',
        'coinbase==1.0.4',
        'contextlib2==0.5.5',
        'Cython==0.20.1',
        'decorator==4.3.0',
        'Delorean>=1.0.0,<2',
        'enum34==1.1.6',
        'futures==3.2.0',
        'gryphon-cdecimal==2.3',
        'gryphon-money',  # Our fork of Python Money.
        'gryphon-pusherclient',  # Our duplicate of PythonPusherClient.
        'idna==2.7',
        'ipython==5.7.0',
        'ipython-genutils==0.2.0',
        'line-profiler==2.1.2',
        'Mako==1.0.7',
        'MarkupSafe==1.0',
        'mock==1.0.1',
        'more-itertools>=4.2.0,<5',
        'MySQL-python==1.2.5',
        'nose==1.3.7',
        'pathlib2==2.3.2',
        'pexpect==4.6.0',
        'pickleshare==0.7.4',
        'prompt-toolkit==1.0.15',
        'ptyprocess==0.6.0',
        'Pygments==2.2.0',
        'pylibmc>=1.5.2,<2',
        'python-dotenv==0.8.2',
        'pytz==2018.5',
        'raven==6.9.0',
        'rednose>=1.3.0,<2',
        'redis==2.10.6',
        'requests==2.19.1',
        'requests-futures==0.9.7',
        'requests-toolbelt==0.8.0',
        'retrying==1.3.3',
        'scandir==1.7',
        'simplegeneric==0.8.1',
        'six==1.11.0',
        'sure==1.2.9',
        'SQLAlchemy>=1.2.10,<1.3',
        'termcolor==1.1.0',
        'traitlets==4.3.2',
        'tzlocal==1.5.1',
        'urllib3==1.23',
        'wcwidth==0.1.7',
        'websocket-client==0.48.0',
    ],
    cmdclass={
        'clean': CleanCommand,
    },
)
