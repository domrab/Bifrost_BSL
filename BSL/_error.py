import sys
import traceback as _traceback


class Error(Exception):
    def __init__(self, s_message="", previous_error=None, b_stacktrace=True):
        x_line_start = lambda i: "\u250C" + i * "\u2500" + NL
        x_line_mid = lambda i: "\u251C" + i * "\u2500" + NL
        x_line_end = lambda i: "\u2514" + i * "\u2500" + NL

        NL = "\n"

        s_info = ""
        s_info += "\u2502 " + self.__class__.__name__ + ":" + NL
        s_info += "\u2502    " + f"{NL}\u2502    ".join([s for s in s_message.split(NL)]) + NL

        s_stacktrace = ""
        if b_stacktrace:
            s_stacktrace += '\u2502 Stacktrace:' + NL
            s_temp = ''.join(_traceback.format_stack()[:-1])
            s_stacktrace += f"{NL}\u2502 ".join(('\u2502 ' + s_temp).split(NL)) + NL

        s_previous = ""
        if previous_error:
            s_previous += "\u2502 Previous Error: " + type(previous_error).__name__ + NL
            s_previous += "\u2502    " + f"{NL}\u2502    ".join([s for s in str(previous_error).split(NL)]) + NL
            s_previous += '\u2502    ' + NL
            s_previous += '\u2502 Previous Stacktrace:' + NL
            s_temp = ''.join(_traceback.format_stack()[:-1] + _traceback.format_tb(previous_error.__traceback__))
            s_previous += f'{NL}\u2502 '.join(('\u2502 ' + s_temp).split(NL)) + NL

        i_longest = max([len(s) for s in (s_message + s_stacktrace + s_info + s_previous).split("\n")])

        self._s_message = (NL +
            x_line_start(i_longest+10) +
            s_previous +
            (x_line_mid(i_longest + 10) if s_previous else "") +
            s_stacktrace +
            s_info +
            x_line_end(i_longest+10)
        )

    def __str__(self):
        return self._s_message


class BfSyntaxError(Error):
    pass


class BfRuntimeError(Error):
    pass


class BfTypeError(Error):
    pass


class BfNameError(Error):
    pass


def _error_handler(exception_type, exception, traceback):
    if issubclass(exception_type, Error):
        sys.stderr.write(str(exception))

    else:
        sys.__excepthook__(exception_type, exception, traceback)


sys.excepthook = _error_handler
