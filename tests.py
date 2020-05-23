## This file runs the tests for Parinfer.
## NOTE: this file is pretty quick and dirty
##       it could use some work to be more robust

import json
import unittest
from parinfer import indent_mode, paren_mode, smart_mode

# load test files
with open('./tests/cases/indent-mode.json') as indent_mode_tests_json:
    INDENT_MODE_TESTS = json.load(indent_mode_tests_json)
with open('./tests/cases/paren-mode.json') as paren_mode_tests_json:
    PAREN_MODE_TESTS = json.load(paren_mode_tests_json)
with open('./tests/cases/smart-mode.json') as smart_mode_tests_json:
    SMART_MODE_TESTS = json.load(smart_mode_tests_json)

modeFn = {
    'indent': indent_mode,
    'paren': paren_mode,
    'smart': smart_mode,
}

crossModeFn = {
    'indent': paren_mode,
    'paren': indent_mode,
    'smart': paren_mode,
}

class TestParinfer(unittest.TestCase):

    def assertStructure(self, actual, expected):
        self.assertEqual(actual['text'], expected['text'])
        self.assertEqual(actual['success'], expected['success'])

        if 'cursorX' in expected:
            self.assertEqual(actual['cursorX'], expected['cursorX'])
        if 'cursorLine' in expected:
            self.assertEqual(actual['cursorLine'], expected['cursorLine'])

        self.assertEqual('error' in actual, 'error' in expected)
        if 'error' in actual:
            # NOTE: we currently do not test 'message' and 'extra'
            self.assertEqual(actual['error']['name'], expected['error']['name'])
            self.assertEqual(actual['error']['lineNo'], expected['error']['lineNo'])
            self.assertEqual(actual['error']['x'], expected['error']['x'])

        if 'tabStops' in expected:
            self.assertEqual(actual['tabStops'] is None, False)
            self.assertEqual(len(actual['tabStops']), len(expected['tabStops']))
            for i in range(len(actual['tabStops'])):
                if 'lineNo' in expected['tabStops'][i]:
                    self.assertEqual(actual['tabStops'][i]['lineNo'], expected['tabStops'][i]['lineNo'])
                if 'x' in expected['tabStops'][i]:
                    self.assertEqual(actual['tabStops'][i]['x'], expected['tabStops'][i]['x'])
                if 'ch' in expected['tabStops'][i]:
                    self.assertEqual(actual['tabStops'][i]['ch'], expected['tabStops'][i]['ch'])
                if 'argX' in expected['tabStops'][i]:
                    self.assertEqual(actual['tabStops'][i]['argX'], expected['tabStops'][i]['argX'])

        if 'parenTrails' in expected:
            self.assertEqual(actual['parenTrails'], expected['parenTrails'])

    def run_test(self, case, mode):
        test_id = mode + ": " + str(case['source']['lineNo'])

        expected = case['result']
        text = case['text']
        options = {}
        if isinstance(case['options'], dict) and 'options' in case:
            options = case['options']

        with self.subTest(test_id):
            actual = modeFn[mode](text, options)
            self.assertStructure(actual, expected)

            # TODO: ?
            if 'parenTrails' in actual:
                del actual['parenTrails']

            if ('error' in expected
                    or 'tabStops' in expected
                    or 'parenTrails' in expected
                    or ('options' in expected and 'changes' in expected['options'])):
                return

            with self.subTest(test_id + " idempotence"):
                options2 = {}
                if 'cursorX' in actual:
                    options2['cursorX'] = actual['cursorX']
                if 'cursorLine' in actual:
                    options2['cursorLine'] = actual['cursorLine']
                actual2 = modeFn[mode](actual['text'], options2)
                self.assertStructure(actual2, actual)

            with self.subTest(test_id + " cross-mode check"):
                if 'cursorX' not in expected:
                    actual3 = crossModeFn[mode](actual['text'], None)
                    self.assertStructure(actual3, actual)

    def test_indent_mode(self):
        for test in INDENT_MODE_TESTS:
            self.run_test(test, "indent")

    def test_paren_mode(self):
        for test in PAREN_MODE_TESTS:
            self.run_test(test, "paren")

    def test_smart_mode(self):
        for test in SMART_MODE_TESTS:
            self.run_test(test, 'smart')

    def assert_error(self, result, error_name, line_no, x):
        self.assertEqual(result['success'], False)
        self.assertEqual(result['error']['name'], error_name)
        self.assertEqual(result['error']['lineNo'], line_no)
        self.assertEqual(result['error']['x'], x)

    def check_error(self, mode, text, error_name, line_no, x):
        result = modeFn[mode](text, None);
        self.assert_error(result, error_name, line_no, x)

    def test_errors(self):
        self.check_error('indent', '(foo"', "unclosed-quote", 0, 4)
        self.check_error('paren', '(foo"', "unclosed-quote", 0, 4)
        self.check_error('paren', '(foo', "unclosed-paren", 0, 0)
        self.check_error('paren', '; "foo', "quote-danger", 0, 2)
        self.check_error('paren', '(foo \\', "eol-backslash", 0, 5)
        self.check_error('paren', '(foo]\nbar)', "unmatched-close-paren", 0, 4)

    # def check_changed_lines(self, mode, text, changed_lines):
    #     result = modeFn[mode](text, None)
    #     # print(result)
    #     self.assertEqual(result['changedLines'], changed_lines)

    def check_result(self, mode, text, expected_text):
        result = modeFn[mode](text, None)
        self.assertEqual(result['text'], expected_text)

    def test_sanity(self):
        self.check_result('indent', "(foo\nbar", "(foo)\nbar")
        self.check_result('indent', "(foo\nbar)", "(foo)\nbar")
        self.check_result('paren', "(foo\nbar)", "(foo\n bar)")
        # self.check_result('paren', "(foo]\nbar)", "(foo\n bar)")

if __name__ == "__main__":
    unittest.main()
