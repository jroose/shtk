"""Declares the Job class used to run and track subprocess pipelines."""
import asyncio
import io
import os
import pathlib
import time

from .StreamFactory import *
from .PipelineNode import *
from .util import *

__all__ = []

@export
class NonzeroExitCodeException(Exception):
    """
    Raised when a process within an SHTK job exits with a nonzero return code.

    Args:
        processes: a list of the PipelineProcess instances to include in the
            error message

    """
    def __init__(self, processes):
        self.processes = processes
        message = io.StringIO()
        print("One or more of the following processes returned non-zero return code:", file=message)
        for proc in self.processes:
            rc = proc.proc.returncode
            args = []
            for arg in proc.args:
                arg = str(arg)
                if any(x in arg for x in " '\"\\"):
                    arg = repr(arg)
                    args.append(repr(arg))
                else:
                    args.append(arg)

            print(f"  [{rc:3}] {' '.join(args)}", file=message)

        self.message = message.getvalue()
        message.close()

        super().__init__(self.message)
        

@export
class Job:
    """
    Instantiates PipelienNodeFactory instances to run subprocesses.

    Job objects instantiate a PipelineNodeFactory template to create PipelineNodes
    that run and track the progress of a command pipeline.

    Args:
        pipeline_factory (PipelineNodeFactory): the command pipeline template
            that will be instantiated by the Job instance.
        cwd (str or Pathlib.Path): the current working directory in which to
            run the pipeline processes.
        env (dict): the environment variables to pass to processes run within
            the pipleine
        event_loop (None or asyncio.AbstractEventLoop): the event loop to use
            for asyncio based processing.  If None is passed a new event loop
            is created from asyncio.new_event_loop() instead.

    """
    def __init__(
        self,
        pipeline_factory,
        cwd = None,
        env = {},
        event_loop = None
    ):
        self.pipeline_factory = pipeline_factory
        self.pipeline = None
        self.environment = env

        if event_loop is None:
            self.event_loop = asyncio.new_event_loop()
        else:
            self.event_loop = event_loop

        if cwd is not None:
            self.cwd = cwd
        else:
            self.cwd = os.getcwd()

    @property
    def stdin(self):
        """
        Returns the pipeline's stdin_stream.writer(), or None

        Returns:
            Pipeline's stdin_stream.writer(), or None if no pipeline is
            running.
        """
        if self.pipeline is not None:
            return self.pipeline.stdin_stream.writer()
        else:
            return None

    @property
    def stdout(self):
        """
        Returns the pipeline's stdout_stream.reader(), or None

        Returns:
            Pipeline's stdout_stream.reader(), or None if no pipeline is
            running.
        """
        if self.pipeline is not None:
            return self.pipeline.stdout_stream.reader()
        else:
            return None

    @property
    def stderr(self):
        """
        Returns the pipeline's stderr_stream.reader(), or None

        Returns:
            Pipeline's stderr_stream.reader(), or None if no pipeline is
            running.
        """
        if self.pipeline is not None:
            return self.pipeline.stderr_stream.reader()
        else:
            return None

    def get_process_nodes(self, pipeline_node=None):
        """
        Gathers the PipelineProcess nodes instantiated for the pipeline.  

        Args:
            pipeline_node (PipelineNode): Should initially be None, used for recursion (Default
                value = None)

        Returns:
            The complete list of PipelineProcess objects in use by the
            pipeline.

        """
        if pipeline_node is None:
            pipeline_node = self.pipeline

        ret = []
        if isinstance(pipeline_node, PipelineProcess):
            ret.append(pipeline_node)
        else:
            for child in pipeline_node.children:
                ret.extend(self.get_process_nodes(child))

        return ret

    async def run_async(self, stdin_factory, stdout_factory, stderr_factory):
        """
        Creates and runs a new pipeline

        Instantiates and runs a pipeline based on the PipelineNodeFactory
        provided to the Job's constructor.

        Args:
            stdin_factory (StreamFactory): the StreamFactory to instantiate to
                create the job's default stdin stream.
            stdout_factory (StreamFactory): the StreamFactory to instantiate to
                create the job's default stdout stream.
            stderr_factory (StreamFactory): the StreamFactory to instantiate to
                create the job's default stderr stream.
        """

        stdin_stream=stdin_factory.build(self)
        stdout_stream=stdout_factory.build(self)
        stderr_stream=stderr_factory.build(self)

        self.pipeline = await self.pipeline_factory.build(
            self,
            stdin_stream=stdin_stream,
            stdout_stream=stdout_stream,
            stderr_stream=stderr_stream,
        )

        stdin_stream.close_reader()
        stdout_stream.close_writer()
        stderr_stream.close_writer()

    def run(self, stdin_factory, stdout_factory, stderr_factory):
        """
        Creates and runs a new pipeline

        Synchronously wrapper for run_async.

        Args:
            stdin_factory (StreamFactory): the StreamFactory to instantiate to
                create the job's default stdin stream.
            stdout_factory (StreamFactory): the StreamFactory to instantiate to
                create the job's default stdout stream.
            stderr_factory (StreamFactory): the StreamFactory to instantiate to
                create the job's default stderr stream.

        """
        return self.event_loop.run_until_complete(
            self.run_async(
                stdin_factory=stdin_factory,
                stdout_factory=stdout_factory,
                stderr_factory=stderr_factory
            )
        )

    async def wait_async(self, exceptions=True):
        """
        Waits for all processes in the pipeline to complete

        Waits for all processes in the pipleine to complete checks the return
        codes of each command.

        Args:
            exceptions (Boolean): When true returns an exception when processes
                exit with non-zero return codes

        Returns:
            A tuple of exit codes from the completed proceses

        Raises:
            NonzeroExitCodeException: When a process returns a non-zero return code
            
        """
        ret = await self.pipeline.wait()

        if exceptions:
            if any(rc != 0 for rc in ret):
                raise NonzeroExitCodeException(self.get_process_nodes())

        return tuple(ret)

    def wait(self, exceptions=True):
        """
        Synchronous wrapper for the wait_async() method.

        Waits for all processes in the pipleine to complete checks the return
        codes of each command.

        Args:
            exceptions (Boolean): When true returns an exception when processes
                exit with non-zero return codes

        Returns:
            A tuple of exit codes from the completed proceses

        Raises:
            NonzeroExitCodeException: When a process returns a non-zero return code

        """
        return self.event_loop.run_until_complete(
            self.wait_async(exceptions=exceptions)
        )

