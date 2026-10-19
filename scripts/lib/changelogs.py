"""Read changelog entries and the names they credit (#71).

Plone's changelogs have one section per release, with one bullet per change.
From mid-2003 on, an entry ends with the name of the person who made the
change in brackets, "[limi]"; from 2016 on, towncrier entries end with
"@login". This module finds the changelog files, parses their sections and
entries, extracts the names, and maps the names to people.

An entry is dated by the release header it sits under, or by the tag of the
release when the header has no date. Entries without a release date are
unreleased and don't count.

Each entry exists several times: on every later release branch, in moved
files, and in copies between repositories. `deduplicate` keeps one per
change, see docs/explanation/counting-rules.md.
"""

import hashlib
import re
import unicodedata
from collections import defaultdict
from dataclasses import dataclass, field

# The years in which the names in changelogs are a measure of their own: from 2004 on, almost every
# entry names a person; from 2013 on, pull requests take over, and from 2016 on, the entries repeat them.
# See docs/explanation/history-and-coverage.md.
REPORTED_YEARS = range(2004, 2013)

# Changelog files at any depth: CHANGES.rst, HISTORY.txt, docs/HISTORY.txt, CHANGELOG.md, ...
CHANGELOG_FILE = re.compile(r'^(HISTORY|CHANGES|CHANGELOG|CHANGE_LOG)(\.(txt|rst|md))?$', re.I)
# Folders that hold vendored code, build output or copies, not the repository's own changelog
SKIP_DIRS = {'node_modules', 'vendor', 'bower_components', '.git', 'eggs', 'parts', 'dist', 'build', 'components',
             'plone_3rdparty', 'thirdparty', '3rdparty', 'debian', 'static', 'js', 'lib', 'libs', 'external',
             'contrib'}
# Test fixtures, templates, examples and vendored copies are no changelogs of the repository
SKIP_PATH = re.compile(r'(^|/)(tests?|testing|_resources|fixtures?|skeleton|base_skeleton|templates?|examples?)(/|$)'
                       r'|\{\{|fake-project|bobtemplates\.plone/|develop/plone/content/history|jscalendar', re.I)
# Further files that are no changelog of their repository, with the reason
SKIP_FILES = {
    ('buildout.coredev', 'release/changelog.txt'): 'the changes of all core packages, aggregated for a Plone release',
}
# GNU-style ChangeLogs ("2005-01-22  Name  <email>", then "* file: text") are not parsed yet
GNU_RECORD = re.compile(r'^\d{4}-\d\d-\d\d\s+[^<\n]+<[^>\n]+@[^>\n]+>\s*$', re.M)

# Entries that are no change, and names that are no person
PLACEHOLDER = re.compile(r'^\s*(\*?add item here\*?|nothing changed yet\.?|no changes( yet)?\.?|\(?unreleased\)?)\s*$',
                         re.I)
NOT_PERSON = {'plone devs', 'plone dev', 'zopeskel', 'plone', 'bobtemplates.plone', 'mister-roboto', 'dependabot',
              'pre-commit-ci', 'plone/meta', 'plone community', 'various', 'unknown', 'anonymous', 'team'}
# Name forms that are often no name, such as "(hopefully)": they count only when every name maps to a person
WEAK_VARIANTS = {'paren', 'dash'}
# Copies of the same text in two repositories are one entry if the text is at least this long
CROSS_REPOSITORY_LENGTH = 60

UNDERLINE = re.compile(r'^\s*([=\-~^*#+`\'"])\1{2,}\s*$')
VERSION = re.compile(r'(?<![\w.])v?(\d+\.\d+(?:\.\d+)*(?:[-.]?(?:alpha|beta|rc|final|a|b|c|dev|post|p)\.?\d*)*)(?![\w.])',
                     re.I)
BULLET = re.compile(r'^(\s*)(?:[-*+•]|\d+[.)])\s+(.*)$')
MD_HEADER = re.compile(r'^\s{0,3}#{1,6}\s+(.*?)\s*#*\s*$')
UNRELEASED = re.compile(r'unreleased|not released|unknown|in development|in progress|\bxxxx|\byyyy|\bnot yet|\btbd\b'
                        r'|\(unpublished', re.I)
OLD_HEADER = re.compile(r'(?i)released|^plone\b|^version\b|^v?\d+\.\d|^(rc|beta|alpha)\d*\b|unreleased|\(\d{4}-')
MONTHS = {m: i for i, m in enumerate(
    ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'], 1)}
MONTHS.update({'mai': 5, 'okt': 10, 'dez': 12, 'mrz': 3, 'mär': 3, 'mae': 3, 'sept': 9})


@dataclass
class Entry:
    """One entry of a changelog file, with the release header it sits under."""
    text: str
    header: str
    line: int
    version: str = ''
    release_date: str = ''
    unreleased: bool = False


@dataclass
class Occurrence:
    """An entry in one file of one branch, with its date, names and where it is."""
    repository: str
    path: str
    branch: str
    default: bool
    commit: str
    line: int
    text: str
    release_date: str
    date_source: str
    names: list = field(default_factory=list)
    variant: str = 'none'

    @property
    def year(self):
        return self.release_date[:4]

    @property
    def text_hash(self):
        return text_hash(self.text)

    @property
    def url(self):
        """The entry on GitHub, at the commit of the branch tip."""
        return f'https://github.com/plone/{self.repository}/blob/{self.commit}/{self.path}#L{self.line}'


# Files


def is_changelog_file(repository, path):
    """True for a changelog file of the repository itself."""
    parts = path.split('/')
    if any(part.lower() in SKIP_DIRS for part in parts[:-1]):
        return False
    if (repository, path) in SKIP_FILES or SKIP_PATH.search(path):
        return False
    return bool(CHANGELOG_FILE.match(parts[-1]))


def is_gnu_changelog(text):
    """True for a GNU-style ChangeLog, which has dated records instead of release sections."""
    return len(GNU_RECORD.findall(text)) >= 2 and not any(UNDERLINE.match(line) for line in text.splitlines())


def decode(data):
    """The text of a file; old files are often Latin-1."""
    try:
        return data.decode('utf-8')
    except UnicodeDecodeError:
        return data.decode('latin-1')


# Dates


def _month(word):
    word = word.lower()[:4]
    return MONTHS.get(word) or MONTHS.get(word[:3])


def parse_date(text):
    """The release date of a header as YYYY-MM-DD, YYYY-MM or YYYY, or '' if it has none.

    Month names match by their first three letters, so that typos such as "Febuary" pass.
    """
    m = re.search(r'\b((?:19|20)\d\d)[-/.](\d{1,2})[-/.](\d{1,2})\b', text)
    if m:
        y, mo, d = map(int, m.groups())
        if 1 <= mo <= 12 and 1 <= d <= 31:
            return f'{y:04d}-{mo:02d}-{d:02d}'
    m = re.search(r'\b(\d{1,2})[./](\d{1,2})[./]((?:19|20)\d\d)\b', text)
    if m:
        a, b, y = map(int, m.groups())
        d, mo = (a, b) if b <= 12 else (b, a)
        if 1 <= mo <= 12:
            return f'{y:04d}-{mo:02d}-{d:02d}'
    m = re.search(r'\b([A-Za-zä]{3,9})\.?\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+((?:19|20)\d\d)\b', text)
    if m and _month(m.group(1)):
        return f'{int(m.group(3)):04d}-{_month(m.group(1)):02d}-{int(m.group(2)):02d}'
    m = re.search(r'\b(\d{1,2})(?:st|nd|rd|th)?\.?\s+([A-Za-zä]{3,9})\.?,?\s+((?:19|20)\d\d)\b', text)
    if m and _month(m.group(2)):
        return f'{int(m.group(3)):04d}-{_month(m.group(2)):02d}-{int(m.group(1)):02d}'
    m = re.search(r'\b([A-Za-zä]{3,9})\.?,?\s+((?:19|20)\d\d)\b', text)
    if m and _month(m.group(1)):
        return f'{int(m.group(2)):04d}-{_month(m.group(1)):02d}'
    m = re.search(r'\b((?:19|20)\d\d)\b', text)
    if m:
        return m.group(1)
    return ''


# Sections and entries


def is_header_text(text):
    """A release header: short, with a version number, or saying that it is (un)released."""
    s = text.strip().strip('*_`').strip()
    if not s or len(s) > 140:
        return False
    if BULLET.match(text) and not re.match(r'^\s*\d+\.\d', text):
        return False
    return (bool(VERSION.search(s)) or bool(UNRELEASED.search(s) and len(s) < 60)
            or bool(re.search(r'(?i)\breleased\b.*\b(19|20)\d\d\b', s) and len(s) < 80))


def parse_changelog(text):
    """The entries of a changelog file, each with the release header it sits under.

    Headers are RST titles with an underline, Markdown headings, and the old
    flush-left lines such as "Plone 2.0.5 - Released December 1, 2004".
    Headings that are no release, such as "Bug fixes:", keep the current
    release. An entry is a bullet with its continuation lines.
    """
    lines = text.replace('\r\n', '\n').replace('\r', '\n').replace('\t', '    ').split('\n')
    header = None
    entry = None  # [indent, lines, blank line seen, line number]
    found = []

    def flush():
        nonlocal entry
        if entry and header is not None:
            body = '\n'.join(entry[1]).strip()
            if body:
                found.append((header, body, entry[3]))
        entry = None

    i = 0
    while i < len(lines):
        line = lines[i]
        following = lines[i + 1] if i + 1 < len(lines) else ''
        stripped = line.strip()
        # An RST title: a line followed by an underline
        if (stripped and UNDERLINE.match(following) and not UNDERLINE.match(line) and len(stripped) <= 140
                and not BULLET.match(line)):
            flush()
            if is_header_text(stripped):
                header = stripped
            i += 2
            continue
        m = MD_HEADER.match(line)
        if m:
            flush()
            if is_header_text(m.group(1)):
                header = m.group(1).strip()
            i += 1
            continue
        indent = len(line) - len(line.lstrip(' '))
        # The old style: a flush-left line with a version or "released", not a bullet
        if (stripped and indent <= 3 and not BULLET.match(line) and is_header_text(stripped)
                and (entry is None or entry[2] or indent <= entry[0]) and OLD_HEADER.search(stripped)):
            flush()
            header = stripped.rstrip(':')
            i += 1
            continue
        bullet = BULLET.match(line)
        if bullet and (entry is None or len(bullet.group(1)) <= entry[0]):
            flush()
            entry = [len(bullet.group(1)), [bullet.group(2)], False, i + 1]
        elif not stripped:
            if entry:
                entry[2] = True
        elif entry is not None:
            if not entry[2] or indent > entry[0]:
                entry[1].append(stripped)
                entry[2] = False
            else:
                flush()
        i += 1
    flush()

    entries = []
    for header, body, line in found:
        date = parse_date(header)
        version = VERSION.search(header)
        entries.append(Entry(text=body, header=header, line=line, version=version.group(1) if version else '',
                             release_date=date, unreleased=bool(UNRELEASED.search(header)) and not date))
    return entries


# Names

REF = re.compile(
    r'(?:\s*[\(\[]?\s*(?:(?:closes|fixes|fix|refs|ref|see|issue|ticket|pr|pull request|gh)\s*:?\s*)?'
    r'(?:#\d+|[\w.\-]+/[\w.\-]+#\d+|https?://\S+|`[^`]*<https?://[^>]+>`_|:(?:issue|pr):`\d+`)'
    r'(?:\s*,\s*(?:#\d+|https?://\S+))*\s*[\)\]]?[.,;]?)\s*$', re.I)
NOT_NAME = re.compile(r'https?:|#\d|^\d+$|^x$|^ ?$|ci skip|skip ci|wip|^see |^fixes|^closes|\.py$|\.pt$|\.zcml$'
                      r'|^\w+\.\w+\.\w+', re.I)
SPLIT = re.compile(r'\s*(?:,|;|&|\+|/|\band\b|\bund\b|\bwith\b)\s*', re.I)
NOT_PAREN_NAME = re.compile(r'(?i)^(again|optional|experimental|deprecated|backport|bbb|merged?|default|thanks.*|see.*'
                            r'|untested|internal|partial.*|wip|work in progress|unused|unreleased|required)$')


def strip_refs(text):
    """The entry without trailing issue and pull request references such as "(#123)" or URLs."""
    previous = None
    text = text.rstrip()
    while previous != text:
        previous = text
        text = REF.sub('', text).rstrip()
    return text


def looks_like_names(content):
    content = content.strip()
    if not content or len(content) > 80 or NOT_NAME.search(content):
        return False
    parts = [p for p in SPLIT.split(content) if p]
    if not parts:
        return False
    for part in parts:
        words = part.strip().lstrip('@').split()
        if not words or len(words) > 4:
            return False
        if not all(re.match(r"^[\w.\-'’]+$", w) or re.match(r'^<?[\w.+\-]+@[\w.\-]+>?$', w) for w in words):
            return False
    return True


def split_names(content):
    """The names in "[a, b]", "[a and b]", "[a/b]" or "[applied by kleist]"."""
    names = []
    for part in SPLIT.split(content.strip()):
        part = part.strip().strip('.').lstrip('@').strip()
        part = re.sub(r'^(?:thanks to|thanks|by|from|patch by|reported by|applied by)\s+', '', part, flags=re.I)
        if part and part.lower() not in ('others', 'other', 'all', 'and', 'et al', 'team'):
            names.append(part)
    return names


def extract_names(text):
    """The names an entry credits, and the form they have.

    Forms: `bracket_end` "[name]" at the end, also "[a] [b]"; `bracket_line`
    "[name]" on its own line before other text such as URLs; `at` "@login";
    `dash` "-- name"; `paren` "(name)"; `email`; and `none`.
    Names that are no person, such as "[plone devs]", are left out.
    """
    names, variant = _names(text)
    return [n for n in names if n.lower() not in NOT_PERSON], variant


def _names(text):
    t = strip_refs(text)
    m = re.search(r'((?:\s*\[[^\[\]]+\](?!\())+)\s*[.]?\s*$', t)
    if m:
        groups = re.findall(r'\[([^\[\]]+)\]', m.group(1))
        names = [n for g in groups if looks_like_names(g) for n in split_names(g)]
        if names:
            return names, 'bracket_end'
    for line in reversed(t.split('\n')):
        m = re.match(r'^\s*\[([^\[\]]+)\]\s*$', line)
        if m and looks_like_names(m.group(1)):
            return split_names(m.group(1)), 'bracket_line'
    m = re.search(r'((?:@[\w\-]+[\s,]*(?:and\s+)?)+)[.]?\s*$', t)
    if m:
        return re.findall(r'@([\w\-]+)', m.group(1)), 'at'
    m = re.search(r'\s--\s*([^-\n][^\n]{0,60})$', t)
    if m and looks_like_names(m.group(1)):
        return split_names(m.group(1)), 'dash'
    m = re.search(r'\(([^()]+)\)\s*[.]?\s*$', t)
    if (m and looks_like_names(m.group(1)) and not re.search(r'\d|\n', m.group(1))
            and all(len(p.split()) == 1 or all(w[:1].isupper() for w in p.split()) for p in split_names(m.group(1)))
            and not NOT_PAREN_NAME.match(m.group(1).strip())):
        return split_names(m.group(1)), 'paren'
    m = re.search(r'<?([\w.+\-]+@[\w\-]+(?:\.[\w\-]+)+)>?\s*$', t)
    if m:
        return [m.group(1)], 'email'
    return [], 'none'


# Deduplication


def normalise(text):
    """The text to compare entries: NFKC, lower case, without RST and Markdown emphasis, whitespace collapsed."""
    text = unicodedata.normalize('NFKC', text).lower()
    text = re.sub(r'[`*_]', '', text)
    return re.sub(r'\s+', ' ', text).strip()


def text_hash(text):
    return hashlib.sha1(normalise(text).encode()).hexdigest()[:16]


def _earliest(occurrence):
    """The order in which an occurrence wins: dated first, earliest release, default branch, then by place."""
    return (occurrence.release_date or '9999', not occurrence.default, occurrence.branch, occurrence.repository,
            occurrence.path, occurrence.line)


def deduplicate(occurrences):
    """One occurrence per change, the earliest dated one.

    Within a repository, the same text (names included) is one entry, over all
    branches and files. Across repositories, the same text is one entry when
    it is at least CROSS_REPOSITORY_LENGTH characters long, or when both
    copies have the same release date: short generic texts such as "Initial
    release [hannosch]" stay separate in packages released on different days.
    """
    by_repository = defaultdict(list)
    for occurrence in occurrences:
        by_repository[(occurrence.repository, occurrence.text_hash)].append(occurrence)
    firsts = [min(group, key=_earliest) for group in by_repository.values()]

    across = defaultdict(list)
    for occurrence in firsts:
        if len(normalise(occurrence.text)) >= CROSS_REPOSITORY_LENGTH:
            key = occurrence.text_hash
        else:
            key = (occurrence.text_hash, occurrence.release_date or occurrence.repository)
        across[key].append(occurrence)
    return sorted((min(group, key=_earliest) for group in across.values()), key=_earliest)


def dated(entry, tag_dates):
    """(release date, date source) of an entry: the header, else the tag of its version."""
    if entry.release_date:
        return entry.release_date, 'header'
    if entry.unreleased:
        return '', 'unreleased'
    if entry.version and entry.version in tag_dates:
        return tag_dates[entry.version], 'tag'
    return '', 'missing'


def occurrences_in_file(repository, path, branch, default, commit, text, tag_dates):
    """The occurrences of the entries of one changelog file, without placeholders."""
    found = []
    for entry in parse_changelog(text):
        if PLACEHOLDER.match(entry.text):
            continue
        release_date, source = dated(entry, tag_dates)
        names, variant = extract_names(entry.text)
        found.append(Occurrence(repository=repository, path=path, branch=branch, default=default, commit=commit,
                                line=entry.line, text=entry.text, release_date=release_date, date_source=source,
                                names=names, variant=variant))
    return found


# Names to people

SVN_DOMAIN = re.compile(r'^(localhost|[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
                        r'|users\.sourceforge\.net)$')
UNMATCHED = 'unmatched'
BOT = 'bot'


def fold(name):
    """A name to compare: lower case, without accents and extra whitespace."""
    name = unicodedata.normalize('NFKD', name)
    name = ''.join(c for c in name if not unicodedata.combining(c))
    return ' '.join(name.split()).lower()


class NameMapper:
    """Maps a changelog name to a person: a GitHub login, or the name of a person without one.

    The layers, in order:
    1. `changelog_names`: curated/mappings/changelog_names.csv
    2. `commit_authors`: curated/mappings/commit_authors.csv, by the local part of a
       Subversion address (`name@localhost`), by the person's name, or by the address itself
    3. `account_aliases`: a second account, counted for the main account
    4. `bot_accounts`: a bot; dropped
    5. `login`: a login that has commits or pull requests in collected/contributors
    6. `fullname`: curated/mappings/mapping-github-username-to-fullname.csv
    A name that no layer maps stays as written, `unmatched`. Aliases and bots
    apply to the result of every layer.
    """

    def __init__(self, changelog_names, commit_authors, commit_author_names, aliases, bots, logins, fullnames):
        self.changelog_names = {name.casefold(): person for name, person in changelog_names.items()}
        self.emails = dict(commit_authors)
        self.svn = {}
        for email, person in commit_authors.items():
            local, _, domain = email.partition('@')
            if SVN_DOMAIN.match(domain):
                self.svn.setdefault(local, person)
        self.aliases = {alias.casefold(): main for alias, main in aliases.items()}
        self.bots = {bot.casefold() for bot in bots}
        self.logins = {}
        for login in logins:
            self.logins.setdefault(login.casefold(), login)
        # Only full names: a first name alone is too ambiguous
        self.names = {}
        for name, person in commit_author_names.items():
            if ' ' in name.strip():
                self.names.setdefault(fold(name), person)
        self.fullnames = {fold(name): login for name, login in fullnames.items()}

    def map(self, name):
        """(person, layer); person is None for bots."""
        person, layer = self._lookup(name)
        if person is None:
            return name.strip(), UNMATCHED
        person = self.aliases.get(person.casefold(), person)
        if person.casefold() in self.bots or person.endswith('[bot]'):
            return None, BOT
        return person, layer

    def _lookup(self, name):
        raw = name.strip().lstrip('@')
        key = raw.casefold()
        if key in self.changelog_names:
            return self.changelog_names[key], 'changelog_names'
        if '@' in key:
            local, _, domain = key.partition('@')
            if key in self.emails:
                return self.emails[key], 'commit_authors'
            if SVN_DOMAIN.match(domain) and local in self.svn:
                return self.svn[local], 'commit_authors'
            return None, UNMATCHED
        if key in self.svn:
            return self.svn[key], 'commit_authors'
        if fold(raw) in self.names:
            return self.names[fold(raw)], 'commit_authors'
        if key in self.aliases:
            return self.aliases[key], 'account_aliases'
        if key in self.bots or key.endswith('[bot]'):
            return raw, 'bot_accounts'
        if key in self.logins:
            return self.logins[key], 'login'
        if fold(raw) in self.fullnames:
            return self.fullnames[fold(raw)], 'fullname'
        return None, UNMATCHED


def credited(occurrence, mapper):
    """[(person, name as written, layer)] for an entry; every named person gets full credit.

    The weak forms "(name)" and "-- name" count only when every name maps to a person.
    """
    mapped = [(name, *mapper.map(name)) for name in occurrence.names]
    if occurrence.variant in WEAK_VARIANTS and any(layer == UNMATCHED for _, _, layer in mapped):
        return []
    result = []
    seen = set()
    for name, person, layer in mapped:
        if person is None or person.casefold() in seen:
            continue
        seen.add(person.casefold())
        result.append((person, name, layer))
    return result
