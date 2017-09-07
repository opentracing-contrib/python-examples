from __future__ import print_function

from opentracing.ext import tags

from ..utils import get_logger


logger = get_logger(__name__)


class RequestHandler(object):
    def __init__(self, tracer, context=None):
        self.tracer = tracer
        self.context = context

    def before_request(self, request, request_context):
        logger.info('Before request %s' % request)

        span = self.tracer.start_span('send', child_of=self.context)
        span.set_tag(tags.SPAN_KIND, tags.SPAN_KIND_RPC_CLIENT)

        request_context['span'] = span

    def after_request(self, request, request_context):
        logger.info('After request %s' % request)

        span = request_context.get('span')
        if span is not None:
            span.finish()
