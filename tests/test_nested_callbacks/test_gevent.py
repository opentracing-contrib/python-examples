from __future__ import print_function

import unittest

import gevent

from ..opentracing_mock import MockTracer


class TestGevent(unittest.TestCase):
    def setUp(self):
        self.tracer = MockTracer()

    def test_main(self):
        # Start a Span and let the callback-chain
        # finish it when the task is done
        span = self.tracer.start_span('one')
        self.submit(span)

        gevent.wait()

        spans = self.tracer.finished_spans
        self.assertEqual(len(spans), 1)
        self.assertEqual(spans[0].operation_name, 'one')

        for i in range(1, 4):
            self.assertEqual(spans[0].tags.get('key%s' % i, None), str(i))

    def submit(self, span):
        def task1():
            span.set_tag('key1', '1')

            def task2():
                span.set_tag('key2', '2')

                def task3():
                    span.set_tag('key3', '3')
                    span.finish()

                gevent.spawn(task3)

            gevent.spawn(task2)

        gevent.spawn(task1)
