#!/usr/bin/env python3
# coding: utf-8

__author__  = 'ChenyangGao <https://chenyanggao.github.io/>'
__version__ = (0, 0, 2)
__all__ = [
    "calc_lines", "output", "clear_lines", "clear_last_lines", 
    "print_iter", 
]

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
write = stdout.write

T = TypeVar("T")


def calc_lines(
    text: str, /, 
    cwmap: None | dict[str, int] = None, 
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
            if cwmap and wc in cwmap:
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


def clear_lines(offset: int = 0, /):
    if offset > 0:
        write(f"\x1b[{offset}B")
    elif offset < 0:
        offset = -offset
    write("\r\x1b[K")
    if offset:
        write("\x1b[1A\x1b[K" * offset)


def clear_last_lines(offset: int = 0, /):
    clear_lines(-offset)


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
                    # TODO: Up to the top.
                    if last_nlines < 0:
                        clear_last_lines(get_terminal_size().lines-1)
                    else:
                        clear_last_lines(last_nlines-1)
                write(msg)
                if calc_nlines is not None:
                    last_nlines = calc_lines(msg)
    except GeneratorExit:
        pass
    except StopIteration as e:
        if isgen:
            if e.args and e.args[0] is not None:
                if not first_loop:
                    if last_nlines < 0:
                        clear_last_lines(get_terminal_size().lines-1)
                    else:
                        clear_last_lines(last_nlines-1)
                write(e.args[0])
        return
    if isgen:
        try:
            gen.throw(GeneratorExit)
        except StopIteration as e:
            if e.args and e.args[0] is not None:
                if not first_loop:
                    if last_nlines:
                        if last_nlines < 0:
                            clear_last_lines(get_terminal_size().lines-1)
                        else:
                            clear_last_lines(last_nlines-1)
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
                _ = yield f"PROCESSED: {n}/{total}\nCOST: {perf_counter() - start_t:.6f} s\n"
                n += 1
        except StopIteration:
            return f"[FAILED] PROCESSED PARTIAL\n    TOTAL: {n}\n    COST: {perf_counter() - start_t:.6f} s\n"
        except GeneratorExit:
            return f"[SUCCESS] PROCESSED ALL\n    TOTAL: {n}\n    COST: {perf_counter() - start_t:.6f} s\n"

    def gen_batch_count_time(total="?"):
        start_t = perf_counter()
        n = 0
        t = 0
        i = yield
        try:
            while True:
                n += 1
                t += len(i)
                i = yield f"BATCH: {n}/{total}\nPROCESSED: {t}\nCOST: {perf_counter() - start_t:.6f} s\n"
        except StopIteration:
            return f"[FAILED] PROCESSED PARTIAL\n    BATCHS: {n}\n    TOTAL: {t}\n    COST: {perf_counter() - start_t:.6f} s\n"
        except GeneratorExit:
            return f"[SUCCESS] PROCESSED ALL\n    BATCHS: {n}\n    TOTAL: {t}\n    COST: {perf_counter() - start_t:.6f} s\n"

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

