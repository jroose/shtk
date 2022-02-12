"Tools to make using asyncio a little less complicated"

class AsyncHelper:
    "Helps manage running programs while communicating with them"
    def __init__(self, event_loop):
        self.event_loop = event_loop
        self.task_count = 0
        self.completed_tasks = set()

    def mark_completed(self, task_id):
        "Mark a task as completed"
        num_prior = len(self.completed_tasks)
        self.completed_tasks.add(task_id)
        num_post = len(self.completed_tasks)
        if num_post == num_prior:
            raise ValueError(f"Task {task_id} completed twice")

        if num_post == self.task_count:
            self.event_loop.stop()

    async def _manage_task(self, task_id, coro):
        "Wait on a task, then mark it completed"
        try:
            ret = await coro
            self.mark_completed(task_id)
            return ret
        except:
            self.event_loop.stop()
            raise

    def create_task(self, coro, *, name=None):
        "Run a task"
        task_id = self.task_count
        self.task_count += 1
        return self.event_loop.create_task(self._manage_task(task_id, coro), name=name)

    def _manage_reader(self, task_id, fd_read, callback, *args):
        "Run a callback, then mark its task completed"
        try:
            ret = callback(fd_read, *args)
            self.event_loop.remove_reader(fd_read)
            self.mark_completed(task_id)
            return ret
        except:
            self.event_loop.stop()
            raise

    def add_reader(self, fd_read, callback, *args):
        "Add a reader callback"
        task_id = self.task_count
        self.task_count += 1
        return self.event_loop.add_reader(
            fd_read, self._manage_reader, task_id, fd_read,
            callback, *args
        )

    def run(self):
        "Run the event loop until all tasks are completed"
        return self.event_loop.run_forever()
