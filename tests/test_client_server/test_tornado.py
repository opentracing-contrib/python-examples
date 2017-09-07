from __future__ import print_function

import unittest

from tornado import gen, ioloop, queues
import opentracing
from opentracing.ext import tags

from ..opentracing_mock import MockTracer
from ..utils import get_logger, get_one_by_tag
from ..utils_tornado import run_until


logger = get_logger(__name__)


class Server(object):
    def __init__(self, *args, **kwargs):
        tracer = kwargs.pop('tracer')
        queue = kwargs.pop('queue')
        super(Server, self).__init__(*args, **kwargs)

        self.tracer = tracer
        self.queue = queue

    @gen.coroutine
    def run(self):
        value = yield self.queue.get()
        self.process(value)

    def process(self, message):
        logger.info('Processing message in server')

        ctx = self.tracer.extract(opentracing.Format.TEXT_MAP, message)
        with self.tracer.start_span('receive', child_of=ctx) as span:
            span.set_tag(tags.SPAN_KIND, tags.SPAN_KIND_RPC_SERVER)


class Client(object):
    def __init__(self, tracer, queue):
        self.tracer = tracer
        self.queue = queue

    @gen.coroutine
    def send(self):
        with self.tracer.start_span('send') as span:
            span.set_tag(tags.SPAN_KIND, tags.SPAN_KIND_RPC_CLIENT)

            message = {}
            self.tracer.inject(span.context,
                               opentracing.Format.TEXT_MAP,
                               message)
            yield self.queue.put(message)

        logger.info('Sent message from client')


class TestTornado(unittest.TestCase):
    def setUp(self):
        self.tracer = MockTracer()
        self.queue = queues.Queue()
        self.loop = ioloop.IOLoop.current()
        self.server = Server(tracer=self.tracer, queue=self.queue)

    def test(self):
        client = Client(self.tracer, self.queue)
        self.loop.add_callback(self.server.run)
        self.loop.add_callback(client.send)

        run_until(self.loop, lambda: len(self.tracer.finished_spans) >= 2)
        self.loop.start()

        spans = self.tracer.finished_spans
        self.assertIsNotNone(get_one_by_tag(spans,
                                            tags.SPAN_KIND,
                                            tags.SPAN_KIND_RPC_SERVER))
        self.assertIsNotNone(get_one_by_tag(spans,
                                            tags.SPAN_KIND,
                                            tags.SPAN_KIND_RPC_CLIENT))
