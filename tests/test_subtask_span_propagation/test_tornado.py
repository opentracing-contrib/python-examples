from __future__ import absolute_import, print_function

import functools

from tornado import gen, ioloop

from ..opentracing_mock import MockTracer
from ..span_propagation import TracerStackContext, TornadoScopeManager
from ..testcase import OpenTracingTestCase


class TestTornado(OpenTracingTestCase):
    def setUp(self):
        self.tracer = MockTracer(TornadoScopeManager())
        self.loop = ioloop.IOLoop.current()

    def test_main(self):
        parent_task = functools.partial(self.parent_task, 'message')
        with TracerStackContext():
            res = self.loop.run_sync(parent_task)
        self.assertEqual(res, 'message::response')

        spans = self.tracer.finished_spans
        self.assertEqual(len(spans), 2)
        self.assertNamesEqual(spans, ['child', 'parent'])
        self.assertIsChildOf(spans[0], spans[1])

    @gen.coroutine
    def parent_task(self, message):
        with self.tracer.start_active('parent'):
            res = yield self.child_task(message)

        raise gen.Return(res)

    @gen.coroutine
    def child_task(self, message):
        with self.tracer.start_active('child'):
            raise gen.Return('%s::response' % message)
