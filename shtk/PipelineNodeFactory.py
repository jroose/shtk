import abc
import asyncio
import contextlib

from .PipelineNode import *
from .StreamFactory import *
from .util import export

__all__ = []

@export
class PipelineNodeFactory(abc.ABC):
    def __init__(self, stdin=None, stdout=None, stderr=None):
        self._stdin = stdin
        self._stdout = stdout
        self._stderr = stderr
        self.children = []

    def stdin(self, arg, mode='r'):
        acceptable_modes = ('r', 'rb')
        if mode not in acceptable_modes:
            raise ValueError(f"Argument `mode` must be one of {acceptable_modes}")

        if isinstance(arg, StreamFactory):
            self._stdin = arg
        elif isinstance(arg, str):
            self._stdin = FileStreamFactory(arg, mode)
        elif arg is None:
            self._stdout = NullStreamFactory(mode)
        else:
            raise TypeError("Argument `arg` must be instance of StreamFactory or str")

        return self

    def stdout(self, arg, mode='w'):
        acceptable_modes = ('w', 'a', 'wb', 'ab')
        if mode not in acceptable_modes:
            raise ValueError(f"Argument `mode` must be one of {acceptable_modes}")

        if isinstance(arg, StreamFactory):
            self._stdout = arg
        elif isinstance(arg, str):
            self._stdout = FileStreamFactory(arg, mode)
        elif arg is None:
            self._stdout = NullStreamFactory(mode)
        else:
            raise TypeError("Argument `arg` must be instance of StreamFactory or str")

        return self

    def stderr(self, arg, mode='w'):
        acceptable_modes = ('w', 'a', 'wb', 'ab')
        if mode not in acceptable_modes:
            raise ValueError(f"Argument `mode` must be one of {acceptable_modes}")

        if isinstance(arg, StreamFactory):
            self._stderr = arg
        elif isinstance(arg, str):
            self._stderr = FileStreamFactory(arg, mode)
        elif arg is None:
            self._stdout = NullStreamFactory(mode)
        else:
            raise TypeError("Argument `arg` must be instance of StreamFactory or str")

        return self

    def __or__(self, other):
        return PipelineChannelFactory(self, other)

    async def build(self, job, stdin_stream, stdout_stream, stderr_stream):
        need_to_close = []

        if self._stdin is not None:
            stdin_stream = self._stdin.build(job)
            need_to_close.append(stdin_stream)
        if self._stdout is not None:
            stdout_stream = self._stdout.build(job)
            need_to_close.append(stdout_stream)
        if self._stderr is not None:
            stderr_stream = self._stderr.build(job)
            need_to_close.append(stderr_stream)

        ret = await self.build_inner(job, stdin_stream, stdout_stream, stderr_stream)
        
        #for stream in need_to_close:
        #    stream.close()

        return ret

    @abc.abstractmethod
    async def build_inner(self, job, stdin_stream, stdout_stream, stderr_stream):
        pass

@export
class PipelineOrFactory(PipelineNodeFactory):
    def __init__(self, first_child, *other_children, **kwargs):
        super().__init__(**kwargs)

        self.children.append(first_child)
        self.children.extend(other_children)

        for it, child in enumerate(self.children):
            if not isinstance(child, PipelineNodeFactory):
                raise TypeError(f"Child `{child}` must be instance of PipelineNodeFactory")

    async def build_inner(self, job, stdin_stream, stdout_stream, stderr_stream):
        for child in self.children:
            ret = await child.build(
                job=job,
                stdin_stream=stdin_stream,
                stdout_stream=stdout_stream,
                stderr_stream=stderr_stream
            )
            if all(code == 0 for code in await ret.wait()):
                break
        return ret

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
                job,
                await left_task,
                await right_task
            )

@export
class PipelineProcessFactory(PipelineNodeFactory):
    def __init__(self, *args, env={}, inherit_env=True):
        super().__init__()
        self.args = args
        self.env = env
        self.inherit_env = inherit_env

    def __call__(self, *args, **kwargs):
        return PipelineProcessFactory(
            *self.args, *args,
            env=dict(self.env, **kwargs),
            inherit_env=self.inherit_env
        )

    async def build_inner(self, job, stdin_stream, stdout_stream, stderr_stream):
        if self.inherit_env:
            env = dict(job.shell.environment, **self.env)
        else:
            env = self.env

        return await PipelineProcess.create(
            job = job,
            args = self.args,
            env = env,
            stdin_stream = stdin_stream,
            stdout_stream = stdout_stream,
            stderr_stream = stderr_stream
        )
