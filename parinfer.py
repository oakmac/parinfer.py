## Parinfer.py - a Parinfer implementation in Python
## v3.12.0
## https://github.com/oakmac/parinfer.py
##
## More information about Parinfer can be found here:
## http://shaunlebron.github.io/parinfer/
##
## Copyright (c) 2015, Chris Oakman and other contributors
## Released under the ISC license
## https://github.com/oakmac/parinfer.py/blob/master/LICENSE.md

import re

#-------------------------------------------------------------------------------
# Constants
#-------------------------------------------------------------------------------

UINT_NULL = -999

INDENT_MODE = 'INDENT_MODE'
PAREN_MODE = 'PAREN_MODE'

BACKSLASH = '\\'
BLANK_SPACE = ' '
DOUBLE_SPACE = '  '
DOUBLE_QUOTE = '"'
NEWLINE = '\n'
SEMICOLON = ';'
TAB = '\t'

LINE_ENDING_REGEX = re.compile(r"\r?\n")

# CLOSE_PARENS = frozenset(['}', ')', ']'])

PARENS = {
    '{': '}',
    '}': '{',
    '[': ']',
    ']': '[',
    '(': ')',
    ')': '(',
}

# toggle this to check the asserts during development
RUN_ASSERTS = True #False

def isBoolean(x):
    return isinstance(x, bool)

def isArray(x):
    return isinstance(x, list)

def isInteger(x):
    return isinstance(x, int)

#-------------------------------------------------------------------------------
# Options Structure
#-------------------------------------------------------------------------------

def transformChange(change):
    if not change:
        return None

    newLines = change.newText.split(LINE_ENDING_REGEX)
    oldLines = change.oldText.split(LINE_ENDING_REGEX)

    # single line case:
    #    (defn foo| [])
    #             ^ newEndX, newEndLineNo
    #          +++

    # multi line case:
    #    (defn foo
    #          ++++
    #       "docstring."
    #    ++++++++++++++++
    #      |[])
    #    ++^ newEndX, newEndLineNo

    lastOldLineLen = len(oldLines[len(oldLines)-1])
    lastNewLineLen = len(newLines[len(newLines)-1])

    oldEndX = (change.x if len(oldLines) == 1 else 0) + lastOldLineLen
    newEndX = (change.x if len(newLines) == 1 else 0) + lastNewLineLen
    newEndLineNo = change.lineNo + (len(newLines)-1)

    return {
        'x': change.x,
        'lineNo': change.lineNo,
        'oldText': change.oldText,
        'newText': change.newText,

        'oldEndX': oldEndX,
        'newEndX': newEndX,
        'newEndLineNo': newEndLineNo,

        'lookupLineNo': newEndLineNo,
        'lookupX': newEndX
    }

def transformChanges(changes):
    if changes.length == 0:
        return None

    lines = {}
    for change in changes:
        change = transformChange(change)
        line = lines[change.lookupLineNo]
        if not line:
          line = lines[change.lookupLineNo] = {}

        line[change.lookupX] = change

    return lines

def parseOptions(options):
    options = options or {}
    return {
        'cursorX': options.cursorX,
        'cursorLine': options.cursorLine,
        'prevCursorX': options.prevCursorX,
        'prevCursorLine': options.prevCursorLine,
        'selectionStartLine': options.selectionStartLine,
        'changes': options.changes,
        'partialResult': options.partialResult,
        'forceBalance': options.forceBalance,
        'returnParens': options.returnParens
    }

#-------------------------------------------------------------------------------
# Result Structure
#-------------------------------------------------------------------------------

# This represents the running result. As we scan through each character
# of a given text, we mutate this structure to update the state of our
# system.

def initialParenTrail():
    return {
        'lineNo': UINT_NULL,        # [integer] - line number of the last parsed paren trail
        'startX': UINT_NULL,        # [integer] - x position of first paren in this range
        'endX': UINT_NULL,          # [integer] - x position after the last paren in this range
        'openers': [],              # [array of stack elements] - corresponding open-paren for each close-paren in this range
        'clamped': {
            'startX': UINT_NULL,    # startX before paren trail was clamped
            'endX': UINT_NULL,      # endX before paren trail was clamped
            'openers': []           # openers that were cut out after paren trail was clamped
        }
    }

def initialResult(text, options, mode, smart):
    """Returns a dictionary of the initial state."""

    result = {

        'mode': mode,                # [enum] - current processing mode (INDENT_MODE or PAREN_MODE)
        'smart': smart,              # [boolean] - smart mode attempts special user-friendly behavior

        'origText': text,            # [string] - original text
        'origCursorX': UINT_NULL,    # [integer] - original cursorX option
        'origCursorLine': UINT_NULL, # [integer] - original cursorLine option

        'inputLines':                # [string array] - input lines that we process line-by-line, char-by-char
          text.split(LINE_ENDING_REGEX),
        'inputLineNo': -1,           # [integer] - the current input line number
        'inputX': -1,                # [integer] - the current input x position of the current character (ch)

        'lines': [],                 # [string array] - output lines (with corrected parens or indentation)
        'lineNo': -1,                # [integer] - output line number we are on
        'ch': "",                    # [string] - character we are processing (can be changed to indicate a replacement)
        'x': 0,                      # [integer] - output x position of the current character (ch)
        'indentX': UINT_NULL,        # [integer] - x position of the indentation point if present

        'parenStack': [],            # We track where we are in the Lisp tree by keeping a stack (array) of open-parens.
                                     # Stack elements are objects containing keys {ch, x, lineNo, indentDelta}
                                     # whose values are the same as those described here in this result structure.

        'tabStops': [],              # In Indent Mode, it is useful for editors to snap a line's indentation
                                     # to certain critical points.  Thus, we have a `tabStops` array of objects containing
                                     # keys {ch, x, lineNo, argX}, which is just the state of the `parenStack` at the cursor line.

        'parenTrail': initialParenTrail(), # the range of parens at the end of a line

        'parenTrails': [],           # [array of {lineNo, startX, endX}] - all non-empty parenTrails to be returned

        'returnParens': False,       # [boolean] - determines if we return `parens` described below
        'parens': [],                # [array of {lineNo, x, closer, children}] - paren tree if `returnParens` is h

        'cursorX': UINT_NULL,        # [integer] - x position of the cursor
        'cursorLine': UINT_NULL,     # [integer] - line number of the cursor
        'prevCursorX': UINT_NULL,    # [integer] - x position of the previous cursor
        'prevCursorLine': UINT_NULL, # [integer] - line number of the previous cursor

        'selectionStartLine': UINT_NULL, # [integer] - line number of the current selection starting point

        'changes': None,             # [object] - mapping change.key to a change object (please see `transformChange` for object structure)

        'isInCode': True,            # [boolean] - indicates if we are currently in "code space" (not string or comment)
        'isEscaping': False,         # [boolean] - indicates if the next character will be escaped (e.g. `\c`).  This may be inside string, comment, or code.
        'isEscaped': False,          # [boolean] - indicates if the current character is escaped (e.g. `\c`).  This may be inside string, comment, or code.
        'isInStr': False,            # [boolean] - indicates if we are currently inside a string
        'isInComment': False,        # [boolean] - indicates if we are currently inside a comment
        'commentX': UINT_NULL,       # [integer] - x position of the start of comment on current line (if any)

        'quoteDanger': False,        # [boolean] - indicates if quotes are imbalanced inside of a comment (dangerous)
        'trackingIndent': False,     # [boolean] - are we looking for the indentation point of the current line?
        'skipChar': False,           # [boolean] - should we skip the processing of the current character?
        'success': False,            # [boolean] - was the input properly formatted enough to create a valid result?
        'partialResult': False,      # [boolean] - should we return a partial result when an error occurs?
        'forceBalance': False,       # [boolean] - should indent mode aggressively enforce paren balance?

        'maxIndent': UINT_NULL,      # [integer] - maximum allowed indentation of subsequent lines in Paren Mode
        'indentDelta': 0,            # [integer] - how far indentation was shifted by Paren Mode
                                     #  (preserves relative indentation of nested expressions)

        'trackingArgTabStop': None,  # [string] - enum to track how close we are to the first-arg tabStop in a list
                                     #  For example a tabStop occurs at `bar` below:
                                     #
                                     #         `   (foo    bar`
                                     #          00011112222000  <-- state after processing char (enums below)
                                     #
                                     #         0   None    => not searching
                                     #         1   'space' => searching for next space
                                     #         2   'arg'   => searching for arg
                                     #
                                     #    (We create the tabStop when the change from 2->0 happens.)
                                     #

        'error': {                   # if 'success' is False, return this error to the user
            'name': None,            # [string] - Parinfer's unique name for this error
            'message': None,         # [string] - error message to display
            'lineNo': None,          # [integer] - line number of error
            'x': None,               # [integer] - start x position of error
            'extra': {
                'name': None,
                'lineNo': None,
                'x': None
            }
        },
        'errorPosCache': {}          # [object] - maps error name to a potential error position
    }

    # Make sure no new properties are added to the result, for type safety.
    # (uncomment only when debugging, since it incurs a perf penalty)
    # Object.preventExtensions(result)
    # Object.preventExtensions(result.parenTrail)

    # merge options if they are valid
    if options:
        if isInteger(options.cursorX):
            result.cursorX            = options.cursorX
            result.origCursorX        = options.cursorX
        if isInteger(options.cursorLine):
            result.cursorLine         = options.cursorLine
            result.origCursorLine     = options.cursorLine
        if isInteger(options.prevCursorX):
            result.prevCursorX        = options.prevCursorX
        if isInteger(options.prevCursorLine):
            result.prevCursorLine     = options.prevCursorLine
        if isInteger(options.selectionStartLine):
            result.selectionStartLine = options.selectionStartLine
        if isArray(options.changes):
            result.changes            = transformChanges(options.changes)
        if isBoolean(options.partialResult):
            result.partialResult      = options.partialResult
        if isBoolean(options.forceBalance):
            result.forceBalance       = options.forceBalance
        if isBoolean(options.returnParens):
            result.returnParens       = options.returnParens

    return result

#-------------------------------------------------------------------------------
# Possible Errors
#-------------------------------------------------------------------------------

# `result.error.name` is set to any of these
ERROR_QUOTE_DANGER = "quote-danger"
ERROR_EOL_BACKSLASH = "eol-backslash"
ERROR_UNCLOSED_QUOTE = "unclosed-quote"
ERROR_UNCLOSED_PAREN = "unclosed-paren"
ERROR_UNMATCHED_CLOSE_PAREN = "unmatched-close-paren"
ERROR_UNMATCHED_OPEN_PAREN = "unmatched-open-paren"
ERROR_LEADING_CLOSE_PAREN = "leading-close-paren"
ERROR_UNHANDLED = "unhandled"

errorMessages = {}
errorMessages[ERROR_QUOTE_DANGER] = "Quotes must balanced inside comment blocks."
errorMessages[ERROR_EOL_BACKSLASH] = "Line cannot end in a hanging backslash."
errorMessages[ERROR_UNCLOSED_QUOTE] = "String is missing a closing quote."
errorMessages[ERROR_UNCLOSED_PAREN] = "Unclosed open-paren."
errorMessages[ERROR_UNMATCHED_CLOSE_PAREN] = "Unmatched close-paren."
errorMessages[ERROR_UNMATCHED_OPEN_PAREN] = "Unmatched open-paren."
errorMessages[ERROR_LEADING_CLOSE_PAREN] = "Line cannot lead with a close-paren."
errorMessages[ERROR_UNHANDLED] = "Unhandled error."

def cacheErrorPos(result, errorName):
    e = {
        'lineNo': result.lineNo,
        'x': result.x,
        'inputLineNo': result.inputLineNo,
        'inputX': result.inputX
    }
    result.errorPosCache[errorName] = e
    return e

def error(result, name):
    cache = result.errorPosCache[name]

    keyLineNo = 'lineNo' if result.partialResult else 'inputLineNo'
    keyX = 'x' if result.partialResult else 'inputX'

    e = {
        'parinferError': True,
        'name': name,
        'message': errorMessages[name],
        'lineNo': cache[keyLineNo] if cache else result[keyLineNo],
        'x': cache[keyX] if cache else result[keyX]
    }
    opener = peek(result.parenStack, 0)

    if name == ERROR_UNMATCHED_CLOSE_PAREN:
        # extra error info for locating the open-paren that it should've matched
        cache = result.errorPosCache[ERROR_UNMATCHED_OPEN_PAREN]
        if cache or opener:
          e.extra = {
            'name': ERROR_UNMATCHED_OPEN_PAREN,
            'lineNo': cache[keyLineNo] if cache else opener[keyLineNo],
            'x': cache[keyX] if cache else opener[keyX]
          }
    elif name == ERROR_UNCLOSED_PAREN:
        e.lineNo = opener[keyLineNo]
        e.x = opener[keyX]

    return e

#-------------------------------------------------------------------------------
# String Operations
#-------------------------------------------------------------------------------

def replaceWithinString(orig, start, end, replace):
    return orig[0:start] + replace + orig[end:]

if RUN_ASSERTS:
    assert replaceWithinString('aaa', 0, 2, '') == 'a'
    assert replaceWithinString('aaa', 0, 1, 'b') == 'baa'
    assert replaceWithinString('aaa', 0, 2, 'b') == 'ba'

def repeatString(text, n):
    return text*n

if RUN_ASSERTS:
    assert repeatString('a', 2) == 'aa'
    assert repeatString('aa', 3) == 'aaaaaa'
    assert repeatString('aa', 0) == ''
    assert repeatString('', 0) == ''
    assert repeatString('', 5) == ''

def getLineEnding(text):
    # NOTE: We assume that if the CR char "\r" is used anywhere,
    #       then we should use CRLF line-endings after every line.
    i = text.find("\r")
    if i != -1:
        return "\r\n"
    return "\n"

#-------------------------------------------------------------------------------
# Line Operations
#-------------------------------------------------------------------------------

def isCursorAffected(result, start, end):
    if result.cursorX == start and result.cursorX == end:
        return result.cursorX == 0
    return result.cursorX >= end

def shiftCursorOnEdit(result, lineNo, start, end, replace):
    oldLength = end - start
    newLength = replace.length
    dx = newLength - oldLength

    if (dx != 0 and
            result.cursorLine == lineNo and
            result.cursorX != UINT_NULL and
            isCursorAffected(result, start, end)):
        result.cursorX += dx

def replaceWithinLine(result, lineNo, start, end, replace):
    line = result.lines[lineNo]
    newLine = replaceWithinString(line, start, end, replace)
    result.lines[lineNo] = newLine

    shiftCursorOnEdit(result, lineNo, start, end, replace)

def insertWithinLine(result, lineNo, idx, insert):
    replaceWithinLine(result, lineNo, idx, idx, insert)

def initLine(result):
    result.x = 0
    result.lineNo += 1

    # reset line-specific state
    result.indentX = UINT_NULL
    result.commentX = UINT_NULL
    result.indentDelta = 0
    del result.errorPosCache[ERROR_UNMATCHED_CLOSE_PAREN]
    del result.errorPosCache[ERROR_UNMATCHED_OPEN_PAREN]
    del result.errorPosCache[ERROR_LEADING_CLOSE_PAREN]

    result.trackingArgTabStop = None
    result.trackingIndent = not result.isInStr

# if the current character has changed, commit its change to the current line.
def commitChar(result, origCh):
    ch = result.ch
    if origCh != ch:
        replaceWithinLine(result, result.lineNo, result.x, result.x + origCh.length, ch)
        result.indentDelta -= (origCh.length - ch.length)
    result.x += ch.length

#-------------------------------------------------------------------------------
# Misc Utils
#-------------------------------------------------------------------------------

def clamp(val, minN, maxN):
    if minN != UINT_NULL:
        val = max(minN, val)
    if maxN != UINT_NULL:
        val = min(maxN, val)
    return val

if RUN_ASSERTS:
    assert clamp(1, 3, 5) == 3
    assert clamp(9, 3, 5) == 5
    assert clamp(1, 3, UINT_NULL) == 3
    assert clamp(5, 3, UINT_NULL) == 5
    assert clamp(1, UINT_NULL, 5) == 1
    assert clamp(9, UINT_NULL, 5) == 5
    assert clamp(1, UINT_NULL, UINT_NULL) == 1

def peek(arr, idxFromBack):
    maxIdx = len(arr) - 1
    if idxFromBack > maxIdx:
        return None
    return arr[maxIdx - idxFromBack]

if RUN_ASSERTS:
    assert peek(['a'], 0) == 'a'
    assert peek(['a'], 1) == None
    assert peek(['a', 'b', 'c'], 0) == 'c'
    assert peek(['a', 'b', 'c'], 1) == 'b'
    assert peek(['a', 'b', 'c'], 5) == None
    assert peek([], 0) == None
    assert peek([], 1) == None

#-------------------------------------------------------------------------------
# Questions about characters
#-------------------------------------------------------------------------------

def isOpenParen(ch):
  return ch == "{" or ch == "(" or ch == "["

def isCloseParen(ch):
  return ch == "}" or ch == ")" or ch == "]"

def isValidCloseParen(parenStack, ch):
    if parenStack.length == 0:
        return False
    return peek(parenStack, 0).ch == MATCH_PAREN[ch]

def isWhitespace(result):
    ch = result.ch
    return not result.isEscaped and (ch == BLANK_SPACE or ch == DOUBLE_SPACE)

# can this be the last code character of a list?
def isClosable(result):
    ch = result.ch
    closer = isCloseParen(ch) and not result.isEscaped
    return result.isInCode and not isWhitespace(result) and ch != "" and not closer

#-------------------------------------------------------------------------------
# Advanced operations on characters
#-------------------------------------------------------------------------------

def checkCursorHolding(result):
    opener = peek(result.parenStack, 0)
    parent = peek(result.parenStack, 1)
    holdMinX = parent.x+1 if parent else 0
    holdMaxX = opener.x

    holding = (
        result.cursorLine == opener.lineNo and
        holdMinX <= result.cursorX and result.cursorX <= holdMaxX
    )
    shouldCheckPrev = not result.changes and result.prevCursorLine != UINT_NULL
    if shouldCheckPrev:
        prevHolding = (
            result.prevCursorLine == opener.lineNo and
            holdMinX <= result.prevCursorX and result.prevCursorX <= holdMaxX
        )
        if prevHolding and not holding:
            raise {'releaseCursorHold': True}
    return holding

def trackArgTabStop(result, state):
    if state == 'space':
        if result.isInCode and isWhitespace(result):
            result.trackingArgTabStop = 'arg'
    elif state == 'arg':
        if not isWhitespace(result):
            opener = peek(result.parenStack, 0)
            opener.argX = result.x
            result.trackingArgTabStop = null

#-------------------------------------------------------------------------------
# Literal character events
#-------------------------------------------------------------------------------

def onOpenParen(result):
    if result.isInCode:
        opener = {
            'inputLineNo': result.inputLineNo,
            'inputX': result.inputX,

            'lineNo': result.lineNo,
            'x': result.x,
            'ch': result.ch,
            'indentDelta': result.indentDelta,
            'maxChildIndent': UINT_NULL
        }

        if result.returnParens:
            opener.children = []
            opener.closer = {
                lineNo: UINT_NULL,
                x: UINT_NULL,
                ch: ''
            }
            parent = peek(result.parenStack, 0)
            parent = parent.children if parent else result.parens
            parent.push(opener)

        result.parenStack.push(opener)
        result.trackingArgTabStop = 'space'

def setCloser(opener, lineNo, x, ch):
    opener.closer.lineNo = lineNo
    opener.closer.x = x
    opener.closer.ch = ch

def onMatchedCloseParen(result):
    opener = peek(result.parenStack, 0)
    if result.returnParens:
        setCloser(opener, result.lineNo, result.x, result.ch)

    result.parenTrail.endX = result.x + 1
    result.parenTrail.openers.push(opener)

    if result.mode == INDENT_MODE and result.smart and checkCursorHolding(result):
        origStartX = result.parenTrail.startX
        origEndX = result.parenTrail.endX
        origOpeners = result.parenTrail.openers
        resetParenTrail(result, result.lineNo, result.x+1)
        result.parenTrail.clamped.startX = origStartX
        result.parenTrail.clamped.endX = origEndX
        result.parenTrail.clamped.openers = origOpeners

    result.parenStack.pop()
    result.trackingArgTabStop = None

def onUnmatchedCloseParen(result):
    if result.mode == PAREN_MODE:
        trail = result.parenTrail
        inLeadingParenTrail = trail.lineNo == result.lineNo and trail.startX == result.indentX
        canRemove = result.smart and inLeadingParenTrail
        if not canRemove:
            raise error(result, ERROR_UNMATCHED_CLOSE_PAREN)
    elif result.mode == INDENT_MODE and not result.errorPosCache[ERROR_UNMATCHED_CLOSE_PAREN]:
        cacheErrorPos(result, ERROR_UNMATCHED_CLOSE_PAREN)
        opener = peek(result.parenStack, 0)
        if opener:
            e = cacheErrorPos(result, ERROR_UNMATCHED_OPEN_PAREN)
            e.inputLineNo = opener.inputLineNo
            e.inputX = opener.inputX

    result.ch = ''

def onCloseParen(result):
    if result.isInCode:
        if isValidCloseParen(result.parenStack, result.ch):
            onMatchedCloseParen(result)
        else:
            onUnmatchedCloseParen(result)

def onTab(result):
    if result.isInCode:
        result.ch = DOUBLE_SPACE

def onSemicolon(result):
    if result.isInCode:
        result.isInComment = True
        result.commentX = result.x
        result.trackingArgTabStop = None

def onNewline(result):
    result.isInComment = False
    result.ch = ''

def onQuote(result):
    if result.isInStr:
        result.isInStr = False
    elif result.isInComment:
        result.quoteDanger = not result.quoteDanger
        if (result.quoteDanger):
            cacheErrorPos(result, ERROR_QUOTE_DANGER)
    else:
        result.isInStr = True
        cacheErrorPos(result, ERROR_UNCLOSED_QUOTE)

def onBackslash(result):
    result.isEscaping = True

def afterBackslash(result):
    result.isEscaping = False
    result.isEscaped = True

    if result.ch == NEWLINE:
        if result.isInCode:
            raise error(result, ERROR_EOL_BACKSLASH)
        onNewline(result)

#-------------------------------------------------------------------------------
# Character dispatch
#-------------------------------------------------------------------------------

def onChar(result):
    ch = result.ch
    result.isEscaped = False

    if (result.isEscaping):
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

    ch = result.ch

    result.isInCode = not result.isInComment and not result.isInStr

    if isClosable(result):
        resetParenTrail(result, result.lineNo, result.x+ch.length)

    state = result.trackingArgTabStop
    if (state):
        trackArgTabStop(result, state)

#-------------------------------------------------------------------------------
# Cursor defs
#-------------------------------------------------------------------------------

def isCursorLeftOf(cursorX, cursorLine, x, lineNo):
    return (
        cursorLine == lineNo and
        x != UINT_NULL and
        cursorX != UINT_NULL and
        cursorX <= x # inclusive since (cursorX = x) implies (x-1 < cursor < x)
    )

def isCursorRightOf(cursorX, cursorLine, x, lineNo):
    return (
        cursorLine == lineNo and
        x != UINT_NULL and
        cursorX != UINT_NULL and
        cursorX > x
    )

def isCursorInComment(result, cursorX, cursorLine):
  return isCursorRightOf(cursorX, cursorLine, result.commentX, result.lineNo)

def handleChangeDelta(result):
    if (result.changes and (result.smart or result.mode == PAREN_MODE)):
        line = result.changes[result.inputLineNo]
        if line:
            change = line[result.inputX]
            if change:
                result.indentDelta += (change.newEndX - change.oldEndX)

#-------------------------------------------------------------------------------
# Paren Trail defs
#-------------------------------------------------------------------------------

def resetParenTrail(result, lineNo, x):
    result.parenTrail.lineNo = lineNo
    result.parenTrail.startX = x
    result.parenTrail.endX = x
    result.parenTrail.openers = []
    result.parenTrail.clamped.startX = UINT_NULL
    result.parenTrail.clamped.endX = UINT_NULL
    result.parenTrail.clamped.openers = []

def isCursorClampingParenTrail(result, cursorX, cursorLine):
    return (
        isCursorRightOf(cursorX, cursorLine, result.parenTrail.startX, result.lineNo) and
        not isCursorInComment(result, cursorX, cursorLine)
    )

# INDENT MODE: allow the cursor to clamp the paren trail
def clampParenTrailToCursor(result):
  startX = result.parenTrail.startX
  endX = result.parenTrail.endX

  clamping = isCursorClampingParenTrail(result, result.cursorX, result.cursorLine)

  if clamping:
    newStartX = max(startX, result.cursorX)
    newEndX = max(endX, result.cursorX)

    line = result.lines[result.lineNo]
    removeCount = 0
    for i in range(startX, newStartX):
        if isCloseParen(line[i]):
            removeCount += 1

    openers = result.parenTrail.openers

    result.parenTrail.openers = openers.slice(removeCount)
    result.parenTrail.startX = newStartX
    result.parenTrail.endX = newEndX

    result.parenTrail.clamped.openers = openers.slice(0, removeCount)
    result.parenTrail.clamped.startX = startX
    result.parenTrail.clamped.endX = endX

# INDENT MODE: pops the paren trail from the stack
def popParenTrail(result):
    startX = result.parenTrail.startX
    endX = result.parenTrail.endX

    if startX == endX:
        return

    openers = result.parenTrail.openers
    while openers.length != 0:
        result.parenStack.push(openers.pop())

# Determine which open-paren (if any) on the parenStack should be considered
# the direct parent of the current line (given its indentation point).
# This allows Smart Mode to simulate Paren Mode's structure-preserving
# behavior by adding its `opener.indentDelta` to the current line's indentation.
# (care must be taken to prevent redundant indentation correction, detailed below)
def getParentOpenerIndex(result, indentX):
    for i in range(len(result.parenStack.length)):
        opener = peek(result.parenStack, i)

        currOutside = (opener.x < indentX)

        prevIndentX = indentX - result.indentDelta
        prevOutside = (opener.x - opener.indentDelta < prevIndentX)

        isParent = False

        if prevOutside and currOutside:
            isParent = True
        elif not prevOutside and not currOutside:
            isParent = False
        elif prevOutside and not currOutside:
            # POSSIBLE FRAGMENTATION
            # (foo    --\
            #            +--- FRAGMENT `(foo bar)` => `(foo) bar`
            # bar)    --/

            # 1. PREVENT FRAGMENTATION
            # ```in
            #   (foo
            # ++
            #   bar
            # ```
            # ```out
            #   (foo
            #     bar
            # ```
            if result.indentDelta == 0:
                isParent = True

            # 2. ALLOW FRAGMENTATION
            # ```in
            # (foo
            #   bar
            # --
            # ```
            # ```out
            # (foo)
            # bar
            # ```
            elif opener.indentDelta == 0:
                isParent = False

            else:
                # TODO: identify legitimate cases where both are nonzero

                # allow the fragmentation by default
                isParent = False

                # TODO: should we throw to exit instead?  either of:
                # 1. give up, just `throw error(...)`
                # 2. fallback to paren mode to preserve structure
        elif not prevOutside and currOutside:
            # POSSIBLE ADOPTION
            # (foo)   --\
            #            +--- ADOPT `(foo) bar` => `(foo bar)`
            #   bar   --/

            nextOpener = peek(result.parenStack, i+1)

            # 1. DISALLOW ADOPTION
            # ```in
            #   (foo
            # --
            #     (bar)
            # --
            #     baz)
            # ```
            # ```out
            # (foo
            #   (bar)
            #   baz)
            # ```
            # OR
            # ```in
            #   (foo
            # --
            #     (bar)
            # -
            #     baz)
            # ```
            # ```out
            # (foo
            #  (bar)
            #  baz)
            # ```
            if nextOpener and nextOpener.indentDelta <= opener.indentDelta:
                # we can only disallow adoption if nextOpener.indentDelta will actually
                # prevent the indentX from being in the opener's threshold.
                if indentX + nextOpener.indentDelta > opener.x:
                    isParent = True
                else:
                    isParent = False

            # 2. ALLOW ADOPTION
            # ```in
            # (foo
            #     (bar)
            # --
            #     baz)
            # ```
            # ```out
            # (foo
            #   (bar
            #     baz))
            # ```
            # OR
            # ```in
            #   (foo
            # -
            #     (bar)
            # --
            #     baz)
            # ```
            # ```out
            #  (foo
            #   (bar)
            #    baz)
            # ```
            elif nextOpener and nextOpener.indentDelta > opener.indentDelta:
                isParent = True

            # 3. ALLOW ADOPTION
            # ```in
            #   (foo)
            # --
            #   bar
            # ```
            # ```out
            # (foo
            #   bar)
            # ```
            # OR
            # ```in
            # (foo)
            #   bar
            # ++
            # ```
            # ```out
            # (foo
            #   bar
            # ```
            # OR
            # ```in
            #  (foo)
            # +
            #   bar
            # ++
            # ```
            # ```out
            #  (foo
            #   bar)
            # ```
            elif result.indentDelta > opener.indentDelta:
                isParent = True

            if isParent: # if new parent
                # Clear `indentDelta` since it is reserved for previous child lines only.
                opener.indentDelta = 0

        if isParent:
            break

    return i

# INDENT MODE: correct paren trail from indentation
def correctParenTrail(result, indentX):
    parens = ""

    index = getParentOpenerIndex(result, indentX)
    for i in range(0, index):
        opener = result.parenStack.pop()
        result.parenTrail.openers.push(opener)
        closeCh = MATCH_PAREN[opener.ch]
        parens += closeCh

        if result.returnParens:
            setCloser(opener, result.parenTrail.lineNo, result.parenTrail.startX+i, closeCh)

    if result.parenTrail.lineNo != UINT_NULL:
        replaceWithinLine(result, result.parenTrail.lineNo, result.parenTrail.startX, result.parenTrail.endX, parens)
        result.parenTrail.endX = result.parenTrail.startX + parens.length
        rememberParenTrail(result)

# PAREN MODE: remove spaces from the paren trail
def cleanParenTrail(result):
    startX = result.parenTrail.startX
    endX = result.parenTrail.endX

    if (startX == endX or
        result.lineNo != result.parenTrail.lineNo):
        return

    line = result.lines[result.lineNo]
    newTrail = ''
    spaceCount = 0
    for i in range(startX, endX):
        if isCloseParen(line[i]):
            newTrail += line[i]
        else:
            spaceCount += 1

    if spaceCount > 0:
        replaceWithinLine(result, result.lineNo, startX, endX, newTrail)
        result.parenTrail.endX -= spaceCount

# PAREN MODE: append a valid close-paren to the end of the paren trail
def appendParenTrail(result):
    opener = result.parenStack.pop()
    closeCh = MATCH_PAREN[opener.ch]
    if result.returnParens:
        setCloser(opener, result.parenTrail.lineNo, result.parenTrail.endX, closeCh)

    setMaxIndent(result, opener)
    insertWithinLine(result, result.parenTrail.lineNo, result.parenTrail.endX, closeCh)

    result.parenTrail.endX += 1
    result.parenTrail.openers.push(opener)
    updateRememberedParenTrail(result)

def invalidateParenTrail(result):
  result.parenTrail = initialParenTrail()

def checkUnmatchedOutsideParenTrail(result):
    cache = result.errorPosCache[ERROR_UNMATCHED_CLOSE_PAREN]
    if cache and cache.x < result.parenTrail.startX:
        raise error(result, ERROR_UNMATCHED_CLOSE_PAREN)

def setMaxIndent(result, opener):
    if opener:
        parent = peek(result.parenStack, 0)
        if parent:
            parent.maxChildIndent = opener.x
        else:
            result.maxIndent = opener.x

def rememberParenTrail(result):
    trail = result.parenTrail
    openers = trail.clamped.openers.concat(trail.openers)
    if openers.length > 0:
        isClamped = trail.clamped.startX != UINT_NULL
        allClamped = trail.openers.length == 0
        shortTrail = {
            'lineNo': trail.lineNo,
            'startX': trail.clamped.startX if isClamped else trail.startX,
            'endX': trail.clamped.endX if allClamped else trail.end,
        }
        result.parenTrails.push(shortTrail)

        if result.returnParens:
            for i in range(len(openers)):
                openers[i].closer.trail = shortTrail

def updateRememberedParenTrail(result):
    trail = result.parenTrails[len(result.parenTrails)-1]
    if not trail or trail.lineNo != result.parenTrail.lineNo:
        rememberParenTrail(result)
    else:
        trail.endX = result.parenTrail.endX
        if result.returnParens:
            opener = result.parenTrail.openers[result.parenTrail.openers.length-1]
            opener.closer.trail = trail

def finishNewParenTrail(result):
    if result.isInStr:
        invalidateParenTrail(result)
    elif result.mode == INDENT_MODE:
        clampParenTrailToCursor(result)
        popParenTrail(result)
    elif result.mode == PAREN_MODE:
        setMaxIndent(result, peek(result.parenTrail.openers, 0))
        if result.lineNo != result.cursorLine:
            cleanParenTrail(result)
        rememberParenTrail(result)

#-------------------------------------------------------------------------------
# Indentation defs
#-------------------------------------------------------------------------------

def addIndent(result, delta):
    origIndent = result.x
    newIndent = origIndent + delta
    indentStr = repeatString(BLANK_SPACE, newIndent)
    replaceWithinLine(result, result.lineNo, 0, origIndent, indentStr)
    result.x = newIndent
    result.indentX = newIndent
    result.indentDelta += delta

def shouldAddOpenerIndent(result, opener):
    # Don't add opener.indentDelta if the user already added it.
    # (happens when multiple lines are indented together)
    return opener.indentDelta != result.indentDelta

def correctIndent(result):
    origIndent = result.x
    newIndent = origIndent
    minIndent = 0
    maxIndent = result.maxIndent

    opener = peek(result.parenStack, 0)
    if opener:
        minIndent = opener.x + 1
        maxIndent = opener.maxChildIndent
        if shouldAddOpenerIndent(result, opener):
            newIndent += opener.indentDelta

    newIndent = clamp(newIndent, minIndent, maxIndent)

    if newIndent != origIndent:
        addIndent(result, newIndent - origIndent)

def onIndent(result):
    result.indentX = result.x
    result.trackingIndent = False

    if result.quoteDanger:
        raise error(result, ERROR_QUOTE_DANGER)

    if result.mode == INDENT_MODE:

        correctParenTrail(result, result.x)

        opener = peek(result.parenStack, 0)
        if opener and shouldAddOpenerIndent(result, opener):
            addIndent(result, opener.indentDelta)
    elif result.mode == PAREN_MODE:
        correctIndent(result)

def checkLeadingCloseParen(result):
    if (result.errorPosCache[ERROR_LEADING_CLOSE_PAREN] and
            result.parenTrail.lineNo == result.lineNo):
        raise error(result, ERROR_LEADING_CLOSE_PAREN)

def onLeadingCloseParen(result):
    if result.mode == INDENT_MODE:
        if not result.forceBalance:
            if result.smart:
                raise {leadingCloseParen: True}
        if not result.errorPosCache[ERROR_LEADING_CLOSE_PAREN]:
            cacheErrorPos(result, ERROR_LEADING_CLOSE_PAREN)
        result.skipChar = True

    if result.mode == PAREN_MODE:
        if not isValidCloseParen(result.parenStack, result.ch):
            if result.smart:
                result.skipChar = True
            else:
                raise error(result, ERROR_UNMATCHED_CLOSE_PAREN)
        elif isCursorLeftOf(result.cursorX, result.cursorLine, result.x, result.lineNo):
            resetParenTrail(result, result.lineNo, result.x)
            onIndent(result)
        else:
            appendParenTrail(result)
            result.skipChar = True

def onCommentLine(result):
    parenTrailLength = len(result.parenTrail.openers)

    # restore the openers matching the previous paren trail
    if result.mode == PAREN_MODE:
        for j in range(0, parenTrailLength):
            result.parenStack.push(peek(result.parenTrail.openers, j))

    i = getParentOpenerIndex(result, result.x)
    opener = peek(result.parenStack, i)
    if opener:
        # shift the comment line based on the parent open paren
        if shouldAddOpenerIndent(result, opener):
            addIndent(result, opener.indentDelta)
        # TODO: store some information here if we need to place close-parens after comment lines

    # repop the openers matching the previous paren trail
    if result.mode == PAREN_MODE:
        for j in range(0, parenTrailLength):
            result.parenStack.pop()

def checkIndent(result):
    if isCloseParen(result.ch):
        onLeadingCloseParen(result)
    elif result.ch == SEMICOLON:
        # comments don't count as indentation points
        onCommentLine(result)
        result.trackingIndent = False
    elif (result.ch != NEWLINE and
            result.ch != BLANK_SPACE and
            result.ch != TAB):
        onIndent(result)

def makeTabStop(result, opener):
    tabStop = {
        'ch': opener.ch,
        'x': opener.x,
        'lineNo': opener.lineNo
    }
    if opener.argX != None:
        tabStop.argX = opener.argX
    return tabStop

def getTabStopLine(result):
  return result.selectionStartLine if result.selectionStartLine != UINT_NULL else result.cursorLine

def setTabStops(result):
    if getTabStopLine(result) != result.lineNo:
        return

    for i in range(len(result.parenStack)):
        result.tabStops.push(makeTabStop(result, result.parenStack[i]))

    if (result.mode == PAREN_MODE):
        for i in range(result.parenTrail.openers.length-1, -1, -1):
            result.tabStops.push(makeTabStop(result, result.parenTrail.openers[i]))

    # remove argX if it falls to the right of the next stop
    for i  in range(1, len(result.tabStops)):
        x = result.tabStops[i].x
        prevArgX = result.tabStops[i-1].argX
        if prevArgX != None and prevArgX >= x:
            del result.tabStops[i-1].argX

#-------------------------------------------------------------------------------
# High-level processing functions
#-------------------------------------------------------------------------------

def processChar(result, ch):
    origCh = ch

    result.ch = ch
    result.skipChar = false

    handleChangeDelta(result)

    if result.trackingIndent:
        checkIndent(result)

    if result.skipChar:
        result.ch = ""
    else:
        onChar(result)

    commitChar(result, origCh)

def processLine(result, lineNo):
    initLine(result)
    result.lines.push(result.inputLines[lineNo])

    setTabStops(result)

    for x in range(len(result.inputLines[lineNo])):
        result.inputX = x
        processChar(result, result.inputLines[lineNo][x])

    processChar(result, NEWLINE)

    if not result.forceBalance:
        checkUnmatchedOutsideParenTrail(result)
        checkLeadingCloseParen(result)

    if result.lineNo == result.parenTrail.lineNo:
        finishNewParenTrail(result)

def finalizeResult(result):
    if result.quoteDanger:
        raise error(result, ERROR_QUOTE_DANGER)
    if result.isInStr:
        raise error(result, ERROR_UNCLOSED_QUOTE)

    if result.parenStack.length != 0:
        if result.mode == PAREN_MODE:
          raise error(result, ERROR_UNCLOSED_PAREN)

    if result.mode == INDENT_MODE:
        initLine(result)
        onIndent(result)

    result.success = True

def processError(result, e):
    result.success = False
    if e.parinferError:
        del e.parinferError
        result.error = e
    else:
        result.error.name = ERROR_UNHANDLED
        result.error.message = e.stack
        raise e

def processText(text, options, mode, smart):
    result = getInitialResult(text, options, mode, smart)

    try:
        for i in range(len(result.inputLines)):
            result.inputLineNo = i
            processLine(result, i)
        finalizeResult(result)
    except:
        # TODO: narrow this
        e = sys.exc_info()[0]
        if e.leadingCloseParen or e.releaseCursorHold:
            return processText(text, options, PAREN_MODE, smart)
        processError(result, e)

    return result

#-------------------------------------------------------------------------------
# Public API
#-------------------------------------------------------------------------------

def publicResult(result):
    lineEnding = getLineEnding(result.origText)
    if result.success:
        final = {
            'text': result.lines.join(lineEnding),
            'cursorX': result.cursorX,
            'cursorLine': result.cursorLine,
            'success': true,
            'tabStops': result.tabStops,
            'parenTrails': result.parenTrails
        }
        if result.returnParens:
            final.parens = result.parens
    else:
        final = {
            'text': result.lines.join(lineEnding) if result.partialResult else result.origText,
            'cursorX': result.cursorX if result.partialResult else result.origCursorX,
            'cursorLine': result.cursorLine if result.partialResult else result.origCursorLine,
            'parenTrails': result.parenTrails if result.partialResult else None,
            'success': false,
            'error': result.error
        }
        if result.partialResult and result.returnParens:
            final.parens = result.parens

    if final.cursorX == UINT_NULL:
        del final.cursorX
    if final.cursorLine == UINT_NULL:
        del final.cursorLine
    if final.tabStops and final.tabStops.length == 0:
        del final.tabStops
    return final

def indent_mode(text, options):
    options = parseOptions(options)
    return publicResult(processText(text, options, INDENT_MODE))

def paren_mode(text, options):
    options = parseOptions(options)
    return publicResult(processText(text, options, PAREN_MODE))

def smart_mode(text, options):
    options = parseOptions(options)
    smart = options.selectionStartLine == None
    return publicResult(processText(text, options, INDENT_MODE, smart))

API = {
    'version': "3.12.0",
    'indent_mode': indent_mode,
    'paren_mode': paren_mode,
    'smart_mode': smart_mode
}
