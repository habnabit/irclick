# -*- coding: utf-8 -*-
"""
    click.parser
    ~~~~~~~~~~~~

    This module started out as largely a copy paste from the stdlib's
    optparse module with the features removed that we do not need from
    optparse because we implement them in Click on a higher level (for
    instance type handling, help formatting and a lot more).

    The plan is to remove more and more from here over time.

    The reason this is a different module and not optparse from the stdlib
    is that there are differences in 2.x and 3.x about the error messages
    generated and optparse in the stdlib uses gettext for no good reason
    and might cause us issues.
"""
import re
from collections import deque

from click.exceptions import UsageError, NoSuchOption, BadOptionUsage, \
     BadArgumentUsage
from click.parser import Argument, Option, normalize_opt


def _unpack_args(args, nargs_spec):
    """Given an iterable of arguments and an iterable of nargs specifications,
    it returns a tuple with all the unpacked arguments at the first index
    and all remaining arguments as the second.

    The nargs specification is the number of arguments that should be consumed
    or `-1` to indicate that this position should eat up all the remainders.

    Missing items are filled with `None`.
    """
    nargs_spec = deque(nargs_spec)
    rv = []

    while nargs_spec:
        nargs = nargs_spec.popleft()
        if nargs >= 1:
            rv.append(args.pop_nargs(nargs))
        elif nargs == -1:
            rv.append(tuple(args.pop_rest()))
        elif nargs == -2:
            rv.append((args.pop_trailer(),))
        else:
            raise RuntimeError(nargs)

    return tuple(rv), args.pop_rest()


def _error_opt_args(nargs, opt):
    if nargs == 1:
        raise BadOptionUsage(opt, '%s option requires an argument' % opt)
    raise BadOptionUsage(opt, '%s option requires %d arguments' % (opt, nargs))


class Splut(object):

    def __init__(self, match, string):
        self.match = match
        self.string = string

    @classmethod
    def of_match(cls, match):
        return cls(match, match.group(0))

    @classmethod
    def ensure(cls, obj):
        if isinstance(obj, cls):
            return obj
        else:
            return cls(None, obj)


class ParsingState(object):

    def __init__(self, line):
        self.opts = {}
        self.order = []
        self._line = line
        self._lineiter = re.finditer(u'(?u)\\S+', self._line)
        self._consuming_largs = False
        self._largs = []
        self._rargs = []

    def push_left(self, *args):
        self._largs.extend(Splut.ensure(x) for x in args)

    def push_right(self, *args):
        self._rargs[:0] = (Splut.ensure(x) for x in args)

    def shift_largs(self):
        self._consuming_largs = True

    def pop_arg(self):
        if self._consuming_largs and self._largs:
            return self._largs.pop(0)
        elif self._rargs:
            return self._rargs.pop(0)
        m = next(self._lineiter, None)
        if m is None:
            return None
        return Splut.of_match(m)

    def _pop_args(self, n):
        for i in range(n):
            arg = self.pop_arg()
            if arg is None:
                raise RuntimeError(i, n)
            yield arg

    def pop_nargs(self, n):
        ret = tuple(s.string for s in self._pop_args(n))
        if n == 1:
            [ret] = ret
        return ret

    def pop_rest(self):
        return [s.string for s in iter(self.pop_arg, None)]

    def pop_trailer(self):
        arg = self.pop_arg()
        if arg is None:
            return u''
        else:
            self._largs = []
            self._rargs = []
            self._lineiter = iter(())
            return self._line[arg.match.start():]


class OptionParser(object):
    """The option parser is an internal class that is ultimately used to
    parse options and arguments.  It's modelled after optparse and brings
    a similar but vastly simplified API.  It should generally not be used
    directly as the high level Click classes wrap it for you.

    It's not nearly as extensible as optparse or argparse as it does not
    implement features that are implemented on a higher level (such as
    types or defaults).

    :param ctx: optionally the :class:`~click.Context` where this parser
                should go with.
    """

    def __init__(self, ctx=None):
        #: The :class:`~click.Context` for this parser.  This might be
        #: `None` for some advanced use cases.
        self.ctx = ctx
        #: This controls how the parser deals with interspersed arguments.
        #: If this is set to `False`, the parser will stop on the first
        #: non-option.  Click uses this to implement nested subcommands
        #: safely.
        self.allow_interspersed_args = True
        #: This tells the parser how to deal with unknown options.  By
        #: default it will error out (which is sensible), but there is a
        #: second mode where it will ignore it and continue processing
        #: after shifting all the unknown options into the resulting args.
        self.ignore_unknown_options = False
        if ctx is not None:
            self.allow_interspersed_args = ctx.allow_interspersed_args
            self.ignore_unknown_options = ctx.ignore_unknown_options
        self._short_opt = {}
        self._long_opt = {}
        self._opt_prefixes = set(['-', '--'])
        self._args = []

    def add_option(self, opts, dest, obj, action=None, nargs=1, const=None):
        """Adds a new option named `dest` to the parser.  The destination
        is not inferred (unlike with optparse) and needs to be explicitly
        provided.  Action can be any of ``store``, ``store_const``,
        ``append``, ``appnd_const`` or ``count``.

        The `obj` can be used to identify the option in the order list
        that is returned from the parser.
        """
        opts = [normalize_opt(opt, self.ctx) for opt in opts]
        option = Option(opts, dest, action=action, nargs=nargs,
                        const=const, obj=obj)
        self._opt_prefixes.update(option.prefixes)
        for opt in option._short_opts:
            self._short_opt[opt] = option
        for opt in option._long_opts:
            self._long_opt[opt] = option

    def add_argument(self, dest, obj, nargs=1):
        """Adds a positional argument named `dest` to the parser.

        The `obj` can be used to identify the option in the order list
        that is returned from the parser.
        """
        self._args.append(Argument(dest=dest, nargs=nargs, obj=obj))

    def parse_args(self, args):
        """Parses positional arguments and returns ``(values, args, order)``
        for the parsed options and arguments as well as the leftover
        arguments if there are any.  The order is a list of objects as they
        appear on the command line.  If arguments appear multiple times they
        will be memorized multiple times as well.
        """
        state = ParsingState(args)
        try:
            self._process_args_for_options(state)
            largs = self._process_args_for_args(state)
        except UsageError:
            if self.ctx is None or not self.ctx.resilient_parsing:
                raise
        return state.opts, largs, state.order

    def _process_args_for_args(self, state):
        state.shift_largs()
        pargs, args = _unpack_args(state,
                                   [x.nargs for x in self._args])

        for idx, arg in enumerate(self._args):
            arg.process(pargs[idx], state)

        return args

    def _process_args_for_options(self, state):
        while True:
            splut = state.pop_arg()
            if splut is None:
                return
            arg = splut.string
            arglen = len(arg)
            # Double dashes always handled explicitly regardless of what
            # prefixes are valid.
            if arg == '--':
                return
            elif arg[:1] in self._opt_prefixes and arglen > 1:
                self._process_opts(splut, state)
            elif self.allow_interspersed_args:
                state.push_left(splut)
            else:
                state.push_right(splut)
                return

        # Say this is the original argument list:
        # [arg0, arg1, ..., arg(i-1), arg(i), arg(i+1), ..., arg(N-1)]
        #                            ^
        # (we are about to process arg(i)).
        #
        # Then rargs is [arg(i), ..., arg(N-1)] and largs is a *subset* of
        # [arg0, ..., arg(i-1)] (any options and their arguments will have
        # been removed from largs).
        #
        # The while loop will usually consume 1 or more arguments per pass.
        # If it consumes 1 (eg. arg is an option that takes no arguments),
        # then after _process_arg() is done the situation is:
        #
        #   largs = subset of [arg0, ..., arg(i)]
        #   rargs = [arg(i+1), ..., arg(N-1)]
        #
        # If allow_interspersed_args is false, largs will always be
        # *empty* -- still a subset of [arg0, ..., arg(i-1)], but
        # not a very interesting subset!

    def _match_long_opt(self, opt, explicit_value, state):
        if opt not in self._long_opt:
            possibilities = [word for word in self._long_opt
                             if word.startswith(opt)]
            raise NoSuchOption(opt, possibilities=possibilities)

        option = self._long_opt[opt]
        if option.takes_value:
            # At this point it's safe to modify rargs by injecting the
            # explicit value, because no exception is raised in this
            # branch.  This means that the inserted value will be fully
            # consumed.
            if explicit_value is not None:
                state.push_right(explicit_value)

            value = state.pop_nargs(option.nargs)

        elif explicit_value is not None:
            raise BadOptionUsage(opt, '%s option does not take a value' % opt)

        else:
            value = None

        option.process(value, state)

    def _match_short_opt(self, splut, state):
        arg = splut.string
        stop = False
        i = 1
        prefix = arg[0]
        unknown_options = []

        for ch in arg[1:]:
            opt = normalize_opt(prefix + ch, self.ctx)
            option = self._short_opt.get(opt)
            i += 1

            if not option:
                if self.ignore_unknown_options:
                    unknown_options.append(ch)
                    continue
                raise NoSuchOption(opt)
            if option.takes_value:
                # Any characters left in arg?  Pretend they're the
                # next arg, and stop consuming characters of arg.
                if i < len(arg):
                    state.push_right(arg[i:])
                    stop = True

                value = state.pop_nargs(option.nargs)

            else:
                value = None

            option.process(value, state)

            if stop:
                break

        # If we got any unknown options we re-combinate the string of the
        # remaining options and re-attach the prefix, then report that
        # to the state as new larg.  This way there is basic combinatorics
        # that can be achieved while still ignoring unknown arguments.
        if self.ignore_unknown_options and unknown_options:
            state.push_left(prefix + ''.join(unknown_options))

    def _process_opts(self, splut, state):
        arg = splut.string
        explicit_value = None
        # Long option handling happens in two parts.  The first part is
        # supporting explicitly attached values.  In any case, we will try
        # to long match the option first.
        if '=' in arg:
            long_opt, explicit_value = arg.split('=', 1)
        else:
            long_opt = arg
        norm_long_opt = normalize_opt(long_opt, self.ctx)

        # At this point we will match the (assumed) long option through
        # the long option matching code.  Note that this allows options
        # like "-foo" to be matched as long options.
        try:
            self._match_long_opt(norm_long_opt, explicit_value, state)
        except NoSuchOption:
            # At this point the long option matching failed, and we need
            # to try with short options.  However there is a special rule
            # which says, that if we have a two character options prefix
            # (applies to "--foo" for instance), we do not dispatch to the
            # short option code and will instead raise the no option
            # error.
            if arg[:2] not in self._opt_prefixes:
                return self._match_short_opt(splut, state)
            if not self.ignore_unknown_options:
                raise
            state.push_left(splut)
