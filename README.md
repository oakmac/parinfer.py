# Parinfer for Python [![Build Status](https://travis-ci.org/oakmac/parinfer.py.svg?branch=master)](https://travis-ci.org/oakmac/parinfer.py)

A [Parinfer] implementation written in Python.

## About

There are several text editors where Python is the best - or only - choice for
extensions. Having a Parinfer implementation in Python allows Parinfer to reach
more editors.

This is basically a 1-to-1 copy of [parinfer.js].

The `.json` files in the [tests] folder are copied directly from the [main
Parinfer repo].

## Run Tests

```sh
python3 tests.py
```

To run a performance stress test:

```
python3 perf.py
```

To profile those performance stress tests:

```
python3 -m cProfile -s time perf.py
```

## License

[ISC license](LICENSE.md)

[Parinfer]:http://shaunlebron.github.io/parinfer/
[parinfer.js]:https://github.com/parinfer/parinfer.js
[tests]:tests/
[main Parinfer repo]:https://github.com/parinfer/parinfer.js/tree/master/test/cases
