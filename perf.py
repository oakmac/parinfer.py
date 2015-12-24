import time
from parinfer import indent_mode, paren_mode

def timeProcess(string, options):
  numlines = len(string.splitlines())
  print "Testing file with", numlines, "lines"

  t = time.clock()
  indent_mode(string, options)
  dt = time.clock() - t
  print "Indent Mode:", dt, "s"

  t = time.clock()
  paren_mode(string, options)
  dt = time.clock() - t
  print "Paren Mode:", dt, "s"

with open('tests/really_long_file.clj', 'r') as f:
    text = f.read()

timeProcess(text, {})
