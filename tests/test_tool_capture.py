import datetime
import json

import pytest

from scripts.lib.capture import CaptureError, CaptureResult
from scripts.lib.model import Source, write_source
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


def write_lines(path, *rows):
    path.write_text(''.join(json.dumps(row) + '\n' for row in rows))


def read_lines(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def record(sid):
    """Write a row for the source, as a capture that stored something does."""
    write_source(Source(sid, 'page', 'A page', datetime.date(2015, 3, 12), 'https://e.org/' + sid, None,
                        datetime.datetime(2026, 10, 22, tzinfo=datetime.timezone.utc), None))


def run_batch(monkeypatch, tmp_repo, work, results=(), outcome=None):
    """Run the batch over the work list with a fake capture; a result names a source that the capture recorded."""
    worklist, out = tmp_repo / 'work.jsonl', tmp_repo / 'results.jsonl'
    write_lines(worklist, *work)
    if results:
        write_lines(out, *results)
    calls = []

    def fake(url, **kwargs):
        calls.append((url, kwargs))
        if outcome is not None:
            return outcome(url)
        record('id-' + url[-1])
        return CaptureResult('id-' + url[-1], True, (LONG,), (), False)

    monkeypatch.setattr(tool, 'capture', fake)
    status = tool.main(['--batch', str(worklist), '--results', str(out)])
    return status, calls, out


def test_batch_writes_one_result_per_url(monkeypatch, tmp_repo):
    work = [{'url': 'https://e.org/1', 'quotes': ['q'], 'names': [], 'kind': None},
            {'url': 'https://e.org/2', 'quotes': [], 'names': ['N'], 'kind': 'profile'}]
    status, calls, out = run_batch(monkeypatch, tmp_repo, work)
    assert status == 0
    assert [row['url'] for row in read_lines(out)] == ['https://e.org/1', 'https://e.org/2']
    assert read_lines(out)[0] == {'url': 'https://e.org/1', 'source_id': 'id-1', 'created': True, 'added': [LONG],
                                  'missing': [], 'unreachable': False, 'error': None}
    assert calls[1][1]['names'] == ['N'] and calls[1][1]['kind'] == 'profile' and calls[0][1]['quotes'] == ['q']
    assert calls[0][1]['fetcher'] is calls[1][1]['fetcher']
    assert calls[0][1]['session'] is calls[1][1]['session']


def test_batch_resumes_after_interruption(monkeypatch, tmp_repo):
    work = [{'url': 'https://e.org/1', 'quotes': ['q']}, {'url': 'https://e.org/2', 'quotes': ['q']}]
    done = {'url': 'https://e.org/1', 'source_id': 'id-1', 'created': True, 'added': [], 'missing': [],
            'unreachable': False, 'error': None}
    status, calls, out = run_batch(monkeypatch, tmp_repo, work, results=[done])
    assert status == 0
    assert [url for url, _ in calls] == ['https://e.org/2']
    assert [row['url'] for row in read_lines(out)] == ['https://e.org/1', 'https://e.org/2']


def test_batch_records_errors_and_continues(monkeypatch, tmp_repo):
    def outcome(url):
        if url.endswith('1'):
            raise CaptureError('boom')
        if url.endswith('2'):
            raise ValueError('bad cell')
        record('id-3')
        return CaptureResult('id-3', False, (), ('gone',), False)

    work = [{'url': f'https://e.org/{n}', 'quotes': ['q']} for n in (1, 2, 3)]
    status, _, out = run_batch(monkeypatch, tmp_repo, work, outcome=outcome)
    assert status == 0
    first, second, third = read_lines(out)
    assert first == {'url': 'https://e.org/1', 'source_id': None, 'created': False, 'added': [], 'missing': [],
                     'unreachable': False, 'error': 'boom'}
    assert second == {'url': 'https://e.org/2', 'source_id': None, 'created': False, 'added': [], 'missing': [],
                      'unreachable': False, 'error': 'unexpected: ValueError: bad cell'}
    assert third['source_id'] == 'id-3' and third['missing'] == ['gone'] and third['error'] is None


def test_batch_names_no_source_that_was_not_recorded(monkeypatch, tmp_repo):
    """A new source of which nothing was found is not in the register: its result has no id."""
    def outcome(url):
        return CaptureResult('id-' + url[-1], False, (), ('not on the page',), False)

    status, _, out = run_batch(monkeypatch, tmp_repo, [{'url': 'https://e.org/1', 'quotes': ['not on the page']}],
                               outcome=outcome)
    assert status == 0
    assert read_lines(out) == [{'url': 'https://e.org/1', 'source_id': None, 'created': False, 'added': [],
                                'missing': ['not on the page'], 'unreachable': False, 'error': None}]


def test_batch_resumes_after_truncated_line(monkeypatch, tmp_repo):
    worklist, out = tmp_repo / 'work.jsonl', tmp_repo / 'results.jsonl'
    write_lines(worklist, {'url': 'https://e.org/1', 'quotes': ['q']})
    out.write_text('{"url": "https://e.org/1", "sour')
    monkeypatch.setattr(tool, 'capture', lambda url, **kw: CaptureResult('s', True, (), (), False))
    assert tool.main(['--batch', str(worklist), '--results', str(out)]) == 0
    assert json.loads(out.read_text().splitlines()[-1])['url'] == 'https://e.org/1'


def test_batch_arguments_go_together(capsys):
    with pytest.raises(SystemExit):
        tool.main(['--batch', 'w.jsonl'])
    with pytest.raises(SystemExit):
        tool.main(['--batch', 'w.jsonl', '--results', 'r.jsonl', URL])
    with pytest.raises(SystemExit):
        tool.main(['--batch', 'w.jsonl', '--results', 'r.jsonl', '--quote', 'x'])
