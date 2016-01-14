## Parinfer.py - a Parinfer implementation in Python
## v0.5.0
## https://github.com/oakmac/parinfer.py
##
## More information about Parinfer can be found here:
## http://shaunlebron.github.io/parinfer/
##
## Copyright (c) 2015, Chris Oakman and other contributors
## Released under the ISC license
## https://github.com/oakmac/parinfer.py/blob/master/LICENSE.md

#-------------------------------------------------------------------------------
# Constants
#-------------------------------------------------------------------------------

INDENT_MODE = 'INDENT_MODE'
PAREN_MODE = 'PAREN_MODE'

BACKSLASH = '\\'
COMMA = ','
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

def insertWithinLine(result, lineNo, idx, insert):
    line = result['lines'][lineNo]
    result['lines'][lineNo] = insertWithinString(line, idx, insert)

def replaceWithinLine(result, lineNo, start, end, replace):
    line = result['lines'][lineNo]
    result['lines'][lineNo] = replaceWithinString(line, start, end, replace)

def removeWithinLine(result, lineNo, start, end):
    line = result['lines'][lineNo]
    result['lines'][lineNo] = removeWithinString(line, start, end)

def initLine(result, line):
    result['x'] = 0
    result['lineNo'] = result['lineNo'] + 1
    result['lines'].append(line)

    # reset line-specific state
    result['commentX'] = None
    result['indentDelta'] = 0

def commitChar(result, origCh):
    ch = result['ch']
    if origCh != ch:
        replaceWithinLine(result, result['lineNo'], result['x'], result['x'] + len(origCh), ch)
    result['x'] = result['x'] + len(ch)

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
            ## TODO: raise exception here
            # raise ParinferError error(result, ERROR_EOL_BACKSLASH, result['lineNo'], result['x'] - 1)
            return None
        onNewLine(result)

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
        onNewLine(result)

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

    if (startX == endX or result['lineNo'] != result['parenTrail']['lineNo']):
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

#-------------------------------------------------------------------------------
# Indentation functions
#-------------------------------------------------------------------------------

def correctIndent(result):
    # TODO: write me
    return None

def onProperIndent(result):
    # TODO: write me
    return None

def onLeadingCloseParen(result):
    # TODO: write me
    return None

def onIndent(result):
    if isCloseParen(result['ch']):
        onLeadingCloseParen(result)
    elif result['ch'] == SEMICOLON:
        # comments don't count as indentation points
        result['trackingIndent'] = False
    elif result['ch'] != NEWLINE:
        onProperIndent(result)

#-------------------------------------------------------------------------------
# High-level processing functions
#-------------------------------------------------------------------------------

def processChar(result, ch):
    # TODO: write me
    return None

def processLine(result, line):
    initLine(result, line)

    if result['mode'] == INDENT_MODE:
        result['trackingIndent'] = (len(result['parenStack']) != 0 and
                                    not result['isInStr'])
    elif result['mode'] == PAREN_MODE:
        result['trackingIndent'] = not result['isInStr']

    chars = line + NEWLINE
    for i in len(chars):
        processChar(result, chars[i])

    if result['lineNo'] == result['parenTrail']['lineNo']:
        finishNewParenTrail(result)

def finalizeResult(result):
    # TODO: write me
    return None

def processError(result, e):
    result['success'] = False
    if e['parinferError']:
        del e['parinferError']
        result['error'] = e
    else:
        result['error']['name'] = ERROR_UNHANDLED
        result['error']['message'] = e['stack']

def processText(text, options, mode):
    # TODO: write me
    return None

#-------------------------------------------------------------------------------
# Public API Helpers
#-------------------------------------------------------------------------------

def getChangedLines(result):
    changedLines = []
    for i in len(result['lines']):
        if result['lines'][i] != result['origLines'][i]:
            changedLines.append({
                'lineNo': i,
                'line': result['lines'][i],
            })
    return changedLines

def publicResult(result):
    if not result['success']:
        return {
            'text': result['origText'],
            'success': False,
            'error': result['error'],
        }

    lineEnding = getLineEnding(result['origText'])
    return {
        'text': lineEnding.join(result['lines']),
        'success': True,
        'changedLines': getChangedLines(result),
    }

#-------------------------------------------------------------------------------
# Public API
#-------------------------------------------------------------------------------

def indent_mode(text, options):
    result = processText(text, options, INDENT_MODE)
    return publicResult(result)

def paren_mode(text, options):
    result = processText(text, options, PAREN_MODE)
    return publicResult(result)
