from __future__ import print_function

import random
import unittest

from tornado import gen, ioloop

from ..opentracing_mock import MockTracer
from ..utils import RefCount, get_logger, get_tags_count
from ..utils_tornado import run_until


random.seed()
logger = get_logger(__name__)


@gen.coroutine
def callback(span, delay):
    logger.info('Starting callback')

    try:
        yield gen.sleep(delay)
        span.set_tag('test_tag_%s' % random.randint(1, 100), 'random')
    finally:
        if span._ref_count.decr() == 0:
            span.finish()

    logger.info('Finishing callback')


class TestTornado(unittest.TestCase):
    def setUp(self):
        self.tracer = MockTracer()
        self.loop = ioloop.IOLoop.current()

    def test(self):
        self.loop.add_callback(self.entry_thread)

        run_until(self.loop, lambda : len(self.tracer.finished_spans) > 0)
        self.loop.start()

        spans = self.tracer.finished_spans
        self.assertEqual(len(spans), 1)

        tags_count = get_tags_count(spans[0], 'test_tag_')
        self.assertEquals(tags_count, 1)

    def test_two_callbacks(self):
        self.loop.add_callback(self.entry_thread_two_callbacks)

        run_until(self.loop, lambda : len(self.tracer.finished_spans) > 0)
        self.loop.start()

        spans = self.tracer.finished_spans
        self.assertEqual(len(spans), 1)

        # Check that the two callbacks finished and each added to span
        # its own tag ('test_tag_{random}')
        tags_count = get_tags_count(spans[0], 'test_tag_')
        self.assertEquals(tags_count, 2)

    # Target will be completed before callback completed.
    @gen.coroutine
    def entry_thread(self):
        span = self.tracer.start_span('parent')
        span._ref_count = RefCount(1)

        # Callback is finished at a late time and we are not
        # able to check status of the callback.
        self.loop.add_callback(callback, span, 0.5)

    # Target will be completed before callback completed.
    @gen.coroutine
    def entry_thread_two_callbacks(self):
        span = self.tracer.start_span('parent')
        span._ref_count = RefCount(2)

        # Callbacks are finished at some unpredictable time and we are not
        # able to check status of the callback.
        for i in range(2):
            interval = 0.1 + random.randint(0, 500) * 0.001
            self.loop.add_callback(callback, span, interval)
