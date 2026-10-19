// Plone community page: tabs and the people search. Without JavaScript, all
// sections show one after another and the page stays readable.
(function () {
  'use strict';
  document.documentElement.classList.add('js');

  // Tabs over the sections below the first screen
  var tabs = document.querySelector('nav.tabs');
  var panels = ['organisations', 'people', 'history'];

  function show(name) {
    panels.forEach(function (panel) {
      document.getElementById(panel).hidden = panel !== name;
      var tab = tabs.querySelector('[data-tab="' + panel + '"]');
      tab.setAttribute('aria-selected', String(panel === name));
    });
  }

  function route() {
    var id;
    try { id = decodeURIComponent(location.hash.slice(1)); } catch (error) { id = ''; }
    var target = id && document.getElementById(id);
    var panel = target && (panels.indexOf(id) >= 0 ? id : (target.closest('.panel') || {}).id);
    show(panel || 'organisations');
    if (!target) { return; }
    if (target.tagName === 'DETAILS') {
      target.open = true;
      target.scrollIntoView();
    } else if (panel) {
      tabs.scrollIntoView();
    }
  }

  if (tabs) {
    tabs.hidden = false;
    window.addEventListener('hashchange', route);
    route();
  }

  // People search: the data is embedded in the page, ranks are worked out here
  var dataElement = document.getElementById('people-data');
  var form = document.getElementById('people-search');
  var result = document.getElementById('people-result');
  if (!dataElement || !form) { return; }
  var data = JSON.parse(dataElement.textContent);
  var people = data.years;
  var names = data.names;

  // The same key as names.fold in Python: no accents or punctuation, lower case, single spaces
  function normalise(text) {
    return text.normalize('NFKD').replace(/[̀-ͯ]/g, '').replace(/[^\p{L}\p{N}\s]/gu, '')
      .toLowerCase().split(/\s+/).filter(Boolean).join(' ');
  }

  function rank(list, person, field) {
    var active = list.filter(function (p) { return p[field] > 0; });
    if (!person[field]) { return 'none'; }
    var higher = active.filter(function (p) { return p[field] > person[field]; }).length;
    return (higher + 1) + ' of ' + active.length + ' (' + person[field].toLocaleString('en') + ')';
  }

  // The anonymous distribution of the selected year: no names, only counts
  var buckets = [[1, 1], [2, 9], [10, 49], [50, Infinity]];
  function distribute(list) {
    var table = document.getElementById('people-distribution');
    if (!table) { return; }
    table.querySelector('.dy').textContent = form.year.value;
    table.querySelectorAll('tbody tr').forEach(function (row) {
      var field = row.getAttribute('data-field');
      row.querySelectorAll('td').forEach(function (cell, index) {
        cell.textContent = list.filter(function (p) {
          return p[field] >= buckets[index][0] && p[field] <= buckets[index][1];
        }).length;
      });
    });
  }

  function render() {
    var query = normalise(form.person.value);
    var year = form.year.value;
    var list = people[year] || [];
    result.textContent = '';
    distribute(list);
    if (!query) { return; }
    // A name of a registered person finds the person's id, anything else is taken as a login
    var id = names[query] || form.person.value.trim().toLowerCase();
    var match = list.filter(function (p) {
      return p.id === id;
    })[0];
    var card = document.createElement('div');
    card.className = 'card';
    if (!match) {
      card.innerHTML = '<p>Nobody with that GitHub login or name was active in ' + year + '. ' +
        'People without a GitHub login are found by their full name.</p>';
      result.appendChild(card);
      return;
    }
    var title = document.createElement('h3');
    title.textContent = (match.name || match.id) + ' in ' + year;
    var facts = document.createElement('dl');
    [['Merged pull requests', rank(list, match, 'pull_requests')],
     ['Commits', rank(list, match, 'commits')],
     ['Community roles', match.roles.length ? match.roles.join(', ') : 'none']].forEach(function (row) {
      var dt = document.createElement('dt');
      var dd = document.createElement('dd');
      dt.textContent = row[0];
      dd.textContent = row[1];
      facts.appendChild(dt);
      facts.appendChild(dd);
    });
    var note = document.createElement('p');
    note.className = 'note';
    note.textContent = 'Out of ' + list.length + ' people active in ' + year + '. ' +
      'Community roles recorded under a full name that the data doesn\u2019t link to a login show up when you search that name (#117).';
    card.appendChild(title);
    card.appendChild(facts);
    card.appendChild(note);
    result.appendChild(card);
  }

  form.addEventListener('input', render);
  form.addEventListener('submit', function (event) { event.preventDefault(); render(); });
})();
