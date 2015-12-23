## Parinfer.py - a Parinfer implementation in Python
## https://github.com/oakmac/parinfer.py

## More information about Parinfer can be found here:
## http://shaunlebron.github.io/parinfer/

## Released under the ISC License:
## https://github.com/oakmac/parinfer.py/blob/master/LICENSE.md

def initial_state():
    """Returns a dictionary of the initial state."""
    return {
        'lines': [],
        'insert': {'line_dy': None, 'x': None},
        'line_no': -1,
        'quote_danger': False,
        'track_indent': False,
        'delim_trail': {'start': None, 'end': None},
        'stack': [],
        'backup': [],
    }

def finalize_state(state):
    # TODO: write me
    return state

def process_text(text, options):
    state = initial_state()

    if options:
        state['cursor_x'] = options['cursor_x']
        state['cursor_line'] = options['cursor_line']

    lines = text.split('\n')
    # TODO: process each line

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
