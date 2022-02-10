import os
import asyncio
from collections import Counter

from .StreamFactory import ManualStreamFactory

class AsyncHelper:
    def __init__(self, event_loop):
        self.event_loop = event_loop
        self.task_count = 0
        self.completed_tasks = set()

    def mark_completed(self, task_id):
        num_prior = len(self.completed_tasks)
        self.completed_tasks.add(task_id)
        num_post = len(self.completed_tasks)
        if num_post == num_prior:
            raise ValueError(f"Task {task_id} completed twice")

        if num_post == self.task_count:
            self.event_loop.stop()

    async def _manage_task(self, task_id, coro):
        try:
            ret = await coro
            self.mark_completed(task_id)
            return ret
        except:
            self.event_loop.stop()
            raise

    def create_task(self, coro, *, name=None):
        task_id = self.task_count
        self.task_count += 1
        return self.event_loop.create_task(self._manage_task(task_id, coro), name=name)

    def _manage_reader(self, task_id, fd, callback, *args):
        try:
            ret = callback(fd, *args)
            self.event_loop.remove_reader(fd)
            self.mark_completed(task_id)
            return ret
        except:
            self.event_loop.stop()
            raise

    def add_reader(self, fd, callback, *args):
        task_id = self.task_count
        self.task_count += 1
        return self.event_loop.add_reader(fd, self._manage_reader, task_id, fd, callback, *args)

    def run(self):
        return self.event_loop.run_forever()

async def run_job(job, stdin, stdout, stderr, exceptions):
    await job.run_async(
        stdin_factory=ManualStreamFactory(fileobj_r=stdin),
        stdout_factory=ManualStreamFactory(fileobj_w=stdout),
        stderr_factory=ManualStreamFactory(fileobj_w=stderr)
    )
    await job.wait_async(
        exceptions = exceptions
    )
