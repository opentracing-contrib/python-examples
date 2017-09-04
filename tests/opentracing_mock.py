import threading
import time

import basictracer


class MockRecorder(basictracer.SpanRecorder):
    def __init__(self, tracer):
        self.tracer = tracer
        self._lock = threading.Lock()

    def record_span(self, span):
        with self._lock:
            span.finish_time = time.time()
            self.tracer.finished_spans.append(span)


class MockTracer(basictracer.BasicTracer):
    def __init__(self):
        super(MockTracer, self).__init__(MockRecorder(self))
        self.finished_spans = []
        self.register_required_propagators()

    def reset(self):
        self.finished_spans = []
        self.extracted_headers = []
