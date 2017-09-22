from __future__ import print_function

import gevent
from opentracing.ext import tags

from ..opentracing_mock import MockTracer
from ..testcase import OpenTracingTestCase
from ..utils import get_one_by_tag

from .response_listener import ResponseListener


class Client(object):
    def __init__(self, tracer):
        self.tracer = tracer

    def task(self, message, listener):
        res = '%s::response' % message
        listener.on_response(res)
        return res

    def send_sync(self, message):
        span = self.tracer.start_span('send')
        span.set_tag(tags.SPAN_KIND, tags.SPAN_KIND_RPC_CLIENT)

        listener = ResponseListener(span)
        return gevent.spawn(self.task, message, listener).get()


class TestThreads(OpenTracingTestCase):
    def setUp(self):
        self.tracer = MockTracer()

    def test_main(self):
        client = Client(self.tracer)
        res = client.send_sync('message')
        self.assertEquals(res, 'message::response')

        spans = self.tracer.finished_spans
        self.assertEqual(len(spans), 1)

        span = get_one_by_tag(spans, tags.SPAN_KIND, tags.SPAN_KIND_RPC_CLIENT)
        self.assertIsNotNone(span)
