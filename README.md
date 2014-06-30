## PyTunesFixer

This is one of my oldest programming projects. Its a Windows-only utility that
edits the metadata of songs straight out of iTunes, grabbing information from
[Discogs](www.discogs.com). Format of the metadata is highly opinionated,
hardcoded, and is defined by the constraints of iTunes' metadata capabilities.

### Just some of the hardcoded metadata requirements

* Composers' names are included by digging into the Written By credits on the release in question.
If none exist, the release artist's name is used as a composer.
* Groups (bands) are decomposed into the individual members.
* Attempts to find an artist's real name (rather than an alias/stage name) are made.
* Lists of composers are sorted by last name, slash delimited.
* Featuring credits are denoted with "feat." in the *artist* field.
