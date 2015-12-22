## This file runs the tests for Parinfer.

import json
import parinfer.indent_mode
import parinfer.paren_mode

# load test files
with open('./tests/indent-mode.json') as indent_mode_tests_json:
    INDENT_MODE_TESTS = json.load(indent_mode_tests_json)
with open('./tests/paren-mode.json') as paren_mode_tests_json:
    PAREN_MODE_TESTS = json.load(paren_mode_tests_json)

print "Running Indent Mode tests..."
for test in INDENT_MODE_TESTS:
    in_text = '\n'.join(test['in']['lines'])
    out_text = '\n'.join(test['out']['lines'])

    # TODO: need to pass options here
    result = parinfer.indent_mode.format_text(in_text, {})

    print out_text == result['text']
