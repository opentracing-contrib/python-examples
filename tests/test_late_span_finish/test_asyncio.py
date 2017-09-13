from __future__ import print_function

import unittest

import asyncio

from ..opentracing_mock import MockTracer
from ..utils import get_logger
from ..utils_tornado import run_until


logger = get_logger(__name__)


class TestAsyncio(unittest.TestCase):
    def setUp(self):
        self.tracer = MockTracer()
        self.loop = asyncio.get_event_loop()

    def test_main(self):
        # Create a Span and use it as parent of a pair of subtasks.
        parent_span = self.tracer.start_span('parent')
        self.submit_subtasks(parent_span)

        run_until(self.loop, lambda: len(self.tracer.finished_spans) >= 2)
        self.loop.run_forever()

        # Late-finish the parent Span now.
        parent_span.finish()

        spans = self.tracer.finished_spans
        self.assertEqual(len(spans), 3)
        self.assertEqual(spans[0].operation_name, 'task1')
        self.assertEqual(spans[1].operation_name, 'task2')
        self.assertEqual(spans[2].operation_name, 'parent')

        for i in range(2):
            self.assertEquals(spans[i].context.trace_id,
                              spans[-1].context.trace_id)
            self.assertEquals(spans[i].parent_id,
                              spans[-1].context.span_id)
            self.assertTrue(spans[i].finish_time <= spans[-1].finish_time)

    # Fire away a few subtasks, passing a parent Span whose lifetime
    # is not tied at all to the children.
    def submit_subtasks(self, parent_span):
        async def task(name, interval):
            logger.info('Running %s' % name)
            with self.tracer.start_span(name, child_of=parent_span):
                await asyncio.sleep(interval)

        self.loop.create_task(task('task1', 0.1))
        self.loop.create_task(task('task2', 0.3))
