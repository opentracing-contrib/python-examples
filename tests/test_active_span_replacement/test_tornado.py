from __future__ import print_function

from tornado import gen, ioloop

from ..opentracing_mock import MockTracer
from ..testcase import OpenTracingTestCase
from ..utils import stop_loop_when


class TestTornado(OpenTracingTestCase):
    def setUp(self):
        self.tracer = MockTracer()
        self.loop = ioloop.IOLoop.current()

    def test_main(self):
        # Start an isolated task and query for its result -and finish it-
        # in another task/thread
        span = self.tracer.start_span('initial')
        self.submit_another_task(span)

        stop_loop_when(self.loop, lambda: len(self.tracer.finished_spans) >= 3)
        self.loop.start()

        spans = self.tracer.finished_spans
        self.assertEqual(len(spans), 3)
        self.assertEqual(spans[0].operation_name, 'initial')
        self.assertEqual(spans[1].operation_name, 'subtask')
        self.assertEqual(spans[2].operation_name, 'task')

        # task/subtask are part of the same trace,
        # and subtask is a child of task
        self.assertSameTrace(spans[1], spans[2])
        self.assertIsChildOf(spans[1], spans[2])

        # initial task is not related in any way to those two tasks
        self.assertNotSameTrace(spans[0], spans[1])
        self.assertEqual(spans[0].parent_id, None)

    @gen.coroutine
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
        self.loop.add_callback(self.task, span)
