## Parinfer.py - a Parinfer implementation in Python
## https://github.com/oakmac/parinfer.py

## More information about Parinfer can be found here:
## http://shaunlebron.github.io/parinfer/

## Released under the ISC License:
## https://github.com/oakmac/parinfer.py/blob/master/LICENSE.md

#-------------------------------------------------------------------------------
# Result Structure
#-------------------------------------------------------------------------------

def initial_state():
    """Returns a dictionary of the initial state."""
    return {
        'lines': [],
        'lineNo': -1,
        'ch': '',
        'x': 0,
        'stack': [],
        'backup': [],
        'insert': {'lineNo': None, 'x': None},
        'parenTrail': {'start': None, 'end': None},
        'cursorX': None,
        'cursorLine': None,
        'cursorDx': None,
        'quoteDanger': False,
        'trackIndent': False,
        'cursorInComment': False,
        'quit': False,
        'process': False,
        'success': False,
        'maxIndent': None,
        'indentDelta': 0,
    }

#-------------------------------------------------------------------------------
# String Operations
#-------------------------------------------------------------------------------

def insertString(orig, idx, insert):
    return orig[:idx] + insert + orig[idx:]

def replaceStringRange(orig, start, end, replace):
    return orig[:start] + replace + orig[end:]

def removeStringRange(orig, start, end):
    return orig[:start] + orig[end:]

#-------------------------------------------------------------------------------
# Reader Operations
#-------------------------------------------------------------------------------

MATCHING_PAREN = {
    '{': '}',
    '}': '{',
    '[': ']',
    ']': '[',
    '(': ')',
    ')': '(',
}

def isOpenParen(c):
    return c == "{" or c == "(" or c == "["

def isCloseParen(c):
    return c == "}" or c == ")" or c == "]"

def isWhitespace(c):
    return c == " " or c == "\t" or c== "\n"

#-------------------------------------------------------------------------------
# Stack States
#-------------------------------------------------------------------------------

def peek(stack, i):
    if i is None:
        i = 1
    return stack[len(stack) - i]

def getPrevCh(stack, i):
    e = peek(stack, i)
    return e and e['ch']

def isEscaping(stack):
    return getPrevCh(stack) == '\\'

def prevNonEscCh(stack):
    i = 1
    if isEscaping(stack):
        i = 2
    return getPrevCh(stack, i)

def isInStr(stack):
    return prevNonEscCh(stack) == '"'

def isInComment(stack):
    return prevNonEscCh(stack) == ';'

def isInCode(stack):
    return isInStr(stack) != True and isInComment(stack) != True

def isValidCloser(stack, ch):
    return getPrevCh(stack) == MATCHING_PAREN[ch]

#-------------------------------------------------------------------------------
# Stack Operations
#-------------------------------------------------------------------------------

def pushOpen(result):
    stack = result['stack']
    if isEscaping(stack) == True:
        stack.pop()
        return
    if isInCode(stack) == True:
        stack.append({
            'ch': result['ch'],
            'indentDelta': result['indentDelta'],
            'x': result['x'],
        })

def pushClose(result):
    stack = result['stack']
    if isEscaping(stack) == True:
        stack.pop()
        return

    backup = result['backup']
    ch = result['ch']
    if isInCode(stack) == True:
        if isValidCloser(stack, ch) == True:
            opener = stack.pop()
            result['maxIndent'] = opener['x']
            backup.append(opener)
        else:
            # erase non-matched paren
            result['ch'] = ""

def pushTab(result):
    if isInStr(result['stack']) != True:
        result['ch'] = "  "

def pushSemicolon(result):
    stack = result['stack']
    if isEscaping(stack) == True:
        stack.pop()
        return
    if isInCode(stack) == True:
        stack.append({
            'ch': result['ch'],
            'x': result['x'],
        })

def pushNewline(result):
    stack = result['stack']
    if isEscaping(stack) == True:
        stack.pop()
    if isInComment(stack) == True:
        stack.pop()
    result['ch'] = ""

def pushEscape(result):
    stack = result['stack']
    if isEscaping(stack) == True:
        stack.pop()
    else:
        stack.append({
            'ch': result['ch'],
            'x': result['x'],
        })

def pushQuote(result):
    stack = result['stack']
    if isEscaping(stack) == True or isInStr(stack) == True:
        stack.pop()
        return
    if isInComment(stack) == True:
        result['quoteDanger'] = not result['quoteDanger']
        return
    # default case
    stack.append({
        'ch': result['ch'],
        'x': result['x'],
    })

def pushDefault(result):
    stack = result['stack']
    if isEscaping(stack) == True:
        stack.pop()

def pushChar(result):
    ch = result['ch']
    if isOpenParen(ch) == True:
        pushOpen(result)
        return
    if isCloseParen(ch) == True:
        pushClose(result)
        return
    if ch == '\t':
        pushTab(result)
        return
    if ch == ';':
        pushSemicolon(result)
        return
    if ch == "\n":
        pushNewline(result)
        return
    if ch == "\\":
        pushEscape(result)
        return
    if ch == '"':
        pushQuote(result)
        return
    # default case
    pushDefault(result)

#-------------------------------------------------------------------------------
# Indent Mode Operations
#-------------------------------------------------------------------------------
























#-------------------------------------------------------------------------------
# XYZ
#-------------------------------------------------------------------------------

def finalize_state(state):
    # TODO: write me
    return state

def process_line(state, line):

    return state

def process_text(text, options):
    state = initial_state()

    if options:
        state['cursor_x'] = options['cursor_x']
        state['cursor_line'] = options['cursor_line']

    lines = text.split('\n')
    for line in lines:
        process_line()

    # finalize the result
    state = finalize_state(state)

    # return the state
    return state

def paren_mode(in_text, options):
    # TODO: write Paren Mode
    return in_text;

def indent_mode(in_text, options):
    state = process_text(in_text, options)

    if state['is_valid'] is True:
        out_text = '\n'.join(state['lines'])
    else:
        out_text = in_text

    return {
        'valid': True,
        'text': out_text,
    }
