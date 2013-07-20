CrowdTube-Connector
===================

A utility that syncs subtitles (a.k.a. captions) between YouTube and CrowdIn.

Also, the CrowdInClient found in crowdin.py should be useful for other python
projects who wish to integrate with CrowdIn's API.

TODO:
- Unit tests
- Logging functionality with verbosity switches
- Figure out sort-ordering in CrowdIn. When uploaded they are correct, but after a few translations are completed they become sorted by translation status with untranslated above translated.  Since these are time-stamped, keeping the order is a big deal.
- Add a requirements.txt, probably with:
    requests
