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

    def check_error(self, mode, text, error_name, line_no, x):
        result = modeFn[mode](text, None);
        self.assertEqual(result['success'], False)
        self.assertEqual(result['error']['name'], error_name)
        self.assertEqual(result['error']['lineNo'], line_no)
        self.assertEqual(result['error']['x'], x)

    def test_errors(self):
        self.check_error('indent', '(foo"', "unclosed-quote", 0, 4)
        self.check_error('paren', '(foo"', "unclosed-quote", 0, 4)
        self.check_error('paren', '(foo', "unclosed-paren", 0, 0)
        self.check_error('paren', '; "foo', "quote-danger", 0, 2)
        self.check_error('paren', '(foo \\', "eol-backslash", 0, 5)

    def check_changed_lines(self, mode, text, changed_lines):
        result = modeFn[mode](text, None)
        self.assertEqual(result['changedLines'], changed_lines)

    def test_changed_lines(self):
        self.check_changed_lines('indent', "(foo\nbar", [{'lineNo': 0, 'line': '(foo)'}])
        self.check_changed_lines('indent', "(foo\nbar)", [{'lineNo': 0, 'line': '(foo)'},
                                                     {'lineNo': 1, 'line': 'bar'}])
        self.check_changed_lines('paren', "(foo\nbar)", [{'lineNo': 1, 'line': ' bar)'}])
        self.check_changed_lines('paren', "(foo]\nbar)", [{'lineNo': 0, 'line': '(foo'},
                                                     {'lineNo': 1, 'line': ' bar)'}])

if __name__ == "__main__":
    unittest2.main()
