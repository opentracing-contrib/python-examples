from __future__ import print_function

import gevent

from ..opentracing_mock import MockTracer
from ..testcase import OpenTracingTestCase


class TestGevent(OpenTracingTestCase):
    def setUp(self):
        self.tracer = MockTracer()

    def test_main(self):
        # Start an isolated task and query for its result -and finish it-
        # in another task/thread
        span = self.tracer.start_span('initial')
        self.submit_another_task(span)

        gevent.wait(timeout=5.0)

        spans = self.tracer.finished_spans
        self.assertEqual(len(spans), 3)
        self.assertNamesEqual(spans, ['initial', 'subtask', 'task'])

        # task/subtask are part of the same trace,
        # and subtask is a child of task
        self.assertSameTrace(spans[1], spans[2])
        self.assertIsChildOf(spans[1], spans[2])

        # initial task is not related in any way to those two tasks
        self.assertNotSameTrace(spans[0], spans[1])
        self.assertEqual(spans[0].parent_id, None)

    def task(self, span):
        # Create a new Span for this task
        with self.tracer.start_span('task') as task_span:

            with span:
                # Simulate work strictly related to the initial Span
                pass

            # Use the task span as parent of a new subtask
            with self.tracer.start_span('subtask', child_of=task_span):
                pass

    def submit_another_task(self, span):
        gevent.spawn(self.task, span)
