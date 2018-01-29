from __future__ import print_function

import random

from tornado import gen, ioloop

from ..opentracing_mock import MockTracer
from ..span_propagation import TornadoScopeManager, TracerStackContext
from ..testcase import OpenTracingTestCase
from ..utils import RefCount, get_logger, stop_loop_when


random.seed()
logger = get_logger(__name__)


class TestTornado(OpenTracingTestCase):
    def setUp(self):
        self.tracer = MockTracer()
        self.loop = ioloop.IOLoop.current()

    def test_main(self):
        def init():
            try:
                scope = self.tracer.start_active('parent', finish_on_close=False)
                scope.span()._ref_count = RefCount(1)
                self.submit_callbacks(scope.span())
            finally:
                scope.close()
                if scope.span()._ref_count.decr() == 0:
                    scope.span().finish()

        with TracerStackContext():
            self.loop.add_callback(init)

        stop_loop_when(self.loop, lambda: len(self.tracer.finished_spans) >= 4)
        self.loop.start()

        spans = self.tracer.finished_spans
        self.assertEquals(len(spans), 4)
        self.assertNamesEqual(spans, ['task', 'task', 'task', 'parent'])

        for i in range(3):
            self.assertSameTrace(spans[i], spans[-1])
            self.assertIsChildOf(spans[i], spans[-1])

    @gen.coroutine
    def task(self, interval, parent_span):
        logger.info('Starting task')

        # No need to reactivate the parent_span, as TracerStackContext
        # keeps track of it.
        try:
            with self.tracer.start_active('task'):
                yield gen.sleep(interval)
        finally:
            if parent_span._ref_count.decr() == 0:
                parent_span.finish()

    def submit_callbacks(self, parent_span):
        for i in range(3):
            parent_span._ref_count.incr()
            self.loop.add_callback(self.task,
                                   0.1 + random.randint(200, 500) * .001,
                                   parent_span)
