import asyncio
import io
import pathlib
import time

from .StreamFactory import *
from .PipelineNode import *
from .util import *

__all__ = []

@export
class ReturnCodeError(Exception):
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
        shell,
        pipeline_factory,
        stdin_factory = None,
        stdout_factory = None,
        stderr_factory = None
    ):
        self.shell = shell
        self.streams = []
        self.pipeline = None

        self.stdin_factory = stdin_factory or ShellStreamFactory('stdin')
        self.stdout_factory = stdout_factory or ShellStreamFactory('stdout')
        self.stderr_factory = stderr_factory or ShellStreamFactory('stderr')

        self.pipeline_factory = pipeline_factory

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

    async def run(self):
        self.stdin_stream = self.stdin_factory.build(self)
        self.stdout_stream = self.stdout_factory.build(self)
        self.stderr_stream = self.stderr_factory.build(self)

        self.pipeline = await self.pipeline_factory.build(
            self,
            stdin_stream=self.stdin_stream,
            stdout_stream=self.stdout_stream,
            stderr_stream=self.stderr_stream
        )

        self.stdin_stream.close_reader()
        self.stdout_stream.close_writer()
        self.stderr_stream.close_writer()

    def wait(self, exceptions=True):
        return self.shell.event_loop.run_until_complete(
            self.wait_async(exceptions=exceptions)
        )

    async def wait_async(self, exceptions=True):
        ret = await self.pipeline.wait()

        if exceptions:
            procnodes = self.get_process_nodes()
            if any(procnode.proc.returncode != 0 for procnode in procnodes):
                raise ReturnCodeError(procnodes)

        return ret
