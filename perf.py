import cProfile
import os
import time

from parinfer import indent_mode, paren_mode, smart_mode

def timeProcess(name, string, options):
    numlines = len(string.splitlines())
    numchars = len(string)
    print("Processing", name, ":", numlines, "lines", numchars, "chars")

    t = time.perf_counter()
    indent_mode(string, options)
    dt = (time.perf_counter() - t) * 1000
    print("indent:", '{:.3f}'.format(dt), "ms")

    t = time.perf_counter()
    paren_mode(string, options)
    dt = (time.perf_counter() - t) * 1000
    print("paren:", '{:.3f}'.format(dt), "ms")

    t = time.perf_counter()
    smart_mode(string, options)
    dt = (time.perf_counter() - t) * 1000
    print("smart:", '{:.3f}'.format(dt), "ms")

    print()

    # cProfile.runctx("indent_mode(string, options)", globals(), locals())
    # cProfile.runctx("paren_mode(string, options)", globals(), locals())

perfDir = 'tests/perf'
for file in os.listdir(perfDir):
    with open(os.path.join(perfDir, file), 'r') as f:
        text = f.read()
    if text:
        timeProcess(file, text, {})
    else:
        print("error: could not open:",file)
