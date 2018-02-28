from __future__ import print_function

from tornado import gen, ioloop

from ..opentracing_mock import MockTracer
from ..span_propagation import TornadoScopeManager, TracerStackContext
from ..testcase import OpenTracingTestCase
from ..utils import get_logger, stop_loop_when


logger = get_logger(__name__)


class TestTornado(OpenTracingTestCase):
    def setUp(self):
        self.tracer = MockTracer(TornadoScopeManager())
        self.loop = ioloop.IOLoop.current()

    def test_main(self):
        # Create a Span and use it as (explicit) parent of a pair of subtasks.
        with TracerStackContext():
            parent_span = self.tracer.start_span('parent')
            self.submit_subtasks(parent_span)

        stop_loop_when(self.loop, lambda: len(self.tracer.finished_spans) >= 2)
        self.loop.start()

        # Late-finish the parent Span now.
        parent_span.finish()

        spans = self.tracer.finished_spans
        self.assertEqual(len(spans), 3)
        self.assertNamesEqual(spans, ['task1', 'task2', 'parent'])

        for i in range(2):
            self.assertSameTrace(spans[i], spans[-1])
            self.assertIsChildOf(spans[i], spans[-1])
            self.assertTrue(spans[i].finish_time <= spans[-1].finish_time)

    # Fire away a few subtasks, passing a parent Span whose lifetime
    # is not tied at all to the children.
    def submit_subtasks(self, parent_span):
        @gen.coroutine
        def task(name):
            logger.info('Running %s' % name)
            with self.tracer.start_active_span(name,
                                               True,
                                               child_of=parent_span):
                gen.sleep(0.1)

        self.loop.add_callback(task, 'task1')
        self.loop.add_callback(task, 'task2')
