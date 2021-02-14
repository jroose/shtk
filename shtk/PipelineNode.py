"""
PipelineNode instances are used to track and manage subprocesses run by shtk
Shells.
"""

import abc
import asyncio

from .util import export

__all__ = []

@export
class PipelineNode(abc.ABC):
    """
    Abstract base class for subprocess management nodes

    Attributes:
        children (list of PipelineNode): children of this node
        stdin_stream (None or Stream): Stream to use for stdin
        stdout_stream (None or Stream): Stream to use for stdout
        stderr_stream (None or Stream): Stream to use for stderr
    """
    def __init__(self):
        self.children = []
        self.stdin_stream = None
        self.stderr_stream = None
        self.stdout_stream = None

    @classmethod
    async def create(cls, *args, **kwargs):
        """
        Instantiates and runs the node

        Args:
            *args: passed to the constructor
            **kwargs: passed to the constructor

        Returns:
            PipelineNode:
                The instantiated and run node.
        """
        instance = cls(*args, **kwargs)
        await instance.run()
        return instance

    async def run(self):
        """
        Runs the process
        """

    @abc.abstractmethod
    def poll(self):
        """
        Check if the child processes have terminated.  Returns the exit code of
        processes that have completed, returns None for processes that have not
        completed.

        Returns:
            list of (int or None):
                A list with one element per child process containing either an
                integer exit code for completed processes or None for
                incomplete processes.  
        """
      
    @abc.abstractmethod
    async def wait_async(self):
        """
        Waits for left and right PipelineNodes to complete

        Returns:
            list of int:
                Combined list of return codes from left (first) and right
                (later) PipelineNode children.
        """
#      
#    def wait(self):
#        """
#        Synchronous wrapper for wait_async()
#
#        Returns:
#            list of int:
#                Combined list of return codes from left (first) and right
#                (later) PipelineNode children.
#        """
#        task = self.wait_async()
#        return task.get_loop().run_until_complete(task)

    @abc.abstractmethod
    def __repr__(self):
        pass

    @abc.abstractmethod
    def __str__(self):
        pass

@export
class PipelineChannel(PipelineNode):
    """
    Represents a pipeline of commands

    Args:
        left (PipelineNode): A PipelineNode whose stdout is (usually) fed to
            right
        right (PipelineNode): A PipelineNode whose stdin is (usually)
            read from left

    Attributes:
        left (PipelineNode): The left PipelineNode
        right (PipelineNode): The right PipelineNode
    """
    def __init__(self, left, right):
        super().__init__()

        self.left = left
        self.right = right

        self.stdin_stream = self.left.stdin_stream
        self.stdout_stream = self.right.stdout_stream
        self.stderr_stream = self.right.stderr_stream

        self.children.extend((self.left, self.right))

    def __repr__(self):
        return f"{self.left!r} | {self.right!r}"

    def __str__(self):
        return f"{self.left!s} | {self.right!s}"

    def poll(self):
        """
        Check if the child processes have terminated.  Returns the exit code of
        processes that have completed, returns None for processes that have not
        completed.

        Returns:
            list of (int or None):
                A list with one element per child process containing either an
                integer exit code for completed processes or None for
                incomplete processes.  
        """

        ret = []
        ret.extend(self.left.poll())
        ret.extend(self.right.poll())

        return ret

    async def wait_async(self):
        """
        Waits for left and right PipelineNodes to complete

        Returns:
            list of int:
                Combined list of return codes from left (first) and right
                (later) PipelineNode children.
        """
        ret = []
        ret.extend(await self.left.wait_async())
        ret.extend(await self.right.wait_async())
        return ret

    def wait(self):
        ret = []
        ret.extend(self.left.wait())
        ret.extend(self.right.wait())
        return ret

@export
class PipelineProcess(PipelineNode):
    """
    An interface representing subprocesses.

    Args:
        cwd (str or pathlib.Path): The current working directory
        args (list of str or pathlib.Path): The arguments for the process
            (including the base command).
        env (dict of str): The environment variables for the process
        stdin_stream (Stream): The Stream whose .reader() is used as stdin
        stdout_stream (Stream): The Stream whose .writer() is used as stdout
        stderr_stream (Stream): The Stream whose .writer() is used as stderr

    Raises:
        AssertionError: When len(args) <= 0
    """
    def __init__(self, cwd, args, env, stdin_stream, stdout_stream, stderr_stream):
        super().__init__()

        self.cwd = cwd
        self.args = args
        self.environment = dict(env)
        self.proc = None

        self.stdin_stream = stdin_stream
        self.stdout_stream = stdout_stream
        self.stderr_stream = stderr_stream

        assert len(self.args) > 0

    async def run(self):
        """
        Runs the process using asyncio.create_subprocess_exec()
        """
        self.proc = await asyncio.create_subprocess_exec(
            *self.args,
            stdin = self.stdin_stream.reader(),
            stdout = self.stdout_stream.writer(),
            stderr = self.stderr_stream.writer(),
            cwd = self.cwd,
            env = self.environment,
            restore_signals = True,
            close_fds = True
        )

    def poll(self):
        """
        Check if the child processes have terminated.  Returns the exit code of
        processes that have completed, returns None for processes that have not
        completed.

        Raises:
            RuntimeError: when called before self.run()

        Returns:
            list of (int or None):
                A list with one element per child process containing either an
                integer exit code for completed processes or None for
                incomplete processes.  
        """
        if self.proc is None:
            raise RuntimeError("Cannot poll a process that has not run yet.")
        else:
            return [self.proc.poll()]

    def __repr__(self):
        return f"PipelineProcess(cwd={self.cwd!r}, args={self.args!r}, env={self.environment!r}, stdin_stream={self.stdin_stream!r}, stdout_stream={self.stdout_stream!r}, stderr_stream={self.stderr_stream!r})" #pylint: disable=line-too-long

    def __str__(self):
        return f"PipelineProcess(args={self.args!r})"

    async def wait_async(self):
        """
        Blocks until the subprocess is completed and returns its returncode
        within a one-element list.

        Raises:
            RuntimeError: when called before self.run()

        Returns:
            list of int:
                A list of one integer
        """
        if self.proc is None:
            raise RuntimeError("Cannot wait on a process that has not run yet.")
        else:
            return [await self.proc.wait()]
