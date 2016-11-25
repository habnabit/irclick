# Copyright (c) Aaron Gallagher <_@habnab.it>
# See LICENSE for details.

import click
import pytest
from click.exceptions import BadOptionUsage

from irclick import line_command, trailer_argument


@pytest.mark.parametrize(('line', 'expected'), [
    (u'', {'one': None}),
    (u'-1 hey', {'one': u'hey'}),
    (u'--one hi', {'one': u'hi'}),
    (u'-1hello', {'one': u'hello'}),
])
def test_cmd1(line, expected):
    state = {}

    @line_command()
    @click.command()
    @click.option('-1', '--one')
    def cmd1(one):
        assert not state
        state.update(one=one)

    cmd1.invoke_line(line)
    assert state == expected


@pytest.mark.parametrize(('line', 'expected'), [
    (u'', {'one': None, 'trailer': u''}),
    (u'hi hello', {'one': None, 'trailer': u'hi hello'}),
    (u'-1hey hi hello', {'one': 'hey', 'trailer': u'hi hello'}),
])
def test_trailer(line, expected):
    state = {}

    @line_command()
    @click.command()
    @click.option('-1', '--one')
    @trailer_argument('trailer')
    def cmd1(one, trailer):
        assert not state
        state.update(one=one, trailer=trailer)

    cmd1.invoke_line(line)
    assert state == expected


@pytest.mark.parametrize(('line', 'expected'), [
    (u'arg1', {'arg': u'arg1'}),
    (u'hi hello', {'arg': u'hi', 'trailer': u'hello'}),
    (u'arg2 -1hey hi hello', {'one': u'hey', 'arg': u'arg2', 'trailer': u'hi hello'}),
    (u'-1hey arg2 hi hello', {'one': u'hey', 'arg': u'arg2', 'trailer': u'hi hello'}),
    (u'-- -1hey arg2 hi hello', {'arg': u'-1hey', 'trailer': u'arg2 hi hello'}),
    (u'-1hey -- arg2 hi hello', {'one': u'hey', 'arg': u'arg2', 'trailer': u'hi hello'}),
    (u'-1hey arg2 -- hi hello', {'one': u'hey', 'arg': u'arg2', 'trailer': u'hi hello'}),
    (u'-1hey arg2 hi -- hello', {'one': u'hey', 'arg': u'arg2', 'trailer': u'hi -- hello'}),
])
def test_trailer_and_arg(line, expected):
    state = {}

    @line_command()
    @click.command()
    @click.option('-1', '--one')
    @click.argument('arg')
    @trailer_argument('trailer')
    def cmd1(one, arg, trailer):
        assert not state
        state.update(one=one, arg=arg, trailer=trailer)

    cmd1.invoke_line(line)
    assert {k: v for k, v in state.items() if v} == expected


@pytest.mark.parametrize(('line', 'expected'), [
    (u'scmd1 hi hello', {'cmd': 'scmd1', 'trailer': u'hi hello'}),
    (u'scmd2 hello hi', {'cmd': 'scmd2', 'trailer': u'hello hi'}),
    (u'-2 scmd2 hey', {'two': True, 'cmd': 'scmd2', 'trailer': u'hey'}),
])
def test_subcommand(line, expected):
    state = {}

    @line_command()
    @click.option('-2', '--two/--no-two')
    @click.group()
    def cmd1(two):
        assert not state
        state.update(two=two)

    @cmd1.command()
    @trailer_argument('trailer')
    def scmd1(trailer):
        assert list(state.keys()) == ['two']
        state.update(cmd='scmd1', trailer=trailer)

    @cmd1.command()
    @trailer_argument('trailer')
    def scmd2(trailer):
        assert list(state.keys()) == ['two']
        state.update(cmd='scmd2', trailer=trailer)

    cmd1.invoke_line(line)
    assert {k: v for k, v in state.items() if v} == expected


@pytest.mark.parametrize(('line', 'expected'), [
    (u'-21hey', {'one': u'hey', 'two': True}),
    (u'-12hey', {'one': u'2hey'}),
    (u'--one=--two', {'one': u'--two'}),
    (u'-1=-2', {'one': u'=-2'}),
    (u'-21=-2', {'one': u'=-2', 'two': True}),
    (u'--two=two', BadOptionUsage),
])
def test_flag_miscellany(line, expected):
    state = {}

    @line_command()
    @click.command()
    @click.option('-1', '--one')
    @click.option('-2', '--two/--no-two')
    def cmd1(one, two):
        assert not state
        state.update(one=one, two=two)

    if isinstance(expected, type):
        with pytest.raises(expected):
            cmd1.invoke_line(line)
        assert state == {}
    else:
        cmd1.invoke_line(line)
        assert {k: v for k, v in state.items() if v} == expected


@pytest.mark.parametrize(('line', 'expected'), [
    (u'one', {'arg1': u'one', 'arg2': ()}),
    (u'one two', {'arg1': u'one', 'arg2': (u'two',)}),
    (u'one two three', {'arg1': u'one', 'arg2': (u'two', 'three')}),
])
def test_varargs(line, expected):
    state = {}

    @line_command()
    @click.command()
    @click.argument('arg1')
    @click.argument('arg2', nargs=-1)
    def cmd1(arg1, arg2):
        assert not state
        state.update(arg1=arg1, arg2=arg2)

    cmd1.invoke_line(line)
    assert state == expected
