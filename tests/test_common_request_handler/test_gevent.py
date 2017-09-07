from __future__ import print_function

import functools
import time
import unittest

import gevent

from opentracing.ext import tags

from ..opentracing_mock import MockTracer
from ..utils import get_logger, get_one_by_operation_name
from ..utils_tornado import run_until
from .request_handler import RequestHandler


logger = get_logger(__name__)


class Client(object):
    def __init__(self, request_handler):
        self.request_handler = request_handler

    def send_task(self, message):
        gevent.sleep(0.1)
        request_context = {}

        def before_handler():
            gevent.sleep(0.1)
            self.request_handler.before_request(message, request_context)

        def after_handler():
            gevent.sleep(0.1)
            self.request_handler.after_request(message, request_context)

        gevent.spawn(before_handler).join()
        gevent.spawn(after_handler).join()

        return '%s::response' % message

    def send(self, message):
        return gevent.spawn(self.send_task, message)

    def send_sync(self, message, timeout=5.0):
        return gevent.spawn(self.send_task, message).get(timeout=timeout)


class TestGevent(unittest.TestCase):
    '''
    There is only one instance of 'RequestHandler' per 'Client'. Methods of
    'RequestHandler' are executed concurrently in different threads which are
    reused (common pool). Therefore we cannot use current active span and
    activate span. So one issue here is setting correct parent span.
    '''

    def setUp(self):
        self.tracer = MockTracer()
        self.client = Client(RequestHandler(self.tracer))

    def test_two_callbacks(self):
        response_greenlet1 = gevent.spawn(self.client.send_task, 'message1')
        response_greenlet2 = gevent.spawn(self.client.send_task, 'message2')

        gevent.joinall([response_greenlet1, response_greenlet2])

        self.assertEquals('message1::response', response_greenlet1.get())
        self.assertEquals('message2::response', response_greenlet2.get())

        spans = self.tracer.finished_spans
        self.assertEquals(len(spans), 2)

        for span in spans:
            self.assertEquals(span.tags.get(tags.SPAN_KIND, None),
                              tags.SPAN_KIND_RPC_CLIENT)

        self.assertNotEquals(spans[0].context.trace_id, spans[1].context.trace_id)
        self.assertIsNone(spans[0].parent_id)
        self.assertIsNone(spans[1].parent_id)

    def test_parent_not_picked(self):
        '''Active parent should not be picked up by child.'''

        with self.tracer.start_span('parent') as span:
            response = self.client.send_sync('no_parent')
            self.assertEquals('no_parent::response', response)

        spans = self.tracer.finished_spans
        self.assertEquals(len(spans), 2)

        child_span = get_one_by_operation_name(spans, 'send')
        self.assertIsNotNone(child_span)

        parent_span = get_one_by_operation_name(spans, 'parent')
        self.assertIsNotNone(parent_span)

        # Here check that there is no parent-child relation.
        self.assertNotEquals(parent_span.context.span_id, child_span.parent_id)

    def test_bad_solution_to_set_parent(self):
        '''Solution is bad because parent is per client (we don't have better choice)'''

        with self.tracer.start_span('parent') as span:
            client = Client(RequestHandler(self.tracer, span.context))
            response = client.send_sync('correct_parent')

            self.assertEquals('correct_parent::response', response)

        response = client.send_sync('wrong_parent')
        self.assertEquals('wrong_parent::response', response)

        spans = self.tracer.finished_spans
        self.assertEquals(len(spans), 3)

        sorted_spans = sorted(spans, key=lambda x: x.start_time)
        parent_span = get_one_by_operation_name(sorted_spans, 'parent')
        self.assertIsNotNone(parent_span)

        self.assertEquals(parent_span.context.span_id, sorted_spans[1].parent_id)
        self.assertEquals(parent_span.context.span_id, sorted_spans[2].parent_id)
