"""Sphinx configuration for the Plone Contributor Statistics documentation."""

project = "Plone Contributor Statistics"
author = "Plone Foundation and contributors"
copyright = "Plone Foundation"

extensions = [
    "myst_parser",
    "sphinx_copybutton",
    "sphinx_design",
    "sphinxcontrib.mermaid",
]

myst_enable_extensions = [
    "attrs_block",
    "attrs_inline",
    "colon_fence",
    "deflist",
    "linkify",
    "strikethrough",
    "substitution",
]
myst_heading_anchors = 3
# Only links with a scheme: package names like plone.app.contenttypes are no domains
myst_linkify_fuzzy_links = False

exclude_patterns = ["_build"]

html_theme = "plone_sphinx_theme"
html_baseurl = "https://plone.github.io/plone-contributor-statistics/"
html_title = project

html_theme_options = {
    "logo": {"text": project},
    "navigation_with_keys": True,
    "path_to_docs": "docs",
    "repository_branch": "main",
    "repository_url": "https://github.com/plone/plone-contributor-statistics",
    "search_bar_text": "Search",
    "show_toc_level": 2,
    "use_edit_page_button": True,
    "use_issues_button": True,
    "use_repository_button": True,
}
