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
    return text.normalize('NFKD').replace(/\p{M}/gu, '').replace(/[^\p{L}\p{N}\s]/gu, '')
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

  // The years of the page, oldest first, as the year menu lists them
  var years = Array.prototype.map.call(form.year.options, function (option) { return option.value; }).sort();
  var docs = result.getAttribute('data-docs') || '';
  var wall = data.organisations || {};

  function entry(id, year) {
    return (people[year] || []).filter(function (p) { return p.id === id; })[0];
  }

  // The nearest year before (step -1) or after (step 1) the year in which the person was active
  function activeYear(id, year, step) {
    for (var index = years.indexOf(year) + step; index >= 0 && index < years.length; index += step) {
      if (entry(id, years[index])) { return years[index]; }
    }
    return null;
  }

  // A button that turns the card to the nearest active year in its direction, disabled when there is none
  function pager(id, year, step) {
    var target = activeYear(id, year, step);
    var button = document.createElement('button');
    button.type = 'button';
    button.className = 'pager';
    button.setAttribute('data-step', step);
    button.textContent = step < 0 ? '\u2039' + (target ? ' ' + target : '') : (target ? target + ' ' : '') + '\u203a';
    button.setAttribute('aria-label', !target ? (step < 0 ? 'No earlier year' : 'No later year')
      : (step < 0 ? 'Earlier: ' : 'Later: ') + target);
    button.disabled = !target;
    button.addEventListener('click', function () {
      form.year.value = target;
      render();
      // Keep the keyboard on the same button of the new card
      var same = result.querySelector('.pager[data-step="' + step + '"]');
      (same && !same.disabled ? same : result.querySelector('.card')).focus();
    });
    return button;
  }

  // The organisation of the year: linked to its entry when it has a level; without one, how to add it
  function organisation(match) {
    var dd = document.createElement('dd');
    var name = match.organisation;
    if (!name || name === 'Unmapped') {
      var how = document.createElement('a');
      how.className = 'how';
      how.href = docs + 'how-to/add-an-affiliation.html';
      how.textContent = 'how to add one';
      dd.textContent = 'none recorded ';
      dd.appendChild(how);
    } else if (wall[name]) {
      var link = document.createElement('a');
      link.href = '#org-' + wall[name];
      link.textContent = name;
      dd.appendChild(link);
    } else {
      dd.textContent = name;
    }
    return dd;
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
    var match = entry(id, year);
    // Someone the data knows from another year gets a card for this year too, with the buttons to their years
    var known = match || years.map(function (y) { return entry(id, y); }).filter(Boolean)[0];
    var card = document.createElement('div');
    card.className = 'card';
    card.tabIndex = -1;
    result.appendChild(card);
    if (!known) {
      card.innerHTML = '<p>Nobody with that GitHub login or name was active in ' + year + '. ' +
        'People without a GitHub login are found by their full name.</p>';
      return;
    }
    var head = document.createElement('div');
    head.className = 'head';
    var title = document.createElement('h3');
    title.textContent = (known.name || known.id) + ' in ' + year;
    head.appendChild(pager(id, year, -1));
    head.appendChild(title);
    head.appendChild(pager(id, year, 1));
    card.appendChild(head);
    if (!match) {
      var none = document.createElement('p');
      none.textContent = 'Not active in ' + year + ': no commits, no merged pull requests, no community roles.';
      card.appendChild(none);
      return;
    }
    var facts = document.createElement('dl');
    [['Organisation', organisation(match)],
     ['Merged pull requests', rank(list, match, 'pull_requests')],
     ['Commits', rank(list, match, 'commits')],
     ['Community roles', match.roles.length ? match.roles.join(', ') : 'none']].forEach(function (row) {
      var dt = document.createElement('dt');
      dt.textContent = row[0];
      facts.appendChild(dt);
      if (typeof row[1] === 'string') {
        var dd = document.createElement('dd');
        dd.textContent = row[1];
        facts.appendChild(dd);
      } else {
        facts.appendChild(row[1]);
      }
    });
    // The talks of the year: the title, linked to the recording where there is one; the event only when there are several
    var talks = match.talks || [];
    if (talks.length) {
      var events = {};
      talks.forEach(function (talk) { events[talk.event] = true; });
      var several = Object.keys(events).length > 1;
      var talksTitle = document.createElement('dt');
      talksTitle.textContent = 'Talks';
      facts.appendChild(talksTitle);
      var talksList = document.createElement('dd');
      talks.forEach(function (talk, index) {
        if (index) { talksList.appendChild(document.createTextNode(' · ')); }
        if (talk.video) {
          var video = document.createElement('a');
          video.href = talk.video;
          video.textContent = talk.title;
          talksList.appendChild(video);
        } else {
          talksList.appendChild(document.createTextNode(talk.title));
        }
        if (several) { talksList.appendChild(document.createTextNode(' (' + talk.event + ')')); }
      });
      facts.appendChild(talksList);
    }
    var note = document.createElement('p');
    note.className = 'note';
    note.textContent = 'Out of ' + list.length + ' people active in ' + year + '. ' +
      'Community roles recorded under a full name that the data doesn\u2019t link to a login show up when you search that name (#117).';
    card.appendChild(facts);
    card.appendChild(note);
  }

  form.addEventListener('input', render);
  form.addEventListener('submit', function (event) { event.preventDefault(); render(); });
})();
