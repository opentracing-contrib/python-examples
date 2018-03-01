# python-examples
Tester examples of common instrumentation patterns.

## Build and test.

```
tox
```

For running indivudual tests, upon installing the dependencies:

```
py.test -s tests/test_nested_callbacks/test_tornado.py
```

## Status

Currently the examples cover threads, Tornado, Gevent and Asyncio (which requires Python 3).
