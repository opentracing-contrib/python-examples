# python-examples
Tester examples of common instrumentation patterns.

## Build and test.

```sh
tox
```

For running indivudual tests, upon installing the dependencies:

```py
py.test -s tests/test_nested_callbacks/test_tornado.py
```

## Status

Currently the examples cover **threads**, **tornado**, **gevent** and **asyncio** (which requires Python 3). The implementations of `ScopeManager` for each is a basic, simple one, used to demonstrate the usage for each platform. See details below.

### threading

`ThreadScopeManager` uses thread-local storage (through `threading.local()`), and does not provide automatic propagation from thread to thread, which needs to be done manually.

### gevent

`GeventScopeManager` uses greenlet-local storage (through `gevent.local.local()`), and does not provide automatic propagation from parent greenlets to their children, which needs to be done manually.

### Tornado

`TornadoScopeManager` uses a variation of `tornado.stack_context.StackContext` to both store and automatically propagate the context from parent coroutines to their children. 

Because of this, in order to make the `TornadoScopeManager` work, calls need to be started like this:

```py
with TracedStackContext():
   my_coroutine()
```

At the moment of writing this, `yield`ing over multiple children is not supported, as the context is effectively shared and switching from coroutine to coroutine messes up the current active `Span`.

### asyncio

`AsyncioScopeManager` uses the current `Task` (through `Task.current_task()`) to store the active `Span`, and does not provide automatic propagation from parent `Task`s to their children, which needs to be done manually.
