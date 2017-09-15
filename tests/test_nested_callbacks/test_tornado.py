from __future__ import print_function

import unittest

from tornado import gen, ioloop

from ..opentracing_mock import MockTracer
from ..utils import stop_loop_when


class TestTornado(unittest.TestCase):
    def setUp(self):
        self.tracer = MockTracer()
        self.loop = ioloop.IOLoop.current()

    def test_main(self):
        # Start a Span and let the callback-chain
        # finish it when the task is done
        span = self.tracer.start_span('one')
        self.submit(span)

        stop_loop_when(self.loop, lambda: len(self.tracer.finished_spans) == 1)
        self.loop.start()

        spans = self.tracer.finished_spans
        self.assertEqual(len(spans), 1)
        self.assertEqual(spans[0].operation_name, 'one')

        for i in range(1, 4):
            self.assertEqual(spans[0].tags.get('key%s' % i, None), str(i))

    def submit(self, span):
        @gen.coroutine
        def task1():
            span.set_tag('key1', '1')

            @gen.coroutine
            def task2():
                span.set_tag('key2', '2')

                @gen.coroutine
                def task3():
                    span.set_tag('key3', '3')
                    span.finish()

                self.loop.add_callback(task3)

            self.loop.add_callback(task2)

        self.loop.add_callback(task1)
