from __future__ import print_function

import random

import gevent

from ..opentracing_mock import MockTracer
from ..testcase import OpenTracingTestCase
from ..span_propagation import GeventScopeManager
from ..utils import RefCount, get_logger


random.seed()
logger = get_logger(__name__)


class TestGevent(OpenTracingTestCase):
    def setUp(self):
        self.tracer = MockTracer(GeventScopeManager())

    def test_main(self):
        try:
            scope = self.tracer.start_active('parent', finish_on_close=False)
            scope.span()._ref_count = RefCount(1)
            self.submit_callbacks(scope.span())
        finally:
            scope.close()
            if scope.span()._ref_count.decr() == 0:
                scope.span().finish()

        gevent.wait(timeout=5.0)

        spans = self.tracer.finished_spans
        self.assertEquals(len(spans), 4)
        self.assertNamesEqual(spans, ['task', 'task', 'task', 'parent'])

        for i in range(3):
            self.assertSameTrace(spans[i], spans[-1])
            self.assertIsChildOf(spans[i], spans[-1])

    def task(self, interval, parent_span):
        logger.info('Starting task')

        try:
            scope = self.tracer.scope_manager.activate(parent_span, False)
            with self.tracer.start_active('task'):
                gevent.sleep(interval)
        finally:
            scope.close()
            if parent_span._ref_count.decr() == 0:
                parent_span.finish()

    def submit_callbacks(self, parent_span):
        for i in range(3):
            parent_span._ref_count.incr()
            gevent.spawn(self.task,
                         0.1 + random.randint(200, 500) * 0.001,
                         parent_span)
