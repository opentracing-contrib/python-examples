from __future__ import print_function

import random

import asyncio

from mocktracer import MockTracer
from ..span_propagation import AsyncioScopeManager
from ..testcase import OpenTracingTestCase
from ..utils import RefCount, get_logger, stop_loop_when


random.seed()
logger = get_logger(__name__)


class TestAsyncio(OpenTracingTestCase):
    def setUp(self):
        self.tracer = MockTracer(AsyncioScopeManager())
        self.loop = asyncio.get_event_loop()

    def test_main(self):
        # Need to run within a Task, as the scope manager depends
        # on Task.current_task()
        async def main_task():
            with self.tracer.start_active_span('parent', True):
                tasks = self.submit_callbacks()
                await asyncio.gather(*tasks)

        self.loop.create_task(main_task())

        stop_loop_when(self.loop, lambda: len(self.tracer.finished_spans()) >= 4)
        self.loop.run_forever()

        spans = self.tracer.finished_spans()
        self.assertEquals(len(spans), 4)
        self.assertNamesEqual(spans, ['task', 'task', 'task', 'parent'])

        for i in range(3):
            self.assertSameTrace(spans[i], spans[-1])
            self.assertIsChildOf(spans[i], spans[-1])

    async def task(self, interval, parent_span):
        logger.info('Starting task')

        with self.tracer.scope_manager.activate(parent_span, False):
            with self.tracer.start_active_span('task', True):
                await asyncio.sleep(interval)

    def submit_callbacks(self):
        parent_span = self.tracer.scope_manager.active.span
        tasks = []
        for i in range(3):
            interval = 0.1 + random.randint(200, 500) * 0.001
            t = self.loop.create_task(self.task(interval, parent_span))
            tasks.append(t)

        return tasks
