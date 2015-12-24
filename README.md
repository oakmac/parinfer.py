# Parinfer for Python

A [Parinfer] implementation written in Python.

## About

There are several text editors where Python is the best - or only - choice for
extensions. Having a Parinfer implementation in Python allows Parinfer to reach
more editors.

This is basically a 1-to-1 copy of [parinfer.js].

The `.json` files in the [tests] folder are copied directly from the [main
Parinfer repo].

I am a very novice Python developer. There is likely lots of room for
improvement in this implementation. PR's welcome :)

## Run Tests

```sh
sudo pip install unittest2
python tests.py
```

To run a performance stress test:

```
python perf.js
```

## License

[ISC license]

[Parinfer]:http://shaunlebron.github.io/parinfer/
[parinfer.js]:https://github.com/shaunlebron/parinfer/blob/master/lib/parinfer.js
[tests]:tests/
[main Parinfer repo]:https://github.com/shaunlebron/parinfer/tree/master/lib/test/cases
[ISC License]:LICENSE.md
