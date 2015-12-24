## This file runs the tests for Parinfer.

import json
from parinfer import indent_mode, paren_mode

# load test files
with open('./tests/indent-mode.json') as indent_mode_tests_json:
    INDENT_MODE_TESTS = json.load(indent_mode_tests_json)
with open('./tests/paren-mode.json') as paren_mode_tests_json:
    PAREN_MODE_TESTS = json.load(paren_mode_tests_json)

def run_indent_mode_test(test):
    test_id = test['in']['file-line-no']
    in_text = '\n'.join(test['in']['lines'])
    out_text = '\n'.join(test['out']['lines'])

    # TODO: need to pass options here
    result = indent_mode(in_text, None)

    if result['success'] != True:
        print "Test " + str(test_id) + " FAILED (parinfer failure)"
    elif result['success'] == True and result['text'] == out_text:
        print "Test " + str(test_id) + " was a success."
    else:
        print "Test " + str(test_id) + " FAILED (out text did not match)"

print "Running Indent Mode tests..."
for test in INDENT_MODE_TESTS:
    run_indent_mode_test(test)

#run_indent_mode_test(INDENT_MODE_TESTS[7])
