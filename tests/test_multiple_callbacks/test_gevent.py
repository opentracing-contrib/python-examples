from __future__ import print_function

import random

import gevent

from mocktracer import MockTracer
from ..testcase import OpenTracingTestCase
from ..span_propagation import GeventScopeManager
from ..utils import RefCount, get_logger


random.seed()
logger = get_logger(__name__)


class TestGevent(OpenTracingTestCase):
    def setUp(self):
        self.tracer = MockTracer(GeventScopeManager())

    def test_main(self):
        def main_task():
            with self.tracer.start_active_span('parent', True):
                tasks = self.submit_callbacks()
                gevent.joinall(tasks)

        gevent.spawn(main_task)
        gevent.wait(timeout=5.0)

        spans = self.tracer.finished_spans()
        self.assertEquals(len(spans), 4)
        self.assertNamesEqual(spans, ['task', 'task', 'task', 'parent'])

        for i in range(3):
            self.assertSameTrace(spans[i], spans[-1])
            self.assertIsChildOf(spans[i], spans[-1])

    def task(self, interval, parent_span):
        logger.info('Starting task')

        with self.tracer.scope_manager.activate(parent_span, False):
            with self.tracer.start_active_span('task', True):
                gevent.sleep(interval)

    def submit_callbacks(self):
        parent_span = self.tracer.scope_manager.active.span
        tasks = []
        for i in range(3):
            interval = 0.1 + random.randint(200, 500) * 0.001
            t = gevent.spawn(self.task, interval, parent_span)
            tasks.append(t)

        return tasks
