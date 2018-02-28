import threading
import gevent.local
import six

if six.PY3:
    import asyncio

from opentracing import ScopeManager, Scope


class AsyncioScopeManager(ScopeManager):
    def activate(self, span, finish_on_close):
        scope = AsyncioScope(self, span, finish_on_close)

        loop = asyncio.get_event_loop()
        task = asyncio.Task.current_task(loop=loop)
        setattr(task, '__active', scope)

        return scope

    def _get_current_task(self):
        loop = asyncio.get_event_loop()
        return asyncio.Task.current_task(loop=loop)

    @property
    def active(self):
        task = self._get_current_task()
        return getattr(task, '__active', None)


class AsyncioScope(Scope):
    def __init__(self, manager, span, finish_on_close):
        super(AsyncioScope, self).__init__(manager, span)
        self._finish_on_close = finish_on_close
        self._to_restore = manager.active

    def close(self):
        if self._manager.active is not self:
            return

        task = self._manager._get_current_task()
        setattr(task, '__active', self._to_restore)

        if self._finish_on_close:
            self.span.finish()


class GeventScopeManager(ScopeManager):
    def __init__(self):
        self._locals = gevent.local.local()

    def activate(self, span, finish_on_close):
        scope = GeventScope(self, span, finish_on_close)
        setattr(self._locals, 'active', scope)

        return scope

    @property
    def active(self):
        return getattr(self._locals, 'active', None)


class GeventScope(Scope):
    def __init__(self, manager, span, finish_on_close):
        super(GeventScope, self).__init__(manager, span)
        self._finish_on_close = finish_on_close
        self._to_restore = manager.active

    def close(self):
        if self._manager.active is not self:
            return

        setattr(self._manager._locals, 'active', self._to_restore)

        if self._finish_on_close:
            self.span.finish()


class TornadoScopeManager(ScopeManager):
    def activate(self, span, finish_on_close):
        scope = TornadoScope(self, span, finish_on_close)
        data = self._get_context_data()
        data['active'] = scope

        return scope

    def _get_context_data(self):
        data = TracerStackContext.current_data()
        if data is None:
            raise Exception('Not under TracerStackContext')

        return data

    @property
    def active(self):
        data = TracerStackContext.current_data()
        if data is None:
            return None

        return data.get('active', None)


class TornadoScope(Scope):
    def __init__(self, manager, span, finish_on_close):
        super(TornadoScope, self).__init__(manager, span)
        self._finish_on_close = finish_on_close
        self._to_restore = manager.active

    def close(self):
        data = self._manager._get_context_data()
        if data.get('active', None) is not self:
            return

        data['active'] = self._to_restore

        if self._finish_on_close:
            self.span.finish()


from tornado.stack_context import StackContextInconsistentError, _state, wrap

class TracerStackContext(object):
    """A context manager that can be used to persist local states.
    It must be used everytime a Tornado's handler or coroutine is traced.
    It is meant to work like a traditional ``StackContext``, preserving the
    state across asynchronous calls.

    A Span attached to a ``TracerStackContext`` is shared between
    different threads.

    This simple implementation follows the suggestions provided here:
    https://github.com/tornadoweb/tornado/issues/1063
    """
    def __init__(self):
        self.active = True
        self.data = {}

    def enter(self):
        """Required to preserve the ``StackContext`` interface"""
        pass

    def exit(self, type, value, traceback):
        """Required to preserve the ``StackContext`` interface"""
        pass

    def __enter__(self):
        self.old_contexts = _state.contexts
        self.new_contexts = (self.old_contexts[0] + (self,), self)
        _state.contexts = self.new_contexts
        return self

    def __exit__(self, type, value, traceback):
        final_contexts = _state.contexts
        _state.contexts = self.old_contexts

        if final_contexts is not self.new_contexts:
            raise StackContextInconsistentError(
                'stack_context inconsistency (may be caused by yield '
                'within a "with TracerStackContext" block)')

        # break the reference to allow faster GC on CPython
        self.new_contexts = None

    def deactivate(self):
        self.active = False

    @classmethod
    def wrap(self, fn):
        return wrap(fn)

    @classmethod
    def current_data(cls):
        """Return the data for the current context. This method can be
        used inside a Tornado coroutine to retrieve and use the current
        tracing context.
        """
        for ctx in reversed(_state.contexts[0]):
            if isinstance(ctx, cls) and ctx.active:
                return ctx.data
