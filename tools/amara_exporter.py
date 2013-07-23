#!/usr/bin/env python
"""
A script to export subtitle information out of Amara onto the local drive.
Launches a thread for each download, so it should be relatively fast.
Then, we can convert this data into CrowdIn format and upload it there.

Also includes a resume mode to pick up where we left off.

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
import time

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import secrets

# BASE_AMARA_URL = 'https://staging.universalsubtitles.org'
BASE_AMARA_URL = 'https://www.universalsubtitles.org'
# BASE_AMARA_URL = 'https://www.amara.org'

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
        self.response = None
        self.exception = None

    def start_synchronous(self):
        self.start()
        self.join()

    def run(self):
        try:
            self.response = self._download(self.url)

            if self.response.status_code != 200:
                # The caller should check self.response for any errors and context
                print 'Non-200 response received', self.response.status_code, self.response.text
                return

            print 'Starting write to', self.dest_file_path
            if self.dest_file_path:
                self._stream_to_file()
        except Exception, ce:
            # TODO(mattfaus): Find the real ConnectionError class and only catch that
            # ConnectionError: HTTPSConnectionPool(host='www.amara.org', port=443):
            # Max retries exceeded with url: /api2/partners/videos/3KKcDNFFF75y/languages/en/subtitles/
            # (Caused by <class 'socket.gaierror'>: [Errno 8] nodename nor servname provided, or not known)
            print 'ConnectionError received', ce
            self.exception = ce

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

        # if self.dest_file_path:
        #     # If writing to a file, we stream it
        #     kwargs['stream'] = True

        if self.get_kwargs:
            kwargs.update(self.get_kwargs)

        print 'Calling GET on', url
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
    try:
        url = BASE_AMARA_URL + '/api2/partners/videos/?video_url=' + BASE_YOUTUBE_URL + youtube_id
        response = requests.get(url, headers=AMARA_AUTH_HEADERS, verify=False)

        if response.status_code != 200:
            print 'Non-200 received', response.status_code, response.text
            return {}

        return response.json()
    except Exception, ce:
        # ConnectionError: HTTPSConnectionPool(host='www.amara.org', port=443):
        # Max retries exceeded with url: /api2/partners/videos/3KKcDNFFF75y/languages/en/subtitles/
        # (Caused by <class 'socket.gaierror'>: [Errno 8] nodename nor servname provided, or not known)
        print 'ConnectionError received', ce
        return {}


def has_subtitle_entries(resource_uri):
    """
    {
        "created": "2013-05-30T07:24:23",
        "description": "How changes in Earth's rotation can effect Earth's seasons and climate",
        "id": "184371",
        "is_original": false,
        "is_rtl": false,
        "is_translation": false,
        "language_code": "sr",
        "metadata": {},
        "name": "Serbian",
        "num_versions": 0,
        "official_signoff_count": 0,
        "original_language_code": null,
        "resource_uri": "/api2/partners/videos/dtBccSDcJ4b5/languages/sr/",
        "site_url": "http://www.amara.org/videos/dtBccSDcJ4b5/sr/184371/",
        "subtitle_count": 0,
        "title": "Milankovitch Cycles   Precession and Obliquity",
        "versions": []
    }
    """
    return True
    try:
        url = BASE_AMARA_URL + resource_uri
        response = requests.get(url, headers=AMARA_AUTH_HEADERS, verify=False)

        if response.status_code != 200:
            print 'Non-200 received', response.status_code, response.text
            return False

        data = response.json()
        return data.get('subtitle_count', 0) > 0

    except Exception, ce:
        # ConnectionError: HTTPSConnectionPool(host='www.amara.org', port=443):
        # Max retries exceeded with url: /api2/partners/videos/3KKcDNFFF75y/languages/en/subtitles/
        # (Caused by <class 'socket.gaierror'>: [Errno 8] nodename nor servname provided, or not known)
        print 'ConnectionError received', ce
        return {}



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

def already_downloaded(file_name, check_contents=True):
    """
    Arguments:
        file_name
        check_contents - When False, only check to see if the file exists
    """
    if os.path.isfile(file_name):
        if not check_contents:
            return True
        else:
            with open(file_name, 'r') as prev_download:
                try:
                    json.loads(prev_download.read())
                    return True
                except:
                    return False
    return False

def export(all_youtube_ids, dest_dir, sleep_secs, force_download):
    """
    Arguments:
        all_youtube_ids - a list of all youtube_ids to export
        dest_dir - where you want to write the subtitle data files
    """
    downloader_threads = []

    # Shuffle them so we can try to make some progress when restarting
    import random
    all_youtube_ids = list(all_youtube_ids)
    random.shuffle(all_youtube_ids)

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
            print '-- -- Iterating over %i languages %s' % (
                len(amara_languages), amara_object.get('resource_uri'))

            for amara_language in amara_languages:
                resource_uri = amara_language.get('resource_uri')

                if not has_subtitle_entries(resource_uri):
                    print 'Does not have subtitles, skipping download.'
                    continue


                subtitles_uri = amara_language.get('subtitles_uri')
                locale_code = amara_language.get('code', 'UNKNOWN')
                # TODO(mattfaus): Do we also want the data behind resource_uri?

                if not subtitles_uri:
                    print '-- -- -- ERROR, languages object missing subtitles_uri:', amara_language.get('code'), amara_language.get('name')
                    continue

                file_name = '%s~%s~%s.json' % (youtube_id, amara_id, locale_code)
                file_name = os.path.join(dest_dir, file_name)

                if not force_download and already_downloaded(file_name, check_contents=True):
                    print '-- -- -- Skipping download for %s: %s' % (locale_code, file_name)
                else:
                    print '-- -- -- Fetching subtitles for %s: %s' % (locale_code, file_name)

                    new_thread = download_subtitle_data(subtitles_uri, file_name)
                    downloader_threads.append(new_thread)

        if sleep_secs:  # sleep == 0 causes infinite sleep
            print 'Sleeping for %i seconds' % sleep_secs
            time.sleep(sleep_secs)

    print 'Waiting for all threads to join'
    for downloader_thread in downloader_threads:
        downloader_thread.join()

        if downloader_thread.response:
            if downloader_thread.response.status_code != 200:
                print '%s returned status %i - %s' % (
                    downloader_thread.url, downloader_thread.response.status_code,
                    downloader_thread.response.text)
        elif downloader_thread.exception:
            print '%s threw exception - %s' % (
                downloader_thread.url, downloader_thread.exception)


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

    # Note: I used a value of 5 to download ~5000 videos x ~10 languages
    # TODO(mattfaus): I'm not sure this actually helped, or if some videos
    # just had bad DNS or something
    # TODO(mattfaus): Auto-scale this value based on the number of languages
    # within each video, i.e. sleep for sleep * len(amara_languages)
    parser.add_option('-s', '--sleep',
        action="store", dest="sleep", type="int",
        help=("Number of seconds to sleep between videos. May alleviate Amara "
            "connection throttling errors."),
        default=0)

    parser.add_option('-x', '--force-download',
        action="store_true", dest="force_download",
        help=("Force re-downloading files that already exist in dest-dir."),
        default=False)

    # If you have failures during your download, you can do this to
    # pick up where you left off. (But add the last few videos back in to make
    # sure they are fully downloaded
    # http://www.catonmat.net/blog/set-operations-in-unix-shell/
    # Set of exported youtube_ids (you'll need to modify the second cut's -f for your directory)
    # l\s ~/misc/amara_subtitle_export/*.json | cut -d'~' -f 1 | cut -d'/' -f 6 | uniq > ~/misc/exported_youtube_ids.txt
    # comm -23 <(sort ~/misc/all_khan_academy_youtube_ids.txt) <(sort ~/misc/exported_youtube_ids.txt) | sort > ~/misc/not_exported_youtube_ids.txt

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
    export(all_youtube_ids, options.dest_dir, options.sleep, options.force_download)


if __name__ == '__main__':
    main()
