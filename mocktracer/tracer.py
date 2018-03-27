from threading import Lock
import time

import opentracing
from opentracing import Format, Tracer
from opentracing import UnsupportedFormatException
from .scope_manager import ThreadLocalScopeManager
from .context import SpanContext
from .span import MockSpan
from .util import generate_id


class MockTracer(Tracer):

    def __init__(self, scope_manager=None):
        """Initialize a MockTracer instance.

        By default, MockTracer registers propagators for Format.TEXT_MAP and
        Format.HTTP_HEADERS. The user should either call register_propagator()
        for each needed inject/extract format.

        The required formats are opt-in because of protobuf version conflicts
        with the binary carrier.
        """

        scope_manager = ThreadLocalScopeManager() \
            if scope_manager is None else scope_manager
        super(MockTracer, self).__init__(scope_manager)

        self._propagators = {}
        self._finished_spans = []
        self._spans_lock = Lock()

        self._register_required_propagators()

    def register_propagator(self, format, propagator):
        """Register a propagator with this MockTracer.

        :param string format: a Format identifier like Format.TEXT_MAP
        :param Propagator propagator: a Propagator instance to handle
            inject/extract calls involving `format`
        """
        self._propagators[format] = propagator

    def _register_required_propagators(self):
        from .text_propagator import TextPropagator
        self.register_propagator(Format.TEXT_MAP, TextPropagator())
        self.register_propagator(Format.HTTP_HEADERS, TextPropagator())

    def finished_spans(self):
        with self._spans_lock:
            return list(self._finished_spans)

    def reset(self):
        with self._spans_lock:
            self._finished_spans.clear()

    def _append_finished_span(self, span):
        with self._spans_lock:
            self._finished_spans.append(span)

    def start_active_span(self,
                          operation_name,
                          finish_on_close,
                          child_of=None,
                          references=None,
                          tags=None,
                          start_time=None,
                          ignore_active_span=False):

        # create a new Span
        span = self.start_span(
            operation_name=operation_name,
            child_of=child_of,
            references=references,
            tags=tags,
            start_time=start_time,
            ignore_active_span=ignore_active_span,
        )

        return self.scope_manager.activate(span, finish_on_close)

    def start_span(self,
                   operation_name=None,
                   child_of=None,
                   references=None,
                   tags=None,
                   start_time=None,
                   ignore_active_span=False):

        start_time = time.time() if start_time is None else start_time

        # See if we have a parent_ctx in `references`
        parent_ctx = None
        if child_of is not None:
            parent_ctx = (
                child_of if isinstance(child_of, opentracing.SpanContext)
                else child_of.context)
        elif references is not None and len(references) > 0:
            # TODO only the first reference is currently used
            parent_ctx = references[0].referenced_context

        # retrieve the active SpanContext
        if not ignore_active_span and parent_ctx is None:
            scope = self.scope_manager.active
            if scope is not None:
                parent_ctx = scope.span.context

        # Assemble the child ctx
        ctx = SpanContext(span_id=generate_id())
        if parent_ctx is not None:
            if parent_ctx._baggage is not None:
                ctx._baggage = parent_ctx._baggage.copy()
            ctx.trace_id = parent_ctx.trace_id
        else:
            ctx.trace_id = generate_id()

        # Tie it all together
        return MockSpan(
            self,
            operation_name=operation_name,
            context=ctx,
            parent_id=(None if parent_ctx is None else parent_ctx.span_id),
            tags=tags,
            start_time=start_time)

    def inject(self, span_context, format, carrier):
        if format in self._propagators:
            self._propagators[format].inject(span_context, carrier)
        else:
            raise UnsupportedFormatException()

    def extract(self, format, carrier):
        if format in self._propagators:
            return self._propagators[format].extract(carrier)
        else:
            raise UnsupportedFormatException()
