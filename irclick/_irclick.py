import contextlib
import functools

import click
from click.utils import make_str as _make_str
from contextlib2 import ExitStack

from irclick._parser import OptionParser
from irclick._splut import Splut


def make_str(value):
    if isinstance(value, Splut):
        return value.string
    else:
        return _make_str(value)


def invoke_line(cmd, line, **kw):
    args = Splut.args_of_line(line)
    with ExitStack() as stack:
        stack.enter_context(patch(click.core, 'make_str', make_str))
        patch_all_parsers(stack, cmd)
        with cmd.make_context('bogus', args=args, **kw) as ctx:
            return cmd.invoke(ctx)


def make_parser(cmd, ctx):
    parser = OptionParser(ctx)
    parser.allow_interspersed_args = ctx.allow_interspersed_args
    parser.ignore_unknown_options = ctx.ignore_unknown_options
    for param in cmd.get_params(ctx):
        param.add_to_parser(parser, ctx)
    return parser


@contextlib.contextmanager
def patch(obj, attr, value):
    prev = getattr(obj, attr)
    try:
        setattr(obj, attr, value)
        yield
    finally:
        setattr(obj, attr, prev)


def patch_all_parsers(stack, cmd):
    stack.enter_context(
        patch(cmd, 'make_parser', functools.partial(make_parser, cmd)))
    if isinstance(cmd, click.MultiCommand):
        for subcmd in cmd.list_commands(None):
            patch_all_parsers(stack, cmd.get_command(None, subcmd))


def line_command(**kw):
    def deco(cmd):
        cmd.invoke_line = functools.partial(invoke_line, cmd)
        return cmd

    return deco


def trailer_argument(*a, **kw):
    prev_cb = kw.pop('callback', None)

    def callback(ctx, param, value):
        [value] = value
        if prev_cb is not None:
            value = prev_cb(ctx, param, value)
        return value

    kw['nargs'] = -2
    kw['callback'] = callback
    return click.argument(*a, **kw)
