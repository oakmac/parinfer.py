# Parinfer.py - a Parinfer implementation in Python
# v0.5.0
# https://github.com/oakmac/parinfer.py
#
# More information about Parinfer can be found here:
# http://shaunlebron.github.io/parinfer/
#
# Copyright (c) 2015, Chris Oakman and other contributors
# Released under the ISC license
# https://github.com/oakmac/parinfer.py/blob/master/LICENSE.md

#-------------------------------------------------------------------------------
# Constants
#-------------------------------------------------------------------------------

INDENT_MODE = 'INDENT_MODE'
PAREN_MODE = 'PAREN_MODE'

BACKSLASH = '\\'
DOUBLE_QUOTE = '"'
NEWLINE = '\n'
SEMICOLON = ';'
TAB = '\t'

## TODO: regex here
LINE_ENDING = "\n"

PARENS = {
    '{': '}',
    '}': '{',
    '[': ']',
    ']': '[',
    '(': ')',
    ')': '(',
}

#-------------------------------------------------------------------------------
# Misc
#-------------------------------------------------------------------------------

def isOpenParen(c):
    return c == "{" or c == "(" or c == "["


def isCloseParen(c):
    return c == "}" or c == ")" or c == "]"

#-------------------------------------------------------------------------------
# Result Structure
#-------------------------------------------------------------------------------


def initialResult(text, options, mode):
    """Returns a dictionary of the initial state."""
    result = {
        'mode': mode,
        'origText': text,
        'origLines': text.split(LINE_ENDING),
        'lines': [],
        'lineNo': -1,
        'ch': '',
        'x': 0,
        'parenStack': [],
        'parenTrail': {
            'lineNo': None,
            'startX': None,
            'endX': None,
            'openers': [],
        },
        'cursorX': None,
        'cursorLine': None,
        'cursorDx': None,
        'isInCode': True,
        'isEscaping': False,
        'isInStr': False,
        'isInComment': False,
        'quoteDanger': False,
        'trackingIndent': False,
        'skipChar': False,
        'success': False,
        'maxIndent': None,
        'indentDelta': 0,
        'error': {
            'name': None,
            'message': None,
            'lineNo': None,
            'x': None,
        },
        'errorPosCache': {},
    }

    if isinstance(options, dict):
        if 'cursorDx' in options:
            result['cursorDx'] = options['cursorDx']
        if 'cursorLine' in options:
            result['cursorLine'] = options['cursorLine']
        if 'cursorX' in options:
            result['cursorX'] = options['cursorX']

    return result

#-------------------------------------------------------------------------------
# Possible Errors
#-------------------------------------------------------------------------------

ERROR_QUOTE_DANGER = "quote-danger"
ERROR_EOL_BACKSLASH = "eol-backslash"
ERROR_UNCLOSED_QUOTE = "unclosed-quote"
ERROR_UNCLOSED_PAREN = "unclosed-paren"
ERROR_UNHANDLED = "unhandled"

errorMessages = {}
errorMessages[ERROR_QUOTE_DANGER] = "Quotes must balanced inside comment blocks."
errorMessages[ERROR_EOL_BACKSLASH] = "Line cannot end in a hanging backslash."
errorMessages[ERROR_UNCLOSED_QUOTE] = "String is missing a closing quote."
errorMessages[ERROR_UNCLOSED_PAREN] = "Unmatched open-paren."

def cacheErrorPos(result, name, lineNo, x):
    result['errorPosCache'][name] = {'lineNo': lineNo, 'x': x}


def error(result, name, lineNo, x):
    cache = result['errorPosCache'][name]

    if lineNo is None:
        lineNo = cache['lineNo']
    if x is None:
        x = cache['x']

    return {
        'parinferError': True,
        'name': name,
        'message': errorMessages[name],
        'lineNo': lineNo,
        'x': x,
    }

#-------------------------------------------------------------------------------
# String Operations
#-------------------------------------------------------------------------------

def insertWithinString(orig, idx, insert):
    return orig[:idx] + insert + orig[idx:]

def replaceWithinString(orig, start, end, replace):
    return orig[:start] + replace + orig[end:]

def removeWithinString(orig, start, end):
    return orig[:start] + orig[end:]

def multiplyString(text, n):
    result = ""
    for i in n:
        result = result + text
    return result

def getLineEnding(text):
    ## TODO: write me
    return None

#-------------------------------------------------------------------------------
# Line Operations
#-------------------------------------------------------------------------------

## TODO: write me

#-------------------------------------------------------------------------------
# Misc Utils
#-------------------------------------------------------------------------------

def clamp(val, minN, maxN):
    if minN is not None:
        val = max(minN, val)
    if maxN is not None:
        val = min(maxN, val)
    return val

def peek(arr):
    arrLen = len(arr)
    if arrLen == 0:
        return None
    return arr[arrLen - 1]

#-------------------------------------------------------------------------------
# Character Functions
#-------------------------------------------------------------------------------

def isValidCloseParen(parenStack, ch):
    if len(parenStack) == 0:
        return False
    return peek(parenStack)['ch'] == PARENS[ch]

def onOpenParen(result):
    if result['isInCode']:
        result['parenStack'].append({
            'lineNo': result['lineNo'],
            'x': result['x'],
            'ch': result['ch'],
            'indentDelta': result['indentDelta'],
        })

def onMatchedCloseParen(result):
    opener = peek(result['parenStack'])
    result['parenTrail']['endX'] = result['x'] + 1
    result['parenTrail']['openers'].append(opener)
    result['maxIndent'] = opener['x']
    result['parenStack'].pop()

def onUnmatchedCloseParen(result):
    result['ch'] = ''

def onCloseParen(result):
    if result['isInCode']:
        if isValidCloseParen(result['parenStack'], result['ch']):
            onMatchedCloseParen(result)
        else:
            onUnmatchedCloseParen(result)

def onTab(result):
    if result['isInCode']:
        result['ch'] = '  '

def onSemicolon(result):
    if result['isInCode']:
        result['isInComment'] = True
        result['commentX'] = result['x']

def onNewLine(result):
    result['isInComment'] = False
    result['ch'] = ''

def onQuote(result):
    if result['isInStr']:
        result['isInStr'] = False
    elif result['isInComment']:
        result['quoteDanger'] = not result['quoteDanger']
        if result['quoteDanger']:
            cacheErrorPos(result, ERROR_QUOTE_DANGER, result['lineNo'], result['x'])
    else:
        result['isInStr'] = True
        cacheErrorPos(result, ERROR_UNCLOSED_QUOTE, result['lineNo'], result['x]'])

def onBackslash(result):
    result['isEscaping'] = True

def afterBackslash(result):
    result['isEscaping'] = False

    if result['ch'] == NEWLINE:
        if result['isInCode']:
            None
            ## TODO: raise exception here
            # raise ParinferError error(result, ERROR_EOL_BACKSLASH, result['lineNo'], result['x'] - 1)
        onNewline(result)

def onChar(result):
    ch = result['ch']
    if result['isEscaping']:
        afterBackslash(result)
    elif isOpenParen(ch):
        onOpenParen(result)
    elif isCloseParen(ch):
        onCloseParen(result)
    elif ch == DOUBLE_QUOTE:
        onQuote(result)
    elif ch == SEMICOLON:
        onSemicolon(result)
    elif ch == BACKSLASH:
        onBackslash(result)
    elif ch == TAB:
        onTab(result)
    elif ch == NEWLINE:
        onNewline(result)

    result['isInCode'] = (not result['isInComment'] and not result['isInStr'])

#-------------------------------------------------------------------------------
# Cursor Functions
#-------------------------------------------------------------------------------

def isCursorOnLeft(result):
    return (result['lineNo'] == result['cursorLine'] and
            result['cursorX'] is not None and
            result['cursorX'] <= result['x'])

def isCursorOnRight(result, x):
    return (result['lineNo'] == result['cursorLine'] and
            result['cursorX'] is not None and
            x is not None and
            result['cursorX'] > x)

def isCursorInComment(result):
    return isCursorOnRight(result, result['commentX'])

def handleCursorDelta(result):
    hasCursorDelta = (result['cursorDx'] is not None and
                      result['cursorLine'] == result['lineNo'] and
                      result['cursorX'] == result['x'])

    if hasCursorDelta:
        result['indentDelta'] = result['indentDelta'] + result['cursorDx']

#-------------------------------------------------------------------------------
# Paren Trail Functions
#-------------------------------------------------------------------------------

def updateParenTrailBounds(result):
    line = result['lines'][result['lineNo']]
    prevCh = None
    if result['x'] > 0:
        prevCh = line[result['x'] - 1]
    ch = result['ch']

    shouldReset = (result['isInCode'] and
                   not isCloseParen(ch) and
                   ch != "" and
                   (ch != " " or prevCh == BACKSLASH) and
                   ch != "  ")

    if shouldReset:
        result['parenTrail']['lineNo'] = result['lineNo']
        result['parenTrail']['startX'] = result['x'] + 1
        result['parenTrail']['endX'] = result['x'] + 1
        result['parenTrail']['openers'] = []
        result['maxIndent'] = None

def truncateParenTrailBounds(result):
    startX = result['parenTrail']['startX']
    endX = result['parenTrail']['endX']

    isCursorBlocking = (isCursorOnRight(result, startX) and
                        not isCursorInComment(result))

    if isCursorBlocking:
        newStartX = max(startX, result['cursorX'])
        newEndX = max(endX, result['cursorX'])

        line = result['lines'][result['lineNo']]
        removeCount = 0
        for i in range(startX, newStartX):
            if isCloseParen(line[i]):
                removeCount = removeCount + 1

        result['parenTrail']['openers'] = result['parenTrail']['openers'][:removeCount]
        result['parenTrail']['startX'] = newStartX
        result['parenTrail']['endX'] = newEndX

def removeParenTrail(result):
    startX = result['parenTrail']['startX']
    endX = result['parenTrail']['endX']

    if startX == endX:
        return

    openers = result['parenTrail']['openers']
    while len(openers) != 0:
        result['parenStack'].append(openers.pop())

    removeWithinLine(result, result['lineNo'], startX, endX)

def correctParenTrail(result, indentX):
    parens = ""

    while len(result['parenStack']) > 0:
        opener = peek(result['parenStack'])
        if opener['x'] >= indentX:
            result['parenStack'].pop()
            parens = parens + PARENS[opener['ch']]
        else:
            break

    insertWithinLine(result, result['parenTrail']['lineNo'], result['parenTrail']['startX'], parens)

def cleanParenTrail(result):
    startX = result['parenTrail']['startX']
    endX = result['parenTrail']['endX']

    if (startX == endX or
        result['lineNo'] != result['parenTrail']['lineNo']):
        return

    line = result['lines'][result['lineNo']]
    newTrail = ""
    spaceCount = 0
    for i in range(startX, endX):
        if isCloseParen(line[i]):
            newTrail = newTrail + line[i]
        else:
            spaceCount = spaceCount + 1

    if spaceCount > 0:
        replaceWithinLine(result, result['lineNo'], startX, endX, newTrail)
        result['parenTrail']['endX'] = result['parenTrail']['endX'] - spaceCount

def appendParenTrail(result):
    opener = result['parenStack'].pop()
    closeCh = PARENS[opener['ch']]

    result['maxIndent'] = opener['x']
    insertWithinLine(result, result['parenTrail']['lineNo'], result['parenTrail']['endX'], closeCh)
    result['parenTrail']['endX'] = result['parenTrail']['endX'] + 1

def finishNewParenTrail(result):
    if result['mode'] == INDENT_MODE:
        truncateParenTrailBounds(result)
        removeParenTrail(result)
    elif result['mode'] == PAREN_MODE:
        cleanParenTrail(result)































def getPrevCh(stack, i):
    e = peek(stack, i)
    if e is None:
        return None
    return e['ch']

def isEscaping(stack):
    return getPrevCh(stack, 1) == BACKSLASH

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
    return (not isInStr(stack) and not isInComment(stack))

def isValidCloser(stack, ch):
    return getPrevCh(stack, 1) == PARENS[ch]

#-------------------------------------------------------------------------------
# Stack Operations
#-------------------------------------------------------------------------------

def pushOpen(result):
    stack = result['stack']
    if isEscaping(stack):
        stack.pop()
        return
    if isInCode(stack):
        stack.append({
            'ch': result['ch'],
            'indentDelta': result['indentDelta'],
            'x': result['x'],
        })

def pushClose(result):
    stack = result['stack']
    if isEscaping(stack):
        stack.pop()
        return

    backup = result['backup']
    ch = result['ch']
    if isInCode(stack):
        if isValidCloser(stack, ch):
            opener = stack.pop()
            result['maxIndent'] = opener['x']
            backup.append(opener)
        else:
            # erase non-matched paren
            result['ch'] = ""

def pushTab(result):
    if not isInStr(result['stack']):
        result['ch'] = "  "

def pushSemicolon(result):
    stack = result['stack']
    if isEscaping(stack):
        stack.pop()
        return
    if isInCode(stack):
        stack.append({
            'ch': result['ch'],
            'x': result['x'],
        })

def pushNewline(result):
    stack = result['stack']
    if isEscaping(stack):
        stack.pop()
    if isInComment(stack):
        stack.pop()
    result['ch'] = ""

def pushEscape(result):
    stack = result['stack']
    if isEscaping(stack):
        stack.pop()
    else:
        stack.append({
            'ch': result['ch'],
            'x': result['x'],
        })

def pushQuote(result):
    stack = result['stack']
    if isEscaping(stack) or isInStr(stack):
        stack.pop()
        return
    if isInComment(stack):
        result['quoteDanger'] = not result['quoteDanger']
        return
    # default case
    stack.append({
        'ch': result['ch'],
        'x': result['x'],
    })

def pushDefault(result):
    stack = result['stack']
    if isEscaping(stack):
        stack.pop()

def pushChar(result):
    ch = result['ch']
    if isOpenParen(ch):
        pushOpen(result)
        return
    if isCloseParen(ch):
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
    if indentX is None:
        indentX = 0

    stack = result['stack']
    parens = ""

    while len(stack) > 0:
        opener = peek(stack, 1)
        if opener['x'] >= indentX:
            stack.pop()
            parens = parens + PARENS[opener['ch']]
        else:
            break

    insertLineNo = result['insert']['lineNo']
    newString = insertString(result['lines'][insertLineNo],
                             result['insert']['x'],
                             parens)
    result['lines'][insertLineNo] = newString

def updateParenTrail(result):
    ch = result['ch']
    stack = result['stack']
    closeParen = isCloseParen(ch)
    escaping = isEscaping(stack)
    inCode = isInCode(stack)

    shouldPass = (ch == SEMICOLON or
                  ch == COMMA or
                  isWhitespace(ch) or
                  closeParen)

    shouldReset = (inCode and
                   (escaping or not shouldPass))

    result['cursorInComment'] = (result['cursorInComment'] or
                                 (result['cursorLine'] == result['lineNo'] and
                                  result['x'] == result['cursorX'] and
                                  isInComment(stack)))

    shouldUpdate = (inCode and
                    not escaping and
                    closeParen and
                    isValidCloser(stack, ch))

    if shouldReset:
        result['backup'] = []
        result['parenTrail'] = {'start': None, 'end': None}
        result['maxIndent'] = None
    elif shouldUpdate:
        if result['parenTrail']['start'] is None:
            result['parenTrail']['start'] = result['x']
        result['parenTrail']['end'] = result['x'] + 1

def blockParenTrail(result):
    start = result['parenTrail']['start']
    end = result['parenTrail']['end']
    isCursorBlocking = (result['lineNo'] == result['cursorLine'] and
                        start is not None and
                        result['cursorX'] > start and
                        not result['cursorInComment'])

    if start is not None and isCursorBlocking:
        start = max(start, result['cursorX'])

    if end is not None and isCursorBlocking:
        end = max(end, result['cursorX'])

    if start == end:
        start = None
        end = None

    result['parenTrail']['start'] = start
    result['parenTrail']['end'] = end

def removeParenTrail(result):
    start = result['parenTrail']['start']
    end = result['parenTrail']['end']

    if start is None or end is None:
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
    prevChIdx = result['x'] - 1
    prevCh = None
    if prevChIdx >= 0:
        prevCh = line[prevChIdx]
    ch = result['ch']

    shouldInsert = (isInCode(result['stack']) and
                    ch != "" and
                    (not isWhitespace(ch) or prevCh == BACKSLASH) and
                    (not isCloseParen(ch) or result['lineNo'] == result['cursorLine']))

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
    checkIndent = (result['trackIndent'] and
                   isInCode(stack) and
                   not isWhitespace(ch) and
                   ch != SEMICOLON)
    skip = (checkIndent and isCloseParen(ch))
    atIndent = (checkIndent and not skip)
    quit = (atIndent and result['quoteDanger'])

    result['quit'] = quit
    result['process'] = (not skip and not quit)

    if atIndent and not quit:
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
    result['trackIndent'] = (len(stack) > 0 and not isInStr(stack))
    result['lines'].append(line)
    result['x'] = 0

    chars = line + NEWLINE
    for ch in chars:
        processChar(result, ch)
        if result['quit']:
            break

    if result['quit'] is False:
        blockParenTrail(result)
        removeParenTrail(result)

def finalizeResult(result):
    stack = result['stack']
    result['success'] = (not isInStr(stack) and
                         not result['quoteDanger'])
    if result['success'] and len(stack) > 0:
        closeParens(result, None)

def processText(text, options):
    result = initialResult()

    if isinstance(options, dict):
        if 'cursorLine' in options:
            result['cursorLine'] = options['cursorLine']
        if 'cursorX' in options:
            result['cursorX'] = options['cursorX']

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
    closeCh = PARENS[opener['ch']]
    result['maxIndent'] = opener['x']
    idx = result['insert']['lineNo']
    line = result['lines'][idx]
    result['lines'][idx] = insertString(line, result['insert']['x'], closeCh)
    result['insert']['x'] = result['insert']['x'] + 1

def minIndent(x, result):
    opener = peek(result['stack'], 1)
    if opener is not None:
        startX = opener['x']
        return max(startX + 1, x)
    return x

def minDedent(x, result):
    if result['maxIndent'] is not None:
        return min(result['maxIndent'], x)
    return x

def correctIndent(result):
    opener = peek(result['stack'], 1)
    delta = 0
    if opener is not None and opener['indentDelta'] is not None:
        delta = opener['indentDelta']

    newX1 = result['x'] + delta
    newX2 = minIndent(newX1, result)
    newX3 = minDedent(newX2, result)

    result['indentDelta'] = result['indentDelta'] + newX3 - result['x']

    if newX3 != result['x']:
        indentStr = ""
        for i in range(0, newX3):
            indentStr = indentStr + " "
        line = result['lines'][result['lineNo']]
        newLine = replaceStringRange(line, 0, result['x'], indentStr)
        result['lines'][result['lineNo']] = newLine
        result['x'] = newX3

    result['trackIndent'] = False
    result['maxIndent'] = None

def handleCursorDelta(result):
    hasCursorDelta = (result['cursorLine'] == result['lineNo'] and
                      result['cursorX'] == result['x'] and
                      result['cursorX'] is not None)
    if hasCursorDelta and result['cursorDx'] is not None:
        result['indentDelta'] = result['indentDelta'] + result['cursorDx']

def processIndent_paren(result):
    ch = result['ch']
    stack = result['stack']
    closeParen = isCloseParen(ch)

    checkIndent = (result['trackIndent'] and
                   isInCode(stack) and
                   not isWhitespace(ch) and
                   result['ch'] != SEMICOLON)

    atValidCloser = (checkIndent and
                     closeParen and
                     isValidCloser(stack, ch))

    isCursorHolding = (result['lineNo'] == result['cursorLine'] and
                       result['cursorX'] is not None and
                       result['cursorX'] <= result['x'])

    shouldMoveCloser = (atValidCloser and
                        not isCursorHolding)

    skip = (checkIndent and
            closeParen and
            not isCursorHolding)

    atIndent = (checkIndent and not skip)
    quit = (atIndent and result['quoteDanger'])

    result['quit'] = quit
    result['process'] = (not skip)

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

    if start is None or end is None:
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
        result['lines'][result['lineNo']] = replaceStringRange(line, start, end, newTrail)
        end = end - spaceCount

    if result['insert']['lineNo'] == result['lineNo']:
        result['insert']['x'] = end

def processLine_paren(result, line):
    result['lineNo'] = result['lineNo'] + 1
    result['backup'] = []
    result['cursorInComment'] = False
    result['parenTrail'] = {'start': None, 'end': None}
    result['trackIndent'] = (not isInStr(result['stack']))
    result['lines'].append(line)
    result['x'] = 0
    result['indentDelta'] = 0

    chars = line + NEWLINE
    for ch in chars:
        processChar_paren(result, ch)
        if result['quit']:
            break

    if not result['quit']:
        formatParenTrail(result)

def finalizeResult_paren(result):
    result['success'] = (len(result['stack']) == 0 and
                         not result['quoteDanger'])

def processText_paren(text, options):
    result = initialResult()

    if isinstance(options, dict):
        if 'cursorDx' in options:
            result['cursorDx'] = options['cursorDx']
        if 'cursorLine' in options:
            result['cursorLine'] = options['cursorLine']
        if 'cursorX' in options:
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
