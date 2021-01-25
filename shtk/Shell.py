"""
Shells are the primary way of interacting with shtk.  You can use them to
define and run a series of commands called a Pipeline as subprocesses of the
Python script.
"""

import asyncio
import atexit
import collections
import contextlib
import os
import os.path
import pathlib
import subprocess
import sys
import threading

from .Job import *
from .util import export, which
from .PipelineNodeFactory import *
from .StreamFactory import *

__all__ = ["default_shell"]

@export
class Shell:
    """
    A shell object tracks pre-requisite information (e.g. cwd and environment
    variables) necessary to run commands as subprocesses.  A shell is also a
    context manager that exposes environment variables and other info to
    subshells and subprocesses, while also setting itself as the default shell
    within managed code.

    Args:
        cwd (str, pathlib.Path): Current working directory for subprocesses.
        inherit_env (boolean): Whether to inherit environment variables from
            the parent shell.
        umask (int): Controls the default umask for subprocesses
        stdin (file-like): Default stdin stream for subprocesses (defaults to
            sys.stdin)
        stdout (file-like): Default stdout stream for subprocesses (defaults to
            sys.stdout)
        stderr (file-like): Default stderr stream for subprocesses (defaults to
            sys.stderr)
        exceptions (boolean): Whether exceptions should be raised when non-zero
            exit codes are returned by subprocesses.
    """
    _thread_vars = collections.defaultdict(dict)
    
    def __init__(self, cwd=None, inherit_env=True, umask=None, stdin=None, stdout=None, stderr=None, exceptions=True):
        self.lock = threading.RLock()
        self.exceptions = exceptions
        self.event_loop = None

        with self.lock:
            if inherit_env:
                self.environment = {k:v for k,v in os.environ.items()}
            else:
                self.environment = {}

            if cwd is None:
                cwd = os.getcwd()
            self.cwd = pathlib.Path(cwd)
            self.pwd = None

            if umask is None:
                umask = int(subprocess.check_output(['grep', 'Umask', f"/proc/{os.getpid()}/status"]).split()[-1], 8)
            self.umask = umask
            
            if stdin is None:
                stdin = sys.stdin
            self.stdin = stdin
            
            if stdout is None:
                stdout = sys.stdout
            self.stdout = stdout

            if stderr is None:
                stderr = sys.stderr
            self.stderr = stderr

    def command(self, name, user=None):
        """
        Creates a PipelineProcessFactory suitable for executing a command

        Args:
            name (str or pathlib.Path): Name or path of the command to run.  If
                an absolute or relative path is provided (must contain a '/'
                character) then the command will be loaded from the specified
                location.  Otherwise the locations specified by the $PATH
                environment variable will be checked for suitable executable
                and readable files with the appropriate name.

                If name is an str, then the name will be passed through
                os.path.expanduser prior to lookup.

            user: User to sudo to prior to execution (Default value = None)

        Returns:
            PipelineProcessFactory:
                A PipelineProcessFactory node representing the command to be
                executed.

        Raises:
            RuntimeError: command cannot be found
            RuntimeError: command filepath is not readable
            RuntimeError: command filepath is not executable
        """

        if isinstance(name, str):
            name = os.path.expanduser(name)

        if isinstance(name, pathlib.Path) or '/' in name:
            path = pathlib.Path(name)
            if path.is_absolute():
                command_path = path.resolve()
            else:
                command_path = (self.cwd / path).resolve()
        else:
            command_path = which(name)

        if command_path is None or not command_path.is_file():
            raise RuntimeError(f"{name}: command not found")

        if not os.access(command_path, os.R_OK):
            raise RuntimeError(f"{command_path}: is not readable")

        if not os.access(command_path, os.X_OK):
            raise RuntimeError(f"{command_path}: is not executable")
                
        if user is None:
            return PipelineProcessFactory(command_path)
        else:
            return PipelineProcessFactory('sudo', '-u', user, command_path)

    def cd(self, path):
        """
        Changes the default current working directory for subprocesses built by the Shell

        Args:
            path (str or pathlib.Path): Changes directory to provided path such
                that managed subprocesses will use this directory as their
                default current working directory.  If '-' is provided, returns
                to previous working directory.

        Raises:
            RuntimeError: raised if path is not a directory
        """
        with self.lock:
            if path == '-':
                path = self.pwd

            path = pathlib.Path(path)
            if not path.is_absolute():
                new_cwd = (self.cwd / path).resolve()
            else:
                new_cwd = path.resolve()

            if not new_cwd.is_dir():
                raise RuntimeError(f"{new_cwd!s} is not a directory")

            self.pwd = self.cwd
            self.cwd = new_cwd

    @contextlib.contextmanager
    def cd_manager(self, new_wd):
        """
        Contextmanager for Shell.cd() returns to previous dir after exit

        Args:
            new_wd (str or pathlib.Path): directory to change to

        Yields:
            pathlib.Path: The new self.cwd
        """
        old_wd = self.cwd
        self.cd(new_wd)
        yield self.cwd
        self.cd(old_wd)

    def export(self, **env):
        """
        Sets environment variables passed as keyword arguments

        Args:
            **env (dict): List of key-value pairs that will set as environment
                variables for the Shell()
        """
        with self.lock:
            for key, value in env.items():
                self.environment[key] = value

    def getenv(self, name):
        """
        Gets the value of an environment variable within the Shell

        Args:
            name (str): Name of the environment variable to evaluate

        Returns:
            str: The value of the named environment variable

        """
        return self.environment[name]

    @classmethod
    def _get_thread_vars(cls):
        thread_id = threading.get_ident()
        return cls._thread_vars[thread_id]

    @classmethod
    def get_shell(cls):
        """
        Gets the current active shell from the shell stack

        Returns:
            Shell: The most recently entered shell context
        """
        tvars = cls._get_thread_vars()
        if len(tvars['shell_stack']) == 0:
            raise RuntimeError("No currently active shell")
        return tvars['shell_stack'][-1]

    def __enter__(self):
        tvars = self._get_thread_vars()
        tvars.setdefault('shell_stack', [])
        tvars['shell_stack'].append(self)

        if self.event_loop is not None:
            raise RuntimeError(f"{self.__class__} is not re-entrant.")

        self.event_loop = asyncio.new_event_loop()

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.event_loop.run_until_complete(
            self.event_loop.shutdown_asyncgens()
        )
        self.event_loop.close()
        self.event_loop = None

        tvars = self._get_thread_vars()
        tvars['shell_stack'].pop()

    def __call__(self, *pipeline_factories, exceptions=None, wait=True):
        """
        Executes a series of PipelineNodeFactory nodes as subprocesses

        Args:
            *pipeline_factories: The PipelineNodeFactory nodes to execute
            exceptions: Whether or not to raise exceptions for non-zero return
                codes (Default value = None)
            wait: Whether the call should block waiting for the subprocesses to
                exit (Default value = True)

        Returns:
            list of int: The return codes of the subprocesses after exiting
        """
        return self.run(*pipeline_factories, exceptions=exceptions, wait=wait)

    def run(self, *pipeline_factories, exceptions=None, wait=True):
        """
        Executes a series of PipelineNodeFactory nodes as subprocesses

        Args:
            *pipeline_factories: The PipelineNodeFactory nodes to execute
            exceptions: Whether or not to raise exceptions for non-zero exit
                codes (Default value = None)
            wait: Whether the call should block waiting for the subprocesses to
                exit (Default value = True)

        Returns:
            list of Job: 
                Job instances representing individual pipelines.  The length of
                the list will always be equal to the len(pipeline_factories)
        """
        async def run_and_wait(*jobs, exceptions=None, wait=True):
            run_tasks = []
            for job in jobs:
                run_tasks.append(
                    self.event_loop.create_task(
                        job.run_async(
                            stdin_factory=ManualStreamFactory(fileobj_r=self.stdin),
                            stdout_factory=ManualStreamFactory(fileobj_w=self.stdout),
                            stderr_factory=ManualStreamFactory(fileobj_w=self.stderr)
                        )
                    )
                )

            for run_task in run_tasks:
                await run_task

            if wait:
                for job in jobs:
                    await job.wait_async(exceptions=exceptions)

        if exceptions is None:
            exceptions = self.exceptions

        ret = []
        for pipeline_factory in pipeline_factories:
            job = Job(pipeline_factory, env=self.environment, cwd=self.cwd, event_loop=self.event_loop)
            self.event_loop.run_until_complete(
                run_and_wait(job, exceptions=exceptions, wait=wait)
            )
            ret.append(job)

        return ret

    def evaluate(self, pipeline_factory, exceptions=None):
        """
        Executes a PipelineNodeFactory and returns the stdout text

        Args:
            pipeline_factory (PipelineNodeFactory): the pipeline to instantiate
                and execute
            exceptions: Whether or not to raise exceptions when subprocesses
                return non-zero return codes (Default value = None)

        Returns:
            str or bytes: 
                A string generated by the text that the final subprocess writes
                to stdout
        """
        if exceptions is None:
            exceptions = self.exceptions

        job = Job(
            pipeline_factory.stdout(PipeStreamFactory()),
            env=self.environment,
            cwd=self.cwd,
            event_loop=self.event_loop
        )

        job.run(
            stdin_factory=ManualStreamFactory(fileobj_r=self.stdin),
            stdout_factory=ManualStreamFactory(fileobj_w=self.stdout),
            stderr_factory=ManualStreamFactory(fileobj_w=self.stderr)
        )
        ret = job.stdout.read()
        job.wait(exceptions=exceptions)

        return ret

default_shell = Shell()
default_shell.__enter__()
atexit.register(default_shell.__exit__, None, None, None)
