from __future__ import absolute_import, print_function

from concurrent.futures import ThreadPoolExecutor

from mocktracer import MockTracer
from ..testcase import OpenTracingTestCase


class TestThreads(OpenTracingTestCase):
    def setUp(self):
        self.tracer = MockTracer()
        self.executor = ThreadPoolExecutor(max_workers=3)

    def test_main(self):
        res = self.executor.submit(self.parent_task, 'message').result()
        self.assertEqual(res, 'message::response')

        spans = self.tracer.finished_spans()
        self.assertEqual(len(spans), 2)
        self.assertNamesEqual(spans, ['child', 'parent'])
        self.assertIsChildOf(spans[0], spans[1])

    def parent_task(self, message):
        with self.tracer.start_active_span('parent', True) as scope:
            f = self.executor.submit(self.child_task, message, scope.span)
            res = f.result()

        return res

    def child_task(self, message, span):
        with self.tracer.scope_manager.activate(span, False):
            with self.tracer.start_active_span('child', True):
                return '%s::response' % message
