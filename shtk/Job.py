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
    def __init__(self, processes):
        self.processes = processes
        message = io.StringIO()
        print("One or more of the following commands had non-zero exit code:", file=message)
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
        if self.pipeline is not None:
            return self.pipeline.stdin_stream.writer()
        else:
            return None

    @property
    def stdout(self):
        if self.pipeline is not None:
            return self.pipeline.stdout_stream.reader()
        else:
            return None

    @property
    def stderr(self):
        if self.pipeline is not None:
            return self.pipeline.stderr_stream.reader()
        else:
            return None

    def get_process_nodes(self, pipeline_node=None):
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
        return self.event_loop.run_until_complete(
            self.run_async(
                stdin_factory=stdin_factory,
                stdout_factory=stdout_factory,
                stderr_factory=stderr_factory
            )
        )

    async def wait_async(self, exceptions=True):
        ret = await self.pipeline.wait()

        if exceptions:
            if any(rc != 0 for rc in ret):
                raise NonzeroExitCodeException(self.get_process_nodes())

        return ret

    def wait(self, exceptions=True):
        return self.event_loop.run_until_complete(
            self.wait_async(exceptions=exceptions)
        )

