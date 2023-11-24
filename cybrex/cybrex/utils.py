import asyncio


class MultipleAsyncExecution:
    def __init__(self, par):
        self.par = par
        self.s = asyncio.Semaphore(par)

    async def execute(self, coro):
        if not self.s:
            raise RuntimeError('`ParallelAsyncExecution` has been already joined')
        await self.s.acquire()
        task = asyncio.create_task(coro)
        task.add_done_callback(lambda f: self.s.release())
        return task

    async def join(self):
        for i in range(self.par):
            await self.s.acquire()
        s = self.s
        self.s = None
        for i in range(self.par):
            s.release()
