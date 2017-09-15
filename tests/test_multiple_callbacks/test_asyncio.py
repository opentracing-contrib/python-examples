from __future__ import print_function

import unittest
import random

import asyncio

from ..opentracing_mock import MockTracer
from ..utils import RefCount, get_logger, stop_loop_when


random.seed()
logger = get_logger(__name__)


class TestAsyncio(unittest.TestCase):
    def setUp(self):
        self.tracer = MockTracer()
        self.loop = asyncio.get_event_loop()

    def test_main(self):
        span = self.tracer.start_span('parent')

        span._ref_count = RefCount(1)
        self.submit_callbacks(span)
        if span._ref_count.decr() == 0:
            span.finish()

        stop_loop_when(self.loop, lambda: len(self.tracer.finished_spans) >= 4)
        self.loop.run_forever()

        spans = self.tracer.finished_spans
        self.assertEquals(len(spans), 4)
        self.assertEquals([x.operation_name for x in spans],
                          ['task', 'task', 'task', 'parent'])

        for i in range(3):
            self.assertEquals(spans[i].context.trace_id,
                              spans[-1].context.trace_id)
            self.assertEquals(spans[i].parent_id,
                              spans[-1].context.span_id)

    async def task(self, interval, parent_span):
        logger.info('Starting task')

        try:
            with self.tracer.start_span('task', child_of=parent_span):
                await asyncio.sleep(interval)
        finally:
            if parent_span._ref_count.decr() == 0:
                parent_span.finish()

    def submit_callbacks(self, parent_span):
        for i in range(3):
            parent_span._ref_count.incr()
            interval = 0.1 + random.randint(200, 500) * 0.001
            self.loop.create_task(self.task(interval, parent_span))
