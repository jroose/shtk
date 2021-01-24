import abc
import asyncio
import contextlib
import pathlib

from .PipelineNode import *
from .StreamFactory import *
from .util import export

__all__ = []

@export
class PipelineNodeFactory(abc.ABC):
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
            raise TypeError(f"Argument `arg` must be instance of StreamFactory or str, not {type(arg)}")

    def stdin(self, arg, mode='r'):
        acceptable_modes = ('r', 'rb')
        if mode not in acceptable_modes:
            raise ValueError(f"Argument `mode` must be one of {acceptable_modes}")

        self.stdin_factory = self._create_stream_factory(arg, mode)

        return self

    def stdout(self, arg, mode='w'):
        acceptable_modes = ('w', 'a', 'wb', 'ab')
        if mode not in acceptable_modes:
            raise ValueError(f"Argument `mode` must be one of {acceptable_modes}")

        self.stdout_factory = self._create_stream_factory(arg, mode)

        return self

    def stderr(self, arg, mode='w'):
        acceptable_modes = ('w', 'a', 'wb', 'ab')
        if mode not in acceptable_modes:
            raise ValueError(f"Argument `mode` must be one of {acceptable_modes}")

        self.stderr_factory = self._create_stream_factory(arg, mode)

        return self

    def __or__(self, other):
        return PipelineChannelFactory(self, other)

    async def build(self, job, stdin_stream=None, stdout_stream=None, stderr_stream=None):
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
        pass

@export
class PipelineChannelFactory(PipelineNodeFactory):
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
                left = await left_task,
                right = await right_task
            )

@export
class PipelineProcessFactory(PipelineNodeFactory):
    def __init__(self, *args, env={}, cwd=None):
        super().__init__()
        self.args = args
        self.env = env
        self.cwd = cwd

    def __call__(self, *args, **kwargs):
        return PipelineProcessFactory(
            *self.args, *args,
            env=dict(self.env, **kwargs),
            cwd=self.cwd
        )

    async def build_inner(self, job, stdin_stream, stdout_stream, stderr_stream):
        if job is not None:
            env = dict(job.environment, **self.env)
        else:
            env = self.env

        cwd = self.cwd or job.cwd
        
        return await PipelineProcess.create(
            cwd = cwd,
            env = env,
            args = self.args,
            stdin_stream = stdin_stream,
            stdout_stream = stdout_stream,
            stderr_stream = stderr_stream
        )
