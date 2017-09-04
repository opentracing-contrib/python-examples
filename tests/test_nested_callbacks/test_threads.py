from __future__ import print_function

from concurrent.futures import ThreadPoolExecutor
import unittest

from ..opentracing_mock import MockTracer
from ..utils import await_until


class TestThreads(unittest.TestCase):
    def setUp(self):
        self.tracer = MockTracer()
        self.executor = ThreadPoolExecutor(max_workers=3)

    def test_main(self):
        # Start a Span and let the callback-chain
        # finish it when the task is done
        span = self.tracer.start_span('one')
        self.submit(span)

        # Cannot shutdown the executor and wait for the callbacks
        # to be run, as in such case only the first will be executed,
        # and the rest will get canceled.
        await_until(lambda : len(self.tracer.finished_spans) == 1, 5)

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

                self.executor.submit(task3)

            self.executor.submit(task2)

        self.executor.submit(task1)
