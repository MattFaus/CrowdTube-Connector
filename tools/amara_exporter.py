#!/usr/bin/env python
"""
A script to export subtitle information out of Amara onto the local drive.
Launches a thread for each download, so it should be relatively fast.
Then, we can convert this data into CrowdIn format and upload it there.

TODO(mattfaus): Add support for other providers (besides YouTube).  All that's
needed is adding the video_url format, and stitching that together with a
new list of IDs for each provider.

For more details on the API:
http://amara.readthedocs.org/en/latest/api.html#api-documentation
"""
import json
import optparse
import os
import sys
import requests
import threading

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import secrets

# BASE_AMARA_URL = 'https://staging.universalsubtitles.org'
BASE_AMARA_URL = 'https://www.universalsubtitles.org'

# Note: https doesn't work, no idea why not
BASE_YOUTUBE_URL = 'http://www.youtube.com/watch?v='

AMARA_AUTH_HEADERS = {
    'X-api-username': secrets.amara_api_username,
    'X-apikey': secrets.amara_api_key,
    'Accept': 'application/json',  # may be redundant with ?format=json
}

class Downloader(threading.Thread):
    """A background downloader thread.  After instantiation, you can call
    start() to launch the thread, and then join() to wait for it to finish. Or,
    you can simply call start_synchronous(), which will do both of these.
    """

    def __init__(self, url, dest_file_path=None, headers=None, get_kwargs=None):
        """Constructor.

        Arguments:
            url - The full URL to the object you want to download
            dest_file_path - If provided, the Downloader will stream the
                response directly into the file, allowing for a constant
                memory download of very large files.
        """
        threading.Thread.__init__(self)
        self.url = url
        self.dest_file_path = dest_file_path
        self.custom_headers = headers
        self.get_kwargs = get_kwargs

    def start_synchronous(self):
        self.start()
        self.join()

    def run(self):
        self.response = self._download(self.url)

        if self.response.status_code != 200:
            # The caller should check self.response for any errors and context
            return

        if self.dest_file_path:
            self._stream_to_file()

    def _stream_to_file(self, chunk_size=100 * 1024):
        if not self.dest_file_path:
            raise ValueError("I don't know where to write the content.")

        with open(self.dest_file_path, 'w') as dest_file:
            for chunk in self.response.iter_content(chunk_size):
                dest_file.write(chunk)

    def _download(self, url):
        kwargs = {}

        if self.custom_headers:
            kwargs['headers'] = self.custom_headers

        if self.dest_file_path:
            # If writing to a file, we stream it
            kwargs['stream'] = True

        if self.get_kwargs:
            kwargs.update(self.get_kwargs)

        return requests.get(url, **kwargs)


def get_amara_video_info(youtube_id):
    """Gets Amara meta-data about a specific youtube video.

    Returns an object that looks like this:
    {
      "meta": {
        "previous": null,
        "total_count": 1,
        "offset": 0,
        "limit": 20,
        "next": null
      },
      "objects": [
        {
          "description": "Visually understanding basic vector operations",
          "all_urls": [
            "http://www.youtube.com/watch?v=r4bH66vYjss"
          ],
          "created": "2011-04-17T19:32:19",
          "title": "Linear Algebra: Vector Examples",
          "thumbnail": "http://i.ytimg.com/vi/r4bH66vYjss/3.jpg",
          "languages": [
            {
              "subtitles_uri": "/api2/partners/videos/86uCiJbku4v4/languages/ar/subtitles/",
              "code": "ar",
              "name": "Arabic",
              "resource_uri": "/api2/partners/videos/86uCiJbku4v4/languages/ar/"
            },
            {
              "subtitles_uri": "/api2/partners/videos/86uCiJbku4v4/languages/zh-tw/subtitles/",
              "code": "zh-tw",
              "name": "Chinese, Traditional",
              "resource_uri": "/api2/partners/videos/86uCiJbku4v4/languages/zh-tw/"
            }
          ],
          "resource_uri": "/api2/partners/videos/86uCiJbku4v4/",
          "team": null,
          "duration": 1533,
          "original_language": "en",
          "id": "86uCiJbku4v4",
          "metadata": {}
        }
      ]
    }
    """
    url = BASE_AMARA_URL + '/api2/partners/videos/?video_url=' + BASE_YOUTUBE_URL + youtube_id
    response = requests.get(url, headers=AMARA_AUTH_HEADERS, verify=False)

    if response.status_code != 200:
        print 'Non-200 received', response.status_code, response.text
        return {}

    return response.json()


def download_subtitle_data(subtitles_uri, dest_file):
    """Starts a background thread to download subtitile data into a file.

    Returns the thread, which you can call .join() on to wait for it to finish
    writing.
    """
    url = BASE_AMARA_URL + subtitles_uri

    downloader = Downloader(url, dest_file, headers=AMARA_AUTH_HEADERS,
        get_kwargs={'verify':False})
    downloader.start()

    return downloader


def export(all_youtube_ids, dest_dir):
    """
    Arguments:
        all_youtube_ids - a list of all youtube_ids to export
        dest_dir - where you want to write the subtitle data files
    """
    downloader_threads = []

    for youtube_id in all_youtube_ids:
        print 'Processing youtube_id', youtube_id

        # First, we have to look-up the amara_id, given the youtube_id
        amara_video = get_amara_video_info(youtube_id)
        amara_objects = amara_video.get('objects', [])
        print '-- Got amara video metadata with num objects =', len(amara_objects)

        # I don't think this will ever return >1 result, but we'll loop just in case
        for amara_object in amara_objects:
            amara_id = amara_object.get('id', 'UNKNOWN')
            amara_languages = amara_object.get('languages', [])
            print '-- -- Iterating over %i languages', amara_object.get('resource_uri')

            for amara_language in amara_languages:
                subtitles_uri = amara_language.get('subtitles_uri')
                locale_code = amara_language.get('code', 'UNKNOWN')
                # TODO(mattfaus): Do we also want the data behind resource_uri?

                if not subtitles_uri:
                    print '-- -- -- ERROR, languages object missing subtitles_uri:', amara_language.get('code'), amara_language.get('name')
                    continue

                file_name = '%s~%s~%s.json' % (youtube_id, amara_id, locale_code)
                file_name = os.path.join(dest_dir, file_name)
                print '-- -- -- Fetching subtitles for %s: %s' % (locale_code, file_name)

                new_thread = download_subtitle_data(subtitles_uri, file_name)
                downloader_threads.append(new_thread)

    print 'Waiting for all threads to join'
    for downloader_thread in downloader_threads:
        downloader_thread.join()

        if downloader_thread.response.status_code != 200:
            print '%s returned status %i - %s' % (
                downloader_thread.url, downloader_thread.response.status_code,
                downloader_thread.response.text)


def main():
    parser = optparse.OptionParser()

    parser.add_option('-i', '--youtube-ids',
        action="store", dest="youtube_ids",
        help="A comma-delimited list of youtube IDs",
        default="")

    parser.add_option('-f', '--youtube-ids-file',
        action="store", dest="youtube_ids_file",
        help="A path to a file which contains youtube_ids, one per line",
        default="")

    parser.add_option('-d', '--dest-dir',
        action="store", dest="dest_dir",
        help="REQUIRED: A path to a directory where the resulting files will be written",
        default="")

    options, args = parser.parse_args()

    if not options.youtube_ids and not options.youtube_ids_file:
        parser.error('One of -i (--youtube-ids) or -f (--youtube-ids-file) '
            'must be provided.')

    if not options.dest_dir:
        # The optparse author does *not* like required options, sheesh
        parser.error('-d (--dest-dir) must be provied.')

    # For convenience, create the directory if needed
    if not os.path.exists(options.dest_dir):
        print 'Creating destination directory'
        os.makedirs(options.dest_dir)

    all_youtube_ids = []
    if options.youtube_ids:
        all_youtube_ids += options.youtube_ids.split(',')

    if options.youtube_ids_file:
        with open(options.youtube_ids_file, 'r') as id_file:
            for line in id_file.readlines():
                all_youtube_ids.append(line.strip())

    orig_len = len(all_youtube_ids)
    all_youtube_ids = set(all_youtube_ids)
    new_len = len(all_youtube_ids)

    if new_len != orig_len:
        print 'YouTube IDs list was %i now its %i after removing %i dupes' % (
            orig_len, new_len, (orig_len - new_len))

    print 'Exporting %i youtube ids' % new_len
    export(all_youtube_ids, options.dest_dir)


if __name__ == '__main__':
    main()
