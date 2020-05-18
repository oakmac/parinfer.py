## This file runs the tests for Parinfer.
## NOTE: this file is pretty quick and dirty
##       it could use some work to be more robust

import json
import unittest
from parinfer import indent_mode, paren_mode

# load test files
with open('./tests/cases/indent-mode.json') as indent_mode_tests_json:
    INDENT_MODE_TESTS = json.load(indent_mode_tests_json)
with open('./tests/cases/paren-mode.json') as paren_mode_tests_json:
    PAREN_MODE_TESTS = json.load(paren_mode_tests_json)

modeFn = {
  'indent': indent_mode,
  'paren': paren_mode
}

oppositeModeFn = {
  'indent': paren_mode,
  'paren': indent_mode
}

class TestParinfer(unittest.TestCase):

    def run_test(self, test, mode):
        # print(test)
        test_id = test['source']['lineNo']
        in_text = test['text']
        expected_text = test['result']['text']
        expected_error = None
        if 'error' in test['result']:
            expected_error = test['result']['error']

        options = None
        if isinstance(test['options'], dict):
            options = test['options']

        # print("options", options)

        with self.subTest(test_id):
            out = modeFn[mode](in_text, options)
            out_text = out['text']

            if expected_error:
                self.assert_error(out, expected_error['name'],
                    expected_error['lineNo'], expected_error['x'])
                # self.check_error()
                # print("result", out)
                # print("expected_error", expected_error)
                # self.assertEqual(out['error'], expected_error)
            else:
                self.assertEqual(out_text, expected_text)

                out_text2 = modeFn[mode](out_text, options)['text']
                self.assertEqual(out_text2, expected_text, "idempotence")

                if options is None:
                    out_text3 = oppositeModeFn[mode](out_text, options)['text']
                    self.assertEqual(out_text3, expected_text, "cross-mode preservation")

    def test_indent_mode(self):
        for test in INDENT_MODE_TESTS:
            # if test['source']['lineNo'] == 118:
                # print("test is",test)
            self.run_test(test, "indent")

    # def test_paren_mode(self):
    #     for test in PAREN_MODE_TESTS:
    #         self.run_test(test, "paren")

    def assert_error(self, result, error_name, line_no, x):
        self.assertEqual(result['success'], False)
        self.assertEqual(result['error']['name'], error_name)
        self.assertEqual(result['error']['lineNo'], line_no)
        self.assertEqual(result['error']['x'], x)

    def check_error(self, mode, text, error_name, line_no, x):
        result = modeFn[mode](text, None);
        self.assert_error(result, error_name, line_no, x)

    # def test_errors(self):
    #     self.check_error('indent', '(foo"', "unclosed-quote", 0, 4)
    #     self.check_error('paren', '(foo"', "unclosed-quote", 0, 4)
    #     self.check_error('paren', '(foo', "unclosed-paren", 0, 0)
    #     self.check_error('paren', '; "foo', "quote-danger", 0, 2)
    #     self.check_error('paren', '(foo \\', "eol-backslash", 0, 5)
    #     self.check_error('paren', '(foo]\nbar)', "unmatched-close-paren", 0, 4)

    # def check_changed_lines(self, mode, text, changed_lines):
    #     result = modeFn[mode](text, None)
    #     print(result)
    #     self.assertEqual(result['changedLines'], changed_lines)

    # def check_result(self, mode, text, expected_text):
    #     result = modeFn[mode](text, None)
    #     # print(result)
    #     self.assertEqual(result['text'], expected_text)

    # def test_sanity(self):
    #     self.check_result('indent', "(foo\nbar", "(foo)\nbar")
    #     self.check_result('indent', "(foo\nbar)", "(foo)\nbar")
    #     self.check_result('paren', "(foo\nbar)", "(foo\n bar)")
    #     # self.check_result('paren', "(foo]\nbar)", "(foo\n bar)")

if __name__ == "__main__":
    unittest.main()
