import asyncio
import contextlib
import os
import pathlib
import sys
import unittest

from ...Stream import Stream, NullStream, FileStream, PipeStream
from ...PipelineNode import PipelineProcess, PipelineChannel
from ...util import which, export

from ..test_util import register, TmpDirMixin

__all__ = []

@export
@register()
class TestCreateAndWait(TmpDirMixin):
    def runTest(self):
        cwd = pathlib.Path(self.tmpdir.name)
        test_file = 'tmp.txt'
        cat = which('cat')
        message = "Hello World!"
        event_loop = asyncio.new_event_loop()

        async def run_and_wait():
            with PipeStream(None) as p3, NullStream(None) as null_stream:
                with PipeStream(None) as p1, PipeStream(None) as p2:
                    cat1 = await PipelineProcess.create(
                        event_loop,
                        cwd = cwd.resolve(),
                        env = {},
                        args = [cat],
                        stdin_stream = p1,
                        stdout_stream = p2,
                        stderr_stream = null_stream
                    )

                    cat2 = await PipelineProcess.create(
                        event_loop,
                        cwd = cwd.resolve(),
                        env = {},
                        args = [cat],
                        stdin_stream = p2,
                        stdout_stream = p3,
                        stderr_stream = null_stream
                    )

                    channel = await PipelineChannel.create(
                        event_loop,
                        left = cat1,
                        right = cat2
                    )

                    p1.writer().write(message)

                p3.close_writer()

                stdout_result = p3.reader().read()

                returncodes = await channel.wait_async()

            return channel, returncodes, stdout_result

        channel, returncodes, stdout_result = event_loop.run_until_complete(run_and_wait())

        processes = [
            channel.left.proc,
            channel.right.proc
        ]

        self.assertEqual([rc for rc in returncodes], [0, 0])
        self.assertEqual([p.returncode for p in processes], [0, 0])
        self.assertEqual(stdout_result, message)
