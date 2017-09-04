from __future__ import print_function

import logging
import threading
import time


class RefCount(object):
    def __init__(self, count=1):
        self._lock = threading.Lock()
        self._count = count

    def incr(self):
        with self._lock:
            self._count += 1
            return self._count

    def decr(self):
        with self._lock:
            self._count -= 1
            return self._count


def await_until(func, timeout):
    end_time = time.time() + timeout
    while time.time() < end_time and not func():
        time.sleep(0.01)


def get_logger(name):
    logging.basicConfig(level=logging.INFO)
    return logging.getLogger(name)

def get_one_by_tag(spans, key, value):
    found = []
    for span in spans:
        if span.tags.get(key) == value:
            found.append(span)

    if len(found) > 1:
        raise RuntimeError('Too many values')

    return found[0] if len(found) > 0 else None

def get_one_by_operation_name(spans, name):
    found = []
    for span in spans:
        if span.operation_name == name:
            found.append(span)

    if len(found) > 1:
        raise RuntimeError('Too many values')

    return found[0] if len(found) > 0 else None
