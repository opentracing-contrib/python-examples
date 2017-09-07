from __future__ import print_function

import unittest

import gevent

from ..opentracing_mock import MockTracer


class TestGevent(unittest.TestCase):
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
        self.assertEqual(spans[0].operation_name, 'initial')
        self.assertEqual(spans[1].operation_name, 'subtask')
        self.assertEqual(spans[2].operation_name, 'task')

        # task/subtask are part of the same trace,
        # and subtask is a child of task
        self.assertEquals(spans[1].context.trace_id,
                          spans[2].context.trace_id)
        self.assertEquals(spans[1].parent_id, spans[2].context.span_id)

        # initial task is not related in any way to those two tasks
        self.assertNotEqual(spans[0].context.trace_id,
                            spans[1].context.trace_id)
        self.assertEqual(spans[0].parent_id, None)

    def task(self, span):
        # Create a new Span for this task
        with self.tracer.start_span('task') as task_span:
            gevent.sleep(0.01)

            with span:
                # Simulate work strictly related to the initial Span
                gevent.sleep(0.2)

            # Use the task span as parent of a new subtask
            with self.tracer.start_span('subtask', child_of=task_span):
                gevent.sleep(0.3)

    def submit_another_task(self, span):
        gevent.spawn(self.task, span)
