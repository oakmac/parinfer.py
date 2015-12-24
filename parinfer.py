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

def closeParens(result, indentX):
    if indentX == None:
        indentX = 0

    stack = result['stack']
    parens = ""

    while len(stack) > 0:
        opener = peek(stack)
        if opener['x'] >= indentX:
            stack.pop()
            parens = parens + MATCHING_PAREN[opener['ch']]
        else:
            break

    insertLineNo = result['insert']['lineNo']
    newString = insertString(result['lines'][insertLineNo],
                             result['insert']['x'],
                             parens)
    result['lines'][insertLineNo] = newString

def updateParenTrail(result):
    ch = result['ch']
    shouldPass = bool(ch == ';' or
                      ch == ',' or
                      isWhitespace(ch) or
                      isCloseParen(ch))

    stack = result['stack']
    shouldReset = bool(isInCode(stack) and
                       (isEscaping(stack) or shouldPass != True))

    result['isCursorInComment'] = bool(result['isCursorInComment'] or
                                       (result['cursorLine'] == result['lineNo'] and
                                        result['x'] == result['cursorX'] and
                                        isInComment(stack)))

    shouldUpdate = bool(isInCode(stack) and
                        isEscaping(stack) != True and
                        isCloseParen(ch) and
                        isValidCloser(stack, ch))

    if shouldReset:
        result['backup'] = []
        result['parenTrail'] = {}
        result['maxIndent'] = None
    elif shouldUpdate:
        if result['parenTrail']['start'] == None:
            result['parenTrail']['start'] = result['x']
        result['parenTrail']['end'] = result['x'] + 1

def blockParenTrail(result):
    start = result['parenTrail']['start']
    end = result['parenTrail']['end']
    isCursorBlocking = bool(result['lineNo'] == result['cursorLine'] and
                            start != None and
                            result['cursorX'] > start and
                            result['isCursorInComment'] != True)

    if start != None and isCursorBlocking:
        start = max(start, result['cursorX'])

    if end != None and isCursorBlocking:
        end = max(end, result['cursorX'])

    if start == end:
        start = None
        end = None

    result['parenTrail']['start'] = start
    result['parenTrail']['end'] = end

def removeParenTrail(result):
    start = result['parenTrail']['start']
    end = result['parenTrail']['end']

    if start == None or end == None:
        return

    stack = result['stack']
    backup = result['backup']

    line = result['lines'][result['lineNo']]
    removeCount = 0
    for i in range(start, end):
        if isCloseParen(line[i]):
            removeCount = removeCount + 1

    ignoreCount = backup['length'] - removeCount
    while ignoreCount != len(backup['length']):
        stack.append(backup.pop())

    result['lines'][result['lineNo']] = removeStringRange(line, start, end)

    if result['insert']['lineNo'] == result['lineNo']:
        result['insert']['x'] = min(result['insert']['x'], start)

def updateInsertionPt(result):
    line = result['lines'][result['lineNo']]
    prevCh = line[result['x'] - 1]
    ch = result['ch']

    shouldInsert = bool(isInCode(result.stack) and
                        ch != "" and
                        (isWhitespace(ch) != True or prevCh == "\\") and
                        (isCloseParen(ch) != True or result['lineNo'] == result['cursorLine']))

    if shouldInsert:
        result['insert'] = {
            'lineNo': result['lineNo'],
            'x': result['x'] + 1,
        }

def processIndentTrigger(result):
    return None

def processIndent(result):
    return None

def updateLine(result, origCh):
    return None

def processChar(result, ch):
    return None

def processLine(result, line):
    return None

def finalizeResult(result):
    return None

def processText(text, options):
    return None

def formatText(text, options):
    return None

#-------------------------------------------------------------------------------
# Paren Mode Operations
#-------------------------------------------------------------------------------

# def finalize_state(state):
#     # TODO: write me
#     return state
#
# def process_line(state, line):
#
#     return state
#
# def process_text(text, options):
#     state = initial_state()
#
#     if options:
#         state['cursor_x'] = options['cursor_x']
#         state['cursor_line'] = options['cursor_line']
#
#     lines = text.split('\n')
#     for line in lines:
#         process_line()
#
#     # finalize the result
#     state = finalize_state(state)
#
#     # return the state
#     return state

#-------------------------------------------------------------------------------
# Public API
#-------------------------------------------------------------------------------

# def indent_mode(in_text, options):
#     state = process_text(in_text, options)
#
#     if state['is_valid'] is True:
#         out_text = '\n'.join(state['lines'])
#     else:
#         out_text = in_text
#
#     return {
#         'valid': True,
#         'text': out_text,
#     }
#
# def paren_mode(in_text, options):
#     # TODO: write Paren Mode
#     return in_text;
