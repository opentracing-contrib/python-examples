from __future__ import print_function

import random

import gevent

from ..opentracing_mock import MockTracer
from ..testcase import OpenTracingTestCase
from ..utils import RefCount, get_logger


random.seed()
logger = get_logger(__name__)


class TestGevent(OpenTracingTestCase):
    def setUp(self):
        self.tracer = MockTracer()

    def test_main(self):
        span = self.tracer.start_span('parent')

        span._ref_count = RefCount(1)
        self.submit_callbacks(span)
        if span._ref_count.decr() == 0:
            span.finish()

        gevent.wait(timeout=5.0)

        spans = self.tracer.finished_spans
        self.assertEquals(len(spans), 4)
        self.assertEquals([x.operation_name for x in spans],
                          ['task', 'task', 'task', 'parent'])

        for i in range(3):
            self.assertSameTrace(spans[i], spans[-1])
            self.assertIsChildOf(spans[i], spans[-1])

    def task(self, interval, parent_span):
        logger.info('Starting task')

        try:
            with self.tracer.start_span('task', child_of=parent_span):
                gevent.sleep(interval)
        finally:
            if parent_span._ref_count.decr() == 0:
                parent_span.finish()

    def submit_callbacks(self, parent_span):
        for i in range(3):
            parent_span._ref_count.incr()
            gevent.spawn(self.task,
                         0.1 + random.randint(200, 500) * 0.001,
                         parent_span)
