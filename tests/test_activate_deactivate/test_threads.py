from __future__ import print_function

from concurrent.futures import ThreadPoolExecutor
import random
from threading import Thread
import time
import unittest

from ..opentracing_mock import MockTracer
from ..utils import RefCount, await_until, get_logger


random.seed()
logger = get_logger(__name__)


class Callback(object):
    def __init__(self, span, delay):
        self.span = span
        self.delay = delay

    def __call__(self, *args, **kwargs):
        logger.info('Starting callback')

        try:
            time.sleep(self.delay)
            self.span.set_tag('test_tag_%s' % random.randint(1, 100), 'random')
        finally:
            if self.span._ref_count.decr() == 0:
                self.span.finish()

        logger.info('Finishing callback')


class TestThreads(unittest.TestCase):
    def setUp(self):
        self.tracer = MockTracer()
        self.executor = ThreadPoolExecutor(max_workers=3)

    def test(self):
        t = Thread(target=self.entry_thread)
        t.start()
        t.join(10.0)

        await_until(lambda : len(self.tracer.finished_spans) > 0, 15.0)

        spans = self.tracer.finished_spans
        self.assertEqual(len(spans), 1)

        tags_count = self.get_tags_count(spans[0])
        self.assertEquals(tags_count, 1)

    def test_two_callbacks(self):
        t = Thread(target=self.entry_thread_two_callbacks)
        t.start()
        t.join(10.0)

        await_until(lambda : len(self.tracer.finished_spans) > 0, 15.0)

        spans = self.tracer.finished_spans
        self.assertEqual(len(spans), 1)

        # Check that the two callbacks finished and each added to span
        # its own tag ('test_tag_{random}')
        tags_count = self.get_tags_count(spans[0])
        self.assertEquals(tags_count, 2)

    # Thread target will be completed before callback completed.
    def entry_thread(self):
        span = self.tracer.start_span('parent')
        span._ref_count = RefCount(1)

        # Callback is finished at a late time and we are not
        # able to check status of the callback.
        self.executor.submit(Callback(span, 0.5))

    # Thread target will be completed before callback completed.
    def entry_thread_two_callbacks(self):
        span = self.tracer.start_span('parent')
        span._ref_count = RefCount(2)
        callback = Callback(span, 0.1 + random.randint(0, 500) * 0.001)
        callback2 = Callback(span, 0.1 + random.randint(0, 500) * 0.001)

        # Callbacks are finished at some unpredictable time and we are not
        # able to check status of the callback.
        self.executor.submit(callback)
        self.executor.submit(callback2)

    def get_tags_count(self, span):
        test_keys = set()
        for key in span.tags.iterkeys():
            if key.startswith('test_tag_'):
                test_keys.add(key)

        return len(test_keys)
