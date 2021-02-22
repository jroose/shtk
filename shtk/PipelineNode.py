"""
PipelineNode instances are used to track and manage subprocesses run by shtk
Shells.
"""

import abc
import asyncio
import signal
import sys

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
    def __init__(self, event_loop):
        self.children = []
        self.stdin_stream = None
        self.stderr_stream = None
        self.stdout_stream = None
        self.event_loop = event_loop

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

#    @abc.abstractmethod
#    def poll(self):
#        """
#        Check if the child ProcessNodes have terminated.  Returns the exit code of
#        processes that have completed, returns None for processes that have not
#        completed.
#
#        Returns:
#            list of (int or None):
#                A list with one element per child process containing either an
#                integer exit code for completed processes or None for
#                incomplete processes.  
#        """

    @staticmethod
    async def _get_return_code(rc_list, idx, coro):
        rc_list[idx] = await coro

    def _flatten_children(self):
        ret = []
        if len(self.children) > 0:
            for child in self.children:
                ret.extend(child._flatten_children())
        else:
            ret.append(self)

        return ret

    def send_signal(self, signal):
        for child in self._flatten_children():
            child.proc.send_signal(signal)

    def terminate(self):
        self.send_signal(signal.SIGTERM)

    def kill(self):
        self.send_signal(signal.SIGKILL)
      
    async def poll_async(self, ret):
        """
        Gets the return codes of all child ProcessNodes

        Args:
            ret (list of [int, None]): a list that will be modified to contain
                a collection of return codes from flattened child ProcessNodes.
                Child processes that have exited will be represented by their
                return code.  Child processes that have not exited will be
                represented by None.
        """

        ret.clear()

        tasks = []
        for it_child, child in enumerate(self._flatten_children()):
            ret.append(None)
            coro = self._get_return_code(ret, it_child, child.proc.wait())
            task = self.event_loop.create_task(coro)
            tasks.append(task)

        try:
            for task in tasks:
                await task
        except asyncio.CancelledError:
            for task in tasks:
                try:
                    if not task.done():
                        task.cancel()
                        await task
                except asyncio.CancelledError:
                    pass
        else:
            return ret

    def poll(self, timeout=1e-6):
        """
        Synchronous wrapper for poll_async().  Gets the return codes of all
        child ProcessNodes.

        Returns:
            list of (int or None): A list containing return codes from
                flattened child ProcessNodes.  Child processes that have exited
                will be represented by their integer return code.  Child
                processes that have not exited will be represented by None.
        """

        ret = []

        try:
            self.event_loop.run_until_complete(
                asyncio.wait_for(
                    self.poll_async(ret),
                    timeout=timeout,
                    loop=self.event_loop
                )
            )
        except asyncio.TimeoutError:
            pass
            
        return ret
      
    async def wait_async(self):
        """
        Waits for and retrieves the return codes of all child ProcessNodes.

        Returns:
            list of int:
                A list of return codes from a flattened collection of child
                processes.
        """

        return await self.poll_async([])
      
    def wait(self):
        """
        Synchronous wrapper for wait_async().

        Returns:
            list of int:
                A list of return codes from a flattened collection of child
                processes.
        """
        return self.event_loop.run_until_complete(self.wait_async())

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
    def __init__(self, event_loop, left, right):
        super().__init__(event_loop)

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

#    def poll(self):
#        """
#        Check if the child ProcessNodes have terminated.  Returns the exit code of
#        processes that have completed, returns None for processes that have not
#        completed.
#
#        Returns:
#            list of (int or None):
#                A list with one element per child process containing either an
#                integer exit code for completed processes or None for
#                incomplete processes.  
#        """
#
#        ret = []
#        ret.extend(self.left.poll())
#        ret.extend(self.right.poll())
#
#        return ret
#
#    async def wait_async(self):
#        """
#        Waits for left and right PipelineNodes to complete
#
#        Returns:
#            list of int:
#                Combined list of return codes from left (first) and right
#                (later) PipelineNode children.
#        """
#        ret = []
#        ret.extend(await self.left.wait_async())
#        ret.extend(await self.right.wait_async())
#        return ret
#
#    def wait(self):
#        ret = []
#        ret.extend(self.left.wait())
#        ret.extend(self.right.wait())
#        return ret

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
        user (None, int, or str): The user to pass to
            asyncio.create_subprocess_exec().  Requires Python >= 3.9.
        group (None, int, or str): The group to pass to
            asyncio.create_subprocess_exec().  Requires Python >= 3.9.

    Raises:
        AssertionError: When len(args) <= 0
    """
    def __init__(self, event_loop, cwd, args, env, stdin_stream, stdout_stream, stderr_stream, user=None, group=None):
        super().__init__(event_loop)

        self.cwd = cwd
        self.args = args
        self.environment = dict(env)
        self.proc = None
        self.wait_future = None
        self.user = user
        self.group = group

        self.stdin_stream = stdin_stream
        self.stdout_stream = stdout_stream
        self.stderr_stream = stderr_stream

        assert len(self.args) > 0

    async def run(self):
        """
        Runs the process using asyncio.create_subprocess_exec()
        """
        
        extra_kwargs = {}
        if self.user is not None:
            extra_kwargs['user'] = self.user
            if (sys.version_info.major, sys.version_info.minor) < (3, 9):
                raise NotImplementedError("Running subprocesses as a different user requires Python version >= 3.9")

        if self.group is not None:
            extra_kwargs['group'] = self.group
            if (sys.version_info.major, sys.version_info.minor) < (3, 9):
                raise NotImplementedError("Running subprocesses as a different group requires Python version >= 3.9")

        proc_start = asyncio.create_subprocess_exec(
            *self.args,
            stdin = self.stdin_stream.reader(),
            stdout = self.stdout_stream.writer(),
            stderr = self.stderr_stream.writer(),
            cwd = self.cwd,
            env = self.environment,
            restore_signals = True,
            close_fds = True,
            loop = self.event_loop,
            **extra_kwargs
        )
        
        self.proc = await proc_start

#        self.wait_future = self.event_loop.create_task(self.proc.wait())

#    def poll(self, timeout=1e-6):
#        """
#        Check if the child ProcessNodes have terminated.  Returns the exit code
#        of processes that have completed, returns None for processes that have
#        not completed.  If the timeout expires before the return code is
#        available then [None] is returned.
#
#        Args:
#            timeout (float): number of seconds to wait
#
#        Raises:
#            RuntimeError: when called before self.run()
#
#        Returns:
#            list of (int or None):
#                A list with one element per child process containing either an
#                integer exit code for completed processes or None for
#                incomplete processes.  
#        """
#        if self.proc is None:
#            raise RuntimeError("Cannot poll a process that has not run yet.")
#        else:
#            if self.wait_future.done():
#                return [self.wait_future.result()]
#            else:
#                try:
#                    shielded_future = asyncio.shield(
#                        self.wait_future,
#                        loop=self.event_loop
#                    )
#                    quick_wait = asyncio.wait_for(shielded_future, timeout=timeout, loop=self.event_loop)
#                    return [self.event_loop.run_until_complete(quick_wait)]
#                except asyncio.TimeoutError:
#                    return [None]
#
#    def wait(self, timeout=None):
#        """
#        Blocks until the subprocess is completed and returns its returncode
#        within a one-element list.  If timeout expires before the return code
#        is available code, then [None] is returned.  
#
#        Args:
#            timeout (float): number of seconds to wait
#
#        Raises:
#            RuntimeError: when called before self.run()
#
#        Returns:
#            list of (int or None):
#                A list of one integer
#        """
#
#        return self.poll(timeout=timeout)
#
#    async def wait_async(self):
#        """
#        Blocks until the subprocess is completed and returns its returncode
#        within a one-element list.
#
#        Raises:
#            RuntimeError: when called before self.run()
#
#        Returns:
#            list of int:
#                A list of one integer
#        """
#        if self.proc is None:
#            raise RuntimeError("Cannot wait on a process that has not run yet.")
#        else:
#            return [await self.wait_future]

    def __repr__(self):
        return f"PipelineProcess(cwd={self.cwd!r}, args={self.args!r}, env={self.environment!r}, stdin_stream={self.stdin_stream!r}, stdout_stream={self.stdout_stream!r}, stderr_stream={self.stderr_stream!r})" #pylint: disable=line-too-long

    def __str__(self):
        return f"PipelineProcess(args={self.args!r})"
