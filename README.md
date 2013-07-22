CrowdTube-Connector
===================

A utility that syncs subtitles (a.k.a. captions) between YouTube and CrowdIn.

Also, the CrowdInClient found in crowdin.py should be useful for other python
projects who wish to integrate with CrowdIn's API.

![Syncing Videos](https://s3.amazonaws.com/uploads.hipchat.com/6574/209451/4n1p29y6m870tni/crowdTube-1.png)
![Syncing Captions](https://s3.amazonaws.com/uploads.hipchat.com/6574/209451/dxs9uuux0kaib0m/crowdTube-2.png)

SHIPSTOPPERS:
- "Download Approved Only" functionality not working, it downloads everything
-- Tried setting "Do not export untranslated" on http://crowdin.net/project/ka-subtitles-test/settings

TODO:
- Unit tests
- Logging functionality with verbosity switches
- Figure out sort-ordering in CrowdIn. When uploaded they are correct, but after a few translations are completed they become sorted by translation status with untranslated above translated.  Since these are time-stamped, keeping the order is a big deal.
- Figure out incremental syncing, so we don't have to download/upload everything from YouTube/CrowdIn every time
- Do a lot of clean-up in youtube.py.  get*() should just return what it gets, and should consolidate the classes into YouTubeCaptionEditor
- Add a requirements.txt, probably with:
    requests

