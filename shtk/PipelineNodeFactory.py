"""
PipelineNodeFactory instances are templates used to instantiate associated
PipelineNode classes.  They allow a pipeline configuration to be run
independently multiple times.
"""

import abc
import asyncio
import contextlib
import pathlib

from .PipelineNode import * #pylint: disable=unused-wildcard-import
from .StreamFactory import StreamFactory, FileStreamFactory, NullStreamFactory, PipeStreamFactory
from .util import export

__all__ = []

@export
class PipelineNodeFactory(abc.ABC):
    """
    Abstract base class defining a template for building PipelineNode's

    Args:
        stdin_factory (None or StreamFactory): Template for stdin Stream's
            (Default value: None)
        stdout_factory (None or StreamFactory): Template for stdout Stream's
            (Default value: None)
        stderr_factory (None or StreamFactory): Template for stderr Stream's
            (Default value: None)

    Attributes:
        stdin_factory (None or StreamFactory): Template for stdin Stream's
            (Default value: None)
        stdout_factory (None or StreamFactory): Template for stdout Stream's
            (Default value: None)
        stderr_factory (None or StreamFactory): Template for stderr Stream's
            (Default value: None)
        children (list of PipelineNodeFactory): templates for children
    """
    def __init__(self, stdin_factory=None, stdout_factory=None, stderr_factory=None):
        self.stdin_factory = stdin_factory
        self.stdout_factory = stdout_factory
        self.stderr_factory = stderr_factory
        self.children = []

    @staticmethod
    def _create_stream_factory(arg, mode):
        if isinstance(arg, StreamFactory):
            return arg
        elif isinstance(arg, str):
            return FileStreamFactory(arg, mode)
        elif isinstance(arg, pathlib.Path):
            return FileStreamFactory(arg, mode)
        elif arg is None:
            return NullStreamFactory()
        else:
            raise TypeError(
                f"Argument `arg` must be instance of StreamFactory or str, not {type(arg)}"
            )

    def stdin(self, arg, mode='r'):
        """
        Sets the stdin stream factory (in-place)

        Args:
          arg (str, pathlib.Path, StreamFactory, or None): If arg is an str or
              pathlib.Path, it is treated as a filename and stdin will be read
              from that file.

              If arg is a StreamFactory it is used directly to create streams
              for stdin.

              If None, stdin reads from os.devnull
          mode: The mode in which to open the file, if opened.  Only relevant
              if arg is a str or pathlib.Path.  Must be one of ('r', 'rb').
              (Default value = 'r')

        Returns:
            PipelineNodeFactory:
                Altered self

        """
        acceptable_modes = ('r', 'rb')
        if mode not in acceptable_modes:
            raise ValueError(f"Argument `mode` must be one of {acceptable_modes}")

        self.stdin_factory = self._create_stream_factory(arg, mode)

        return self

    def stdout(self, arg, mode='w'):
        """
        Sets the stdout stream factory (in-place)

        Args:
          arg (str, pathlib.Path, StreamFactory, or None): If arg is an str or
              pathlib.Path, it is treated as a filename and stdout will write
              to that file.

              If arg is a StreamFactory it is used directly to create streams
              for stdout.

              If None, stdout writes to os.devnull
          mode: The mode in which to open the file, if opened.  Only relevant
              if arg is a str or pathlib.Path.  Must be one of ('w', 'wb', 'a',
              'ab').  (Default value = 'w')

        Returns:
            PipelineNodeFactory:
                Altered self
        """
        acceptable_modes = ('w', 'a', 'wb', 'ab')
        if mode not in acceptable_modes:
            raise ValueError(f"Argument `mode` must be one of {acceptable_modes}")

        self.stdout_factory = self._create_stream_factory(arg, mode)

        return self

    def stderr(self, arg, mode='w'):
        """
        Sets the stderr stream factory (in-place)

        Args:
          arg (str, pathlib.Path, StreamFactory, or None): If arg is an str or
              pathlib.Path, it is treated as a filename and stderr will write
              to that file.

              If arg is a StreamFactory it is used directly to create streams
              for stderr.

              If None, stderr writes to os.devnull
          mode: The mode in which to open the file, if opened.  Only relevant
              if arg is a str or pathlib.Path.  Must be one of ('w', 'wb', 'a',
              'ab').  (Default value = 'w')

        Returns:
            PipelineNodeFactory:
                Altered self
        """
        acceptable_modes = ('w', 'a', 'wb', 'ab')
        if mode not in acceptable_modes:
            raise ValueError(f"Argument `mode` must be one of {acceptable_modes}")

        self.stderr_factory = self._create_stream_factory(arg, mode)

        return self

    def __or__(self, other):
        """
        Shorthand to create a PipelineChannelFactory(self, other)

        Args:
            other (PipelineNodeFactory): the child process to pipe stdout to

        Returns:
            PipelineChannelFactory:
                The constructed PipelineChannelFactory instance
        """
        return PipelineChannelFactory(self, other)

    async def build(self, job, stdin_stream=None, stdout_stream=None, stderr_stream=None):
        """
        Creates and executes PipelineNode's and self-defined StreamFactories

        If self.std{in,out,err}_factory is defined, it is pased to the child as
        the preferred stream.  Otherwise the std{in,out,err}_stream parameters
        are used.

        Args:
            job (Job): job from which to pull environment variables, current
                working directory, etc.
            stdin_stream (Stream): Stream instance to pass to PipelineNode as stdin
            stdout_stream (Stream): Stream instance to pass to PipelineNode as stdout
            stderr_stream (Stream): Stream instance to pass to PipelineNode as stderr

        Returns:
            PipelineNode:
                The constructed PipelineNode instance

        """

        need_to_close = []

        if self.stdin_factory is not None:
            stdin_stream = self.stdin_factory.build(job)
            need_to_close.append(stdin_stream.close_reader)
        elif stdin_stream is None:
            raise ValueError("stdin_stream must not be None when not overriden by stdin()")

        if self.stdout_factory is not None:
            stdout_stream = self.stdout_factory.build(job)
            need_to_close.append(stdout_stream.close_writer)
        elif stdout_stream is None:
            raise ValueError("stdout_stream must not be None when not overriden by stdout()")

        if self.stderr_factory is not None:
            stderr_stream = self.stderr_factory.build(job)
            need_to_close.append(stderr_stream.close_writer)
        elif stderr_stream is None:
            raise ValueError("stderr_stream must not be None when not overriden by stderr()")

        ret = await self.build_inner(job, stdin_stream, stdout_stream, stderr_stream)

        for closer in need_to_close:
            closer()

        return ret

    @abc.abstractmethod
    async def build_inner(self, job, stdin_stream, stdout_stream, stderr_stream):
        """
        Abstract method used for instantiating PipelineNodes.  This method
        is wrapped by build() which handles stream management prior to passing
        them to build_inner().

        Args:
            job (Job): The job from which to pull the current working directory
                and environment variables for subprocesses.
            stdin_stream (Stream): The Stream instance to be used as the
                PipelineNode's stdin_stream.
            stdout_stream (Stream): The Stream instance to be used as the
                PipelineNode's stdout_stream.
            stderr_stream (Stream): The Stream instance to be used as the
                PipelineNode's stderr_stream.

        Returns:
            PipelineNode:
                An instantiated PipelineNode.
        """

@export
class PipelineChannelFactory(PipelineNodeFactory):
    """
    PipelineChannelFactory is a template for creating PipelineChannel.

    PipelineChannelFactory creates PipelineChannel instances representing a
    chain of subprocesses with each feeding stdout to the next subprocess's
    stdin.

    Args:
        left (PipelineNodeFactory): A PipelineNodeFactory that will create a
            series of processes that should write to stdout.
        right (PipelineNodeFactory): A PipelineNodeFactory that will create a
            series of processes that should read from stdin.

    Attributes:
        left (PipelineNodeFactory): A PipelineNodeFactory that will create a
            series of processes that should write to stdout.
        right (PipelineNodeFactory): A PipelineNodeFactory that will create a
            series of processes that should read from stdin.
        children (list of PipelineNodeFactory): [left, right]
        pipe_stream (PipeStreamFactory): The PipeStreamFactory that will be
            used to redirect left's stdout to right's stdin.
    """
    def __init__(self, left, right, **kwargs):
        super().__init__(**kwargs)

        if not isinstance(left, PipelineNodeFactory):
            raise TypeError("Argument `left` must be instance of PipelineNodeFactory")

        if not isinstance(right, PipelineNodeFactory):
            raise TypeError("Argument `right` must be instance of PipelineNodeFactory")

        self.left = left
        self.right = right
        self.children = [left, right]
        self.pipe_stream = PipeStreamFactory()

    async def build_inner(self, job, stdin_stream, stdout_stream, stderr_stream):
        """Instantiates a PipelineChannel"""
        pipe_stream = self.pipe_stream.build(job)

        with contextlib.closing(self.pipe_stream.build(job)) as pipe_stream:
            left_task = asyncio.create_task(self.left.build(
                job=job,
                stdin_stream=stdin_stream,
                stdout_stream=pipe_stream,
                stderr_stream=stderr_stream
            ))

            right_task = asyncio.create_task(self.right.build(
                job,
                stdin_stream=pipe_stream,
                stdout_stream=stdout_stream,
                stderr_stream=stderr_stream
            ))

            return await PipelineChannel.create(
                job.event_loop,
                left=await left_task,
                right=await right_task
            )

@export
class PipelineProcessFactory(PipelineNodeFactory):
    """
    Template for a PipelineProcess which runs a command as a subprocess

    Args:
        *args (list of str or pathlib.Path): The command to run and its
            arguments for the instantiated PipelineProcess instances.
        environment (dict): The environment variables to use for the
            instantiated PipelineProcess instances (Default value = {}).
        cwd (str or pathlib.Path): The current working directory for the
            instantiated PipelineProcess instances (Default value = None).
    """
    def __init__(self, *args, env=None, cwd=None):
        super().__init__()
        self.args = args
        self.cwd = cwd

        if env is None:
            self.environment = {}
        else:
            self.environment = dict(env)

    def __call__(self, *args, **env):
        """
        Appends arguments and/or environment variables to a copy of self

        Args:
            *args: command arguments to append to the template
            **env: environment variables to add to the template

        Returns:
            PipelineProcessFactory:
                A copy of self with the extra args and envs
        """
        return PipelineProcessFactory(
            *self.args, *args,
            env=dict(self.environment, **env),
            cwd=self.cwd
        )

    async def build_inner(self, job, stdin_stream, stdout_stream, stderr_stream):
        """Instantiates a PipelineProcess"""
        if job is not None:
            env = dict(job.environment, **self.environment)
        else:
            env = self.environment

        cwd = self.cwd or job.cwd

        return await PipelineProcess.create(
            job.event_loop,
            cwd=cwd,
            env=env,
            args=self.args,
            stdin_stream=stdin_stream,
            stdout_stream=stdout_stream,
            stderr_stream=stderr_stream,
            user=job.user,
            group=job.group
        )
