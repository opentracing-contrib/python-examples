from __future__ import absolute_import, print_function

import gevent

from ..opentracing_mock import MockTracer
from ..testcase import OpenTracingTestCase


class TestGevent(OpenTracingTestCase):
    def setUp(self):
        self.tracer = MockTracer()

    def test_main(self):
        res = gevent.spawn(self.parent_task, 'message').get()
        self.assertEqual(res, 'message::response')

        spans = self.tracer.finished_spans
        self.assertEqual(len(spans), 2)
        self.assertNamesEqual(spans, ['child', 'parent'])
        self.assertIsChildOf(spans[0], spans[1])

    def parent_task(self, message):
        with self.tracer.start_span('parent') as span:
            res = gevent.spawn(self.child_task, message, span).get()

        return res

    def child_task(self, message, span):
        with self.tracer.start_span('child', child_of=span):
            return '%s::response' % message
