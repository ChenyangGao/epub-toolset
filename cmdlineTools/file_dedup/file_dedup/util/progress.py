#!/usr/bin/env python3
# coding: utf-8

__author__  = 'ChenyangGao <https://chenyanggao.github.io/>'
__version__ = (0, 0, 2)
__all__ = [
    "EraseLineType", "EraseScreenType", "calc_lines", "output", 
    "clear", "clear_up", "clear_down", "clear_lines", "print_iter", 
]

from enum import IntEnum
from inspect import isgeneratorfunction
from os import get_terminal_size
from re import compile as re_compile, Pattern
from sys import stdout
from typing import (
    cast, Any, Callable, Final, Generator, Iterable, Optional, 
    TypeVar, Union
)
from warnings import warn

wcwidth: Any
try:
    from cwcwidth import wcwidth # type: ignore
except ImportError:
    try:
        from wcwidth import wcwidth # type: ignore
    except ImportError:
        warn("""You need one of the following modules to ensure that the width of the character output on the terminal emulator can be calculated correctly: 
- cwcwidth: https://pypi.org/project/cwcwidth/
- wcwidth: https://pypi.org/project/wcwidth/
""")
        wcwidth = None

CRE_VT100_ESCSEQ: Final[Pattern[str]] = re_compile("\x1b[([{][0-9;]*\\w")
DEFAULT_CWMAP: Final[dict[str, int]] = {}
write = stdout.write

T = TypeVar("T")


class _Ensured_Enum_Mixin:
    @classmethod
    def ensure(cls, val, /):
        if isinstance(val, cls):
            return val
        try:
            return cls[val]
        except (KeyError, TypeError):
            return cls(val)

    @classmethod
    def map(cls, val):
        inst = cls.ensure(val)
        return cls.__VT100_ESCSEQMAP__[inst.value]


class EraseLineType(_Ensured_Enum_Mixin, IntEnum):
    current_to_end = 0
    current_to_start = 1
    entire_line = 2
    end = 0
    start = 1
    right = 0
    left = 1
    entire = 2

    __VT100_ESCSEQMAP__ = {
        0: "\x1b[K",
        1: "\x1b[1K",
        2: "\x1b[2K",
    }


class EraseScreenType(_Ensured_Enum_Mixin, IntEnum):
    erase_down = 0
    erase_up = 1
    entire_screen = 2
    down = 0
    up = 1
    end = 0
    start = 1
    entire = 2

    __VT100_ESCSEQMAP__ = {
        0: "\x1b[J",
        1: "\x1b[1J",
        2: "\x1b[2J",
    }


def calc_lines(
    text: str, /, 
    cwmap: dict[str, int] = DEFAULT_CWMAP, 
    cwcall: Callable[[str], int] = wcwidth, 
    line_width: None | int = None, 
) -> int:
    text = CRE_VT100_ESCSEQ.sub("", text)
    nrows = 1
    ncols = 0
    columns: int
    if line_width is None:
        columns = get_terminal_size().columns
    else:
        columns = line_width
    for wc in text:
        if wc == "\n":
            nrows += 1
            ncols = 0
        elif wc == "\r":
            ncols = 0
        else:
            if wc in cwmap:
                wcw = cwmap[wc]
            elif cwcall:
                wcw = cwcall(wc)
            else:
                wcw = -1
            if wcw < 0:
                raise ValueError(f"Can't determine the width of {wc!r}")
            elif wcw > columns:
                raise ValueError(f"The width of {wc!r} is too long")
            ncols += wcw
            if ncols > columns:
                nrows += 1
                ncols = wcw
    return nrows


def output(text: str, /) -> int:
    write(text)
    if wcwidth is None:
        return -1
    return calc_lines(text)


def clear(
    erase_screen_type: int | str | EraseScreenType = EraseScreenType.entire_screen, 
):
    # ANSI/VT100 Terminal Control Escape Sequences
    # See detail:
    #     - https://www.cse.psu.edu/~kxc104/class/cmpen472/16f/hw/hw8/vt100ansi.htm
    #     - https://espterm.github.io/docs/VT100%20escape%20codes.html
    # \x1b[nA   Cursor Up
    #               Moves the cursor up by *n* rows; the default count is 1.
    # \x1b[nB   Cursor Down
    #               Moves the cursor down by *n* rows; the default count is 1.
    # \x1b[nC   Cursor Forward (Right)
    #               the cursor forward by *n* columns; the default count is 1.
    # \x1b[nD   Cursor Backward(Left) 
    #               Moves the cursor backward by *n* columns; the default count is 1.
    # \x1b[x;yH Cursor Home
    #               Sets the cursor position where subsequent text will begin. 
    #               If no x(row)/y(column) parameters are provided (ie. \x1b[H), 
    #               the cursor will move to the homeposition, at the upper 
    #               left of the screen.
    # \x1b[x;yf Force Cursor Position
    #               Identical to *Cursor Home*.
    #
    # \x1b[s    Save Cursor
    #               Save current cursor position.
    # \x1b[u    Unsave Cursor
    #               Restores cursor position after a Save Cursor.
    # \x1b7     Save Cursor & Attrs
    #               Save current cursor position.
    # \x1b8     Restore Cursor & Attrs
    #               Restores cursor position after a Save Cursor.
    #
    # \x1b[K    Erase End of Line.
    #               Erases from the current cursor position to the end of the current line.
    # \x1b[1K   Erase Start of Line
    #               Erases from the current cursor position to the start of the current line.
    # \x1b[2K   Erase Line
    #               Erases the entire current line.
    # \x1b[J    Erase Down
    #               Erases the screen from the current line down to the bottom of the screen.
    # \x1b[1J   Erase Up
    #               Erases the screen from the current line up to the top of the screen.
    # \x1b[2J   Erase Screen
    #               Erases the screen with the background colour and moves the cursor to home.
    write(EraseScreenType.map(erase_screen_type))


def clear_up(
    offset: int = 0, /, 
    erase_line_type: int | str | EraseLineType = EraseLineType.current_to_end, 
    stay: bool = True, 
):
    if offset < 0:
        clear_down(-offset, erase_line_type, stay)
    elif stay:
        write(f"\x1b[{offset}A")
        clear_down(-offset, erase_line_type, False)
    else:
        escseq = EraseLineType.map(erase_line_type)
        if offset:
            write(escseq + ("\x1b[1A" + escseq) * offset)
        else:
            write(escseq)


def clear_down(
    offset: int = 0, /, 
    erase_line_type: int | str | EraseLineType = EraseLineType.current_to_end, 
    stay: bool = True, 
):
    if offset < 0:
        clear_up(-offset, erase_line_type, stay)
    elif stay:
        write(f"\x1b[{offset}B")
        clear_up(-offset, erase_line_type, stay)
    else:
        escseq = EraseLineType.map(erase_line_type)
        if offset:
            write(escseq + ("\x1b[1B" + escseq) * offset)
        else:
            write(escseq)


def clear_lines(
    count: int = 1, /, 
    upside: None | bool = None, 
):
    if count == 0:
        return
    write("\r")
    if count < 0:
        if upside is None:
            clear(EraseScreenType.entire_screen)
        elif upside:
            clear(EraseScreenType.erase_up)
        else:
            clear(EraseScreenType.erase_down)
    elif upside is None or upside:
        clear_up(count-1, stay=False)
    else:
        clear_down(count-1, stay=False)


def print_iter(
    it: Iterable[T], /, 
    genstr: Union[
        Callable[[T], Optional[str]], 
        Callable[..., Generator[Optional[str], T, Optional[str]]], 
    ] = str, 
    clear_nlines: None | int | Callable[[str], int] = None, 
) -> Generator[T, None, None]:
    msg: Optional[str]
    last_nlines: int
    calc_nlines: None | Callable[[str], int]
    if clear_nlines is None:
        calc_nlines = calc_lines
    elif callable(clear_nlines):
        calc_nlines = clear_nlines
    else:
        calc_nlines = None
        last_nlines = cast(int, clear_nlines)
    isgen = isgeneratorfunction(genstr)
    first_loop = True
    if isgen:
        gen = cast(
            Callable[..., Generator[Optional[str], T, Optional[str]]], 
            genstr, 
        )()
        if (msg := next(gen)) is not None:
            write(msg)
            if calc_nlines is not None:
                last_nlines = calc_lines(msg)
            first_loop = False
        genstr = gen.send
    genstr = cast(Callable[[T], Optional[str]], genstr)
    try:
        for i in it:
            yield i
            if (msg := genstr(i)) is not None:
                if first_loop:
                    first_loop = False
                else:
                    clear_lines(last_nlines)
                write(msg)
                if calc_nlines is not None:
                    last_nlines = calc_lines(msg)
    except GeneratorExit:
        pass
    except StopIteration as e:
        if isgen:
            if e.args and e.args[0] is not None:
                if not first_loop:
                    clear_lines(last_nlines)
                write(e.args[0])
        return
    if isgen:
        try:
            gen.throw(GeneratorExit)
        except StopIteration as e:
            if e.args and e.args[0] is not None:
                if not first_loop:
                    if last_nlines:
                        clear_lines(last_nlines)
                write(e.args[0])


if __name__ == "__main__":
    from functools import partial
    from time import perf_counter, sleep
    from typing import Any

    _: Any
    g: Any

    def gen_count_time(total="?"):
        start_t = perf_counter()
        n = 1
        _ = yield
        try:
            while True:
                _ = yield f"""\
PROCESSED: {n}/{total}
COST: {perf_counter() - start_t:.6f} s
"""
                n += 1
        except StopIteration:
            return f"""\
[FAILED] PROCESSED PARTIAL
    TOTAL: {n}
    COST: {perf_counter() - start_t:.6f} s
"""
        except GeneratorExit:
            return f"""\
[SUCCESS] PROCESSED ALL
    TOTAL: {n}
    COST: {perf_counter() - start_t:.6f} s
"""

    def gen_batch_count_time(total="?"):
        start_t = perf_counter()
        n = 0
        t = 0
        i = yield
        try:
            while True:
                n += 1
                t += len(i)
                i = yield f"""\
BATCH: {n}/{total}
PROCESSED: {t}
COST: {perf_counter() - start_t:.6f} s
"""
        except StopIteration:
            return f"""\
[FAILED] PROCESSED PARTIAL
    BATCHS: {n}
    TOTAL: {t}
    COST: {perf_counter() - start_t:.6f} s
"""
        except GeneratorExit:
            return f"""\
[SUCCESS] PROCESSED ALL
    BATCHS: {n}
    TOTAL: {t}
    COST: {perf_counter() - start_t:.6f} s
"""

    print("😄 process 10 elements")
    for _ in print_iter(range(10), partial(gen_count_time, total=10)):
        sleep(.1)

    print("😂 process 10 elements, failed after the 5th")
    g = print_iter(range(10), partial(gen_count_time, total=10))
    for i, _ in enumerate(g):
        sleep(.1)
        if i == 5:
            g.close()

    print("🤭 process 10 batches, the latter "
          "batch has 1 more element than the previous one")
    for _ in print_iter([range(i) for i in range(10)], partial(gen_batch_count_time, total=10)):
        sleep(.1)

    print("😢 process 10 batches, failed after the 5th")
    g = print_iter([range(i) for i in range(10)], partial(gen_batch_count_time, total=10))
    for i, _ in enumerate(g):
        sleep(.1)
        if i == 5:
            g.close()

