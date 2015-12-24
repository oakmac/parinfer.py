## This file runs the tests for Parinfer.
## NOTE: this file is pretty quick and dirty
##       it could use some work to be more robust

import json
import unittest2
from parinfer import indent_mode, paren_mode

# load test files
with open('./tests/indent-mode.json') as indent_mode_tests_json:
    INDENT_MODE_TESTS = json.load(indent_mode_tests_json)
with open('./tests/paren-mode.json') as paren_mode_tests_json:
    PAREN_MODE_TESTS = json.load(paren_mode_tests_json)

modeFn = {
  'indent': indent_mode,
  'paren': paren_mode
}

oppositeModeFn = {
  'indent': paren_mode,
  'paren': indent_mode
}

class TestParinfer(unittest2.TestCase):

    def run_test(self, test, mode):
        test_id = test['in']['fileLineNo']
        in_text = '\n'.join(test['in']['lines'])
        expected_text = '\n'.join(test['out']['lines'])

        options = None
        if isinstance(test['in']['cursor'], dict):
            options = test['in']['cursor']

        with self.subTest(test_id):
            out_text = modeFn[mode](in_text, options)['text']
            self.assertEqual(out_text, expected_text)

            out_text2 = modeFn[mode](out_text, options)['text']
            self.assertEqual(out_text2, expected_text, "idempotence")

            if options is None:
                out_text3 = oppositeModeFn[mode](out_text, options)['text']
                self.assertEqual(out_text3, expected_text, "cross-mode preservation")

    def test_indent_mode(self):
        for test in INDENT_MODE_TESTS:
            self.run_test(test, "indent")

    def test_paren_mode(self):
        for test in PAREN_MODE_TESTS:
            self.run_test(test, "paren")

if __name__ == "__main__":
    unittest2.main()
