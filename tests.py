## This file runs the tests for Parinfer.

import json
from parinfer import indent_mode, paren_mode

# load test files
with open('./tests/indent-mode.json') as indent_mode_tests_json:
    INDENT_MODE_TESTS = json.load(indent_mode_tests_json)
with open('./tests/paren-mode.json') as paren_mode_tests_json:
    PAREN_MODE_TESTS = json.load(paren_mode_tests_json)

def run_test(test, parinfer_fn):
    test_id = test['in']['file-line-no']
    in_text = '\n'.join(test['in']['lines'])
    out_text = '\n'.join(test['out']['lines'])

    options = None
    if isinstance(test['in']['cursor'], dict):
        options = {}
        if 'cursor-dx' in test['in']['cursor']:
            options['cursorDx'] = test['in']['cursor']['cursor-dx']
        if 'cursor-line' in test['in']['cursor']:
            options['cursorLine'] = test['in']['cursor']['cursor-line']
        if 'cursor-x' in test['in']['cursor']:
            options['cursorX'] = test['in']['cursor']['cursor-x']

    result = parinfer_fn(in_text, options)

    if result['text'] == out_text:
        print "Test " + str(test_id) + " was a success."
    else:
        print "Test " + str(test_id) + " FAILED (out text did not match)"

print "Running Indent Mode tests..."
for test in INDENT_MODE_TESTS:
    run_test(test, indent_mode)

print "Running Paren Mode tests..."
for test in PAREN_MODE_TESTS:
    run_test(test, paren_mode)
