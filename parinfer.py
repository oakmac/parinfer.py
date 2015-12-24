## Parinfer.py - a Parinfer implementation in Python
## https://github.com/oakmac/parinfer.py

## More information about Parinfer can be found here:
## http://shaunlebron.github.io/parinfer/

## Released under the ISC License:
## https://github.com/oakmac/parinfer.py/blob/master/LICENSE.md










### DEBUG: remove this

import json

def print_r(x):
    print json.dumps(x, sort_keys=True, indent=2, separators=(',', ': '))
    print "~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"

### END DEBUG










#-------------------------------------------------------------------------------
# Result Structure
#-------------------------------------------------------------------------------

def initialResult():
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
# Constants
#-------------------------------------------------------------------------------

BACKSLASH = '\\'
COMMA = ','
DOUBLE_QUOTE = '"'
NEWLINE = '\n'
SEMICOLON = ';'
TAB = '\t'

MATCHING_PAREN = {
    '{': '}',
    '}': '{',
    '[': ']',
    ']': '[',
    '(': ')',
    ')': '(',
}

#-------------------------------------------------------------------------------
# Reader Operations
#-------------------------------------------------------------------------------

def isOpenParen(c):
    return c == "{" or c == "(" or c == "["

def isCloseParen(c):
    return c == "}" or c == ")" or c == "]"

def isWhitespace(c):
    return c == " " or c == TAB or c== NEWLINE

#-------------------------------------------------------------------------------
# Stack States
#-------------------------------------------------------------------------------

def peek(stack, i):
    if i is None:
        i = 1
    try:
        return stack[len(stack) - i]
    except IndexError:
        return None

def getPrevCh(stack, i):
    e = peek(stack, i)
    if e == None:
        return None
    else:
        return e['ch']

def isEscaping(stack):
    return getPrevCh(stack, None) == BACKSLASH

def prevNonEscCh(stack):
    i = 1
    if isEscaping(stack):
        i = 2
    return getPrevCh(stack, i)

def isInStr(stack):
    return prevNonEscCh(stack) == DOUBLE_QUOTE

def isInComment(stack):
    return prevNonEscCh(stack) == SEMICOLON

def isInCode(stack):
    return isInStr(stack) != True and isInComment(stack) != True

def isValidCloser(stack, ch):
    return getPrevCh(stack, None) == MATCHING_PAREN[ch]

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
    if ch == TAB:
        pushTab(result)
        return
    if ch == SEMICOLON:
        pushSemicolon(result)
        return
    if ch == NEWLINE:
        pushNewline(result)
        return
    if ch == BACKSLASH:
        pushEscape(result)
        return
    if ch == DOUBLE_QUOTE:
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
        opener = peek(stack, None)
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
    shouldPass = bool(ch == SEMICOLON or
                      ch == COMMA or
                      isWhitespace(ch) or
                      isCloseParen(ch))

    stack = result['stack']
    shouldReset = bool(isInCode(stack) and
                       (isEscaping(stack) or shouldPass != True))

    result['cursorInComment'] = bool(result['cursorInComment'] or
                                     (result['cursorLine'] == result['lineNo'] and
                                      result['x'] == result['cursorX'] and
                                      isInComment(stack)))

    shouldUpdate = bool(isInCode(stack) and
                        isEscaping(stack) != True and
                        isCloseParen(ch) and
                        isValidCloser(stack, ch))

    if shouldReset:
        result['backup'] = []
        result['parenTrail'] = {'start': None, 'end': None}
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
                            result['cursorInComment'] != True)

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

    ignoreCount = len(backup) - removeCount
    while ignoreCount != len(backup):
        stack.append(backup.pop())

    result['lines'][result['lineNo']] = removeStringRange(line, start, end)

    if result['insert']['lineNo'] == result['lineNo']:
        result['insert']['x'] = min(result['insert']['x'], start)

def updateInsertionPt(result):
    line = result['lines'][result['lineNo']]
    try:
        prevCh = line[result['x'] - 1]
    except IndexError:
        prevCh = None
    ch = result['ch']

    shouldInsert = bool(isInCode(result['stack']) and
                        ch != "" and
                        (isWhitespace(ch) != True or prevCh == BACKSLASH) and
                        (isCloseParen(ch) != True or result['lineNo'] == result['cursorLine']))

    if shouldInsert:
        result['insert'] = {
            'lineNo': result['lineNo'],
            'x': result['x'] + 1,
        }

def processIndentTrigger(result):
    closeParens(result, result['x'])
    result['trackIndent'] = False

def processIndent(result):
    stack = result['stack']
    ch = result['ch']
    checkIndent = bool(result['trackIndent'] and
                       isInCode(stack) and
                       isWhitespace(ch) != True and
                       ch != SEMICOLON)
    skip = bool(checkIndent and isCloseParen(ch))
    atIndent = bool(checkIndent and skip != True)
    quit = bool(atIndent and result['quoteDanger'])

    result['quit'] = quit
    result['process'] = bool(skip != True and quit != True)

    if atIndent and quit != True:
        processIndentTrigger(result)

def updateLine(result, origCh):
    ch = result['ch']
    if origCh != ch:
        lineNo = result['lineNo']
        line = result['lines'][lineNo]
        result['lines'][lineNo] = replaceStringRange(line, result['x'], result['x'] + len(origCh), ch)

def processChar(result, ch):
    origCh = ch
    result['ch'] = ch
    processIndent(result)

    if result['quit']:
        return

    if result['process']:
        # NOTE: the order here is important!
        updateParenTrail(result)
        pushChar(result)
        updateInsertionPt(result)
    else:
        result['ch'] = ""

    updateLine(result, origCh)
    result['x'] = result['x'] + len(result['ch'])

def processLine(result, line):
    stack = result['stack']

    result['lineNo'] = result['lineNo'] + 1
    result['backup'] = []
    result['cursorInComment'] = False
    result['parenTrail'] = {'start': None, 'end': None}
    result['trackIndent'] = bool(len(stack) > 0 and isInStr(stack) != True)
    result['lines'].append(line)
    result['x'] = 0

    chars = line + NEWLINE
    for ch in chars:
        processChar(result, ch)
        if result['quit']:
            break

    if result['quit'] == False:
        blockParenTrail(result)
        removeParenTrail(result)

def finalizeResult(result):
    stack = result['stack']
    result['success'] = bool(isInStr(stack) != True and
                             result['quoteDanger'] != True)
    if result['success'] and len(stack) > 0:
        closeParens(result, None)

def processText(text, options):
    result = initialResult()

    if options:
        result['cursorX'] = options['cursorX']
        result['cursorLine'] = options['cursorLine']

    lines = text.split(NEWLINE)
    for line in lines:
        processLine(result, line)
        if result['quit']:
            break

    finalizeResult(result)
    return result

def formatText(text, options):
    result = processText(text, options)
    outText = text
    if result['success']:
        outText = NEWLINE.join(result['lines'])
    return {
        'text': outText,
        'success': result['success'],
    }

#-------------------------------------------------------------------------------
# Paren Mode Operations
# NOTE: Paren Mode re-uses some Indent Mode functions
#-------------------------------------------------------------------------------

def appendParenTrail(result):
    opener = result['stack'].pop()
    closeCh = MATCHING_PAREN[opener['ch']]
    result['maxIndent'] = opener['x']
    idx = result['insert']['lineNo']
    line = result['lines'][idx]
    result['lines'][idx] = insertString(line, result['insert']['x'], closeCh)
    result['insert']['x'] = result['insert']['x'] + 1

def minIndent(x, result):
    opener = peek(result['stack'])
    if opener != None:
        startX = opener['x']
        return max(startX + 1, x)
    return x

def minDedent(x, result):
    if result['maxIndent'] != None:
        return min(result['maxIndent'], x)
    return x

def correctIndent(result):
    opener = peek(result['stack'])
    delta = 0
    if opener != None and opener['indentDelta'] != None:
        delta = opener['indentDelta']

    newX = result['x'] + delta
    newX = minIndent(newX, result)
    newX = minDedent(newX, result)

    result['indentDelta'] = result['indentDelta'] + newX - result['x']

    if newX != result['x']:
        indentStr = ""
        for i in range(0, newX):
            indentStr = indentStr + " "
        line = result['lines'][result['lineNo']]
        newLine = replaceStringRange(line, 0, result['x'], indentStr)
        result['lines'][result['lineNo']] = newLine
        result['x'] = newX

    result['trackIndent'] = False
    result['maxIndent'] = None

def handleCursorDelta(result):
    hasCursorDelta = bool(result['cursorLine'] == result['lineNo'] and
                          result['cursorX'] == result['x'] and
                          result['cursorX'] != None)
    if hasCursorDelta:
        result['indentDelta'] = result['indentDelta'] + result['cursorDx']

def processIndent_paren(result):
    ch = result['ch']
    stack = result['stack']

    checkIndent = bool(result['trackIndent'] and
                       isInCode(stack) and
                       isWhitespace(ch) != True and
                       result['ch'] != SEMICOLON)

    atValidCloser = bool(checkIndent and
                         isCloseParen(ch) and
                         isValidCloser(stack, ch))

    isCursorHolding = bool(result['lineNo'] == result['cursorLine'] and
                           result['cursorX'] != None and
                           result['cursorX'] <= result['x'])

    shouldMoveCloser = bool(atValidCloser and isCursorHolding != True)
    skip = bool(checkIndent and isCloseParen(ch) and isCursorHolding != True)
    atIndent = bool(checkIndent and skip != True)
    quit = bool(atIndent and result['quoteDanger'])

    result['quit'] = quit
    result['process'] = bool(skip != True)

    if quit:
        return

    if shouldMoveCloser:
        appendParenTrail(result)

    handleCursorDelta(result)

    if atIndent:
        correctIndent(result)

def processChar_paren(result, ch):
    origCh = ch
    result['ch'] = ch
    processIndent_paren(result)

    if result['quit']:
        return

    if result['process']:
        # NOTE: the order here is important!
        updateParenTrail(result)
        pushChar(result)
        updateInsertionPt(result)
    else:
        result['ch'] = ""

    updateLine(result, origCh)
    result['x'] = result['x'] + len(result['ch'])

def formatParenTrail(result):
    start = result['parenTrail']['start']
    end = result['parenTrail']['end']

    if start == None or end == None:
        return

    line = result['lines'][result['lineNo']]
    newTrail = ""
    spaceCount = 0
    for i in range(start, end):
        if isCloseParen(line[i]):
            newTrail = newTrail + line[i]
        else:
            spaceCount = spaceCount + 1

    if spaceCount > 0:
        result['lines'][result['lineNo']] = replaceString(line, start, end, newTrail)
        end = end - spaceCount

    if result['insert']['lineNo'] == result['lineNo']:
        result['insert']['x'] = end

def processLine_paren(result, line):
    result['lineNo'] = result['lineNo'] + 1
    result['backup'] = []
    result['cursorInComment'] = False
    result['parenTrail'] = {'start': None, 'end': None}
    result['trackIndent'] = bool(isInStr(result['stack']) != True)
    result['lines'].append(line)
    result['x'] = 0
    result['indentDelta'] = 0

    chars = line + NEWLINE
    for ch in chars:
        processChar_paren(result, ch)
        if result['quit']:
            break

    if result['quit'] != True:
        formatParenTrail(result)

def finalizeResult_paren(result):
    result['success'] = bool(len(result['stack']) == 0 and
                             result['quoteDanger'] != True)

def processText_paren(text, options):
    result = initialResult()

    if options:
        result['cursorDx'] = options['cursorDx']
        result['cursorLine'] = options['cursorLine']
        result['cursorX'] = options['cursorX']

    lines = text.split(NEWLINE)
    for line in lines:
        processLine_paren(result, line)
        if result['quit']:
            break

    finalizeResult_paren(result)
    return result

def formatText_paren(text, options):
    result = processText_paren(text, options)
    outText = text
    if result['success']:
        outText = NEWLINE.join(result['lines'])
    return {
        'text': outText,
        'success': result['success'],
    }
    
#-------------------------------------------------------------------------------
# Public API
#-------------------------------------------------------------------------------

def indent_mode(in_text, options):
    return formatText(in_text, options)

def paren_mode(in_text, options):
    return formatText_paren(in_text, options)
