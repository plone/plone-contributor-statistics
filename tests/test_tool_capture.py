import datetime

import pytest

from scripts.lib.capture import CaptureError, CaptureResult
from scripts.tools import capture as tool

URL = 'https://example.org/sprint'
LONG = 'A' * 100


def run(monkeypatch, capsys, result, argv):
    calls = []

    def fake(url, **kwargs):
        calls.append((url, kwargs))
        if isinstance(result, Exception):
            raise result
        return result

    monkeypatch.setattr(tool, 'capture', fake)
    status = tool.main(argv)
    out = capsys.readouterr()
    return status, out, calls


def test_all_found(monkeypatch, capsys):
    result = CaptureResult('example-org-sprint', True, (LONG, 'Short passage'), (), False)
    status, out, calls = run(monkeypatch, capsys, result, [URL, '--quote', 'A', '--quote', 'Short'])
    assert status == 0
    assert out.out.splitlines() == ['example-org-sprint  ' + URL, '+ ' + 'A' * 80, '+ Short passage']
    assert calls[0][0] == URL
    assert calls[0][1]['quotes'] == ['A', 'Short']
    assert calls[0][1]['refresh'] is False


def test_missing_quote_exits_1(monkeypatch, capsys):
    result = CaptureResult('s', False, (), ('gone text',), False)
    status, out, _ = run(monkeypatch, capsys, result, [URL, '--quote', 'gone text'])
    assert status == 1
    assert '! not found: gone text' in out.out.splitlines()


def test_unreachable_exits_1(monkeypatch, capsys):
    result = CaptureResult('s', True, (), (), True)
    status, out, _ = run(monkeypatch, capsys, result, [URL, '--quote', 'x'])
    assert status == 1
    assert out.out.splitlines()[-1] == '! unreachable'


def test_capture_error_goes_to_stderr(monkeypatch, capsys):
    status, out, _ = run(monkeypatch, capsys, CaptureError('boom'), [URL, '--quote', 'x'])
    assert status == 1
    assert out.err.strip() == '! boom'
    assert out.out == ''


def test_options_are_passed_on(monkeypatch, capsys):
    result = CaptureResult('s', False, (), (), False)
    _, _, calls = run(monkeypatch, capsys, result, [URL, '--quote', 'x', '--kind', 'profile', '--title', 'T',
                                                    '--date', '2020-01-02', '--refresh'])
    kwargs = calls[0][1]
    assert (kwargs['kind'], kwargs['title'], kwargs['refresh']) == ('profile', 'T', True)
    assert kwargs['date'] == datetime.date(2020, 1, 2)


def test_quote_is_required(monkeypatch, capsys):
    monkeypatch.setattr(tool, 'capture', lambda *a, **k: pytest.fail('no capture expected'))
    with pytest.raises(SystemExit) as exit_info:
        tool.main([URL])
    assert exit_info.value.code == 2


def test_cli_accepts_name_without_quote(monkeypatch, capsys):
    result = CaptureResult('example-org-sprint', True, ('Passage',), ('Nobody',), False)
    status, out, calls = run(monkeypatch, capsys, result, [URL, '--name', 'Maurits', '--name', 'Nobody'])
    assert status == 1
    assert calls[0][1]['names'] == ['Maurits', 'Nobody']
    assert calls[0][1]['quotes'] == ()
    assert '! not found: Nobody' in out.out


def test_cli_needs_a_quote_or_a_name(monkeypatch, capsys):
    with pytest.raises(SystemExit):
        run(monkeypatch, capsys, None, [URL])
