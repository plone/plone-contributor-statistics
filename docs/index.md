---
myst:
  html_meta:
    "description": "How the Plone contributor statistics are collected, and why."
    "property=og:description": "How the Plone contributor statistics are collected, and why."
    "property=og:title": "Plone Contributor Statistics"
---

(index)=

# Plone Contributor Statistics

The Plone contributor statistics count who contributes to Plone and which organisations sponsor that work.
The Git history of Plone reaches back to 2002, and the statistics start with 2003.
This documentation explains where the data comes from, how it is counted, and why the method is the way it is.

The statistics themselves, such as rankings and trends, are not part of this documentation.
Neither is the code: it has its own comments and tests.

## Who this is for

If your organisation is ranked and you want to know how the numbers come together, start with {doc}`/explanation/index`.

If you study Plone as an example of a long-lived free software community, start with {doc}`/reference/index`.

If you look for people you once worked with, start with {doc}`/how-to/index`.

If you change the data, the method or this documentation, read {doc}`/contributing/index`.

````{grid} 1 1 2 2
:gutter: 2

```{grid-item-card} Explanation
:link: explanation/index
:link-type: doc

How the statistics come together, and why.
```

```{grid-item-card} Reference
:link: reference/index
:link-type: doc

Data sources, files, mapping files and Make targets.
```

```{grid-item-card} How-to guides
:link: how-to/index
:link-type: doc

Correct a mapping, add curated data, regenerate the statistics.
```

```{grid-item-card} Contributing
:link: contributing/index
:link-type: doc

The rules for changes to data, method and documentation.
```
````

```{toctree}
:hidden:

explanation/index
reference/index
how-to/index
contributing/index
glossary
```
