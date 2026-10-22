Author: Andreas Zeidler <az@zitc.de>
Date: 2018-11-12T15:06:30+01:00

Pass the source object's UUID when adding a new translation.

As of #17 the `add_at_translation` view expects the UUID so it can
include the translation group and source language when building the
URL to redirect to `at_babel_edit`.  Passing only the portal type
is no longer enough.

Note that this requires at least version 2.0.1 of
`archetypes.multilingual`.

It also essentially reverts 5c9a0898 again.
