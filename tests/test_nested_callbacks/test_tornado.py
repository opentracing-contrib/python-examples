from __future__ import print_function


from tornado import gen, ioloop

from ..opentracing_mock import MockTracer
from ..testcase import OpenTracingTestCase
from ..span_propagation import TornadoScopeManager, TracerStackContext
from ..utils import stop_loop_when


class TestTornado(OpenTracingTestCase):
    def setUp(self):
        self.tracer = MockTracer(TornadoScopeManager())
        self.loop = ioloop.IOLoop.current()

    def test_main(self):
        # Start a Span and let the callback-chain
        # finish it when the task is done
        span = self.tracer.start_manual('one')
        self.submit(span)

        stop_loop_when(self.loop, lambda: len(self.tracer.finished_spans) == 1)
        self.loop.start()

        spans = self.tracer.finished_spans
        self.assertEqual(len(spans), 1)
        self.assertEqual(spans[0].operation_name, 'one')

        for i in range(1, 4):
            self.assertEqual(spans[0].tags.get('key%s' % i, None), str(i))

    def _active_span(self):
        scope = self.tracer.scope_manager.active()
        if scope is None:
            return None

        return scope.span()

    # Since TracerStackContext propagates the
    # active Span, we don't need to activate the Span
    # manually at all.
    def submit(self, span):
        @gen.coroutine
        def task1():
            self.assertEqual(span, self._active_span())
            span.set_tag('key1', '1')

            @gen.coroutine
            def task2():
                self.assertEqual(span, self._active_span())
                span.set_tag('key2', '2')

                @gen.coroutine
                def task3():
                    self.assertEqual(span, self._active_span())
                    span.set_tag('key3', '3')
                    span.finish()

                yield task3()

            yield task2()

        with TracerStackContext() as ctx:
            with self.tracer.scope_manager.activate(span, False):
                self.loop.run_sync(task1)
