import contextlib

import click

from irclick._parser import OptionParser


@contextlib.contextmanager
def patch(obj, attr, value):
    prev = getattr(obj, attr)
    try:
        setattr(obj, attr, value)
        yield
    finally:
        setattr(obj, attr, prev)


def line_command(**kw):
    def deco(cmd):
        def make_parser(ctx):
            parser = OptionParser(ctx)
            parser.allow_interspersed_args = ctx.allow_interspersed_args
            parser.ignore_unknown_options = ctx.ignore_unknown_options
            for param in cmd.get_params(ctx):
                param.add_to_parser(parser, ctx)
            return parser

        def invoke_line(line, **kw):
            with patch(cmd, 'make_parser', make_parser):
                with cmd.make_context('bogus', args=line, **kw) as ctx:
                    return cmd.invoke(ctx)

        cmd.invoke_line = invoke_line
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
