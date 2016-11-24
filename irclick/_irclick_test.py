import click
import pytest

from irclick._irclick import line_command, trailer_argument


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
    (u'arg1', {'one': None, 'arg': u'arg1', 'trailer': u''}),
    (u'hi hello', {'one': None, 'arg': u'hi', 'trailer': u'hello'}),
    (u'arg2 -1hey hi hello', {'one': u'hey', 'arg': u'arg2', 'trailer': u'hi hello'}),
    (u'-1hey arg2 hi hello', {'one': u'hey', 'arg': u'arg2', 'trailer': u'hi hello'}),
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
    assert state == expected
