from __future__ import print_function

import unittest

import asyncio

from ..opentracing_mock import MockTracer
from ..utils_tornado import run_until


class TestAsyncio(unittest.TestCase):
    def setUp(self):
        self.tracer = MockTracer()
        self.loop = asyncio.get_event_loop()

    def test_main(self):
        # Start a Span and let the callback-chain
        # finish it when the task is done
        span = self.tracer.start_span('one')
        self.submit(span)

        run_until(self.loop, lambda: len(self.tracer.finished_spans) == 1)
        self.loop.run_forever()

        spans = self.tracer.finished_spans
        self.assertEqual(len(spans), 1)
        self.assertEqual(spans[0].operation_name, 'one')

        for i in range(1, 4):
            self.assertEqual(spans[0].tags.get('key%s' % i, None), str(i))

    def submit(self, span):
        async def task1():
            span.set_tag('key1', '1')

            async def task2():
                span.set_tag('key2', '2')

                async def task3():
                    span.set_tag('key3', '3')
                    span.finish()

                self.loop.create_task(task3())

            self.loop.create_task(task2())

        self.loop.create_task(task1())
