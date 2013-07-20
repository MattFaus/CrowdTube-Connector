import os
import urlparse

from lib import gdata
import lib.gdata.youtube.client
import secrets

GDATA_API_CLIENT_ID = 'CrowdTube-Connector'

class YouTubeCaptionFetcher(object):

    def __init__(self, google_email, google_password, youtube_username):
        self.youtube_username = youtube_username
        self.youtube_client = lib.gdata.youtube.client.YouTubeClient()

        # We shouldn't need this auth_token, but we'll keep it around
        self.auth_token = self.youtube_client.client_login(
            google_email, google_password, GDATA_API_CLIENT_ID)

        # A dictionary of youtube_id and YouTubeVideo objects
        self.videos = {}

    def get_videos(self):
        # Format copied from lib.gdata.youtube.client.py
        feed_uri = '%s%s/%s' % (lib.gdata.youtube.client.YOUTUBE_USER_FEED_URI,
            self.youtube_username, 'uploads')

        all_videos = self.youtube_client.get_videos(uri=feed_uri)
        for video in all_videos.entry:
            new_video = YouTubeVideo(video, self.youtube_client)
            self.videos[new_video.video_id] = new_video


class YouTubeVideo(object):

    def __init__(self, video_entry, youtube_client=None):
        self.youtube_client = youtube_client
        self.video_id = video_entry.GetId()
        self.title = video_entry.title.text

        caption_link = video_entry.get_link(
            'http://gdata.youtube.com/schemas/2007#video.captionTracks')

        self.caption_feed = caption_link.href

        # TODO(mattfaus): Make this less ugly
        has_entries = [
            a.value for a in caption_link.GetAttributes()
            if '{http://gdata.youtube.com/schemas/2007}hasEntries' == a._qname]
        has_entries = has_entries[0] == 'true'

        self.has_entries = has_entries

        self.caption_tracks = {}

    def get_caption_tracks(self, download=True):
        if not self.has_entries:
            return

        if not self.youtube_client:
            raise ValueError('No youtube client available!')

        # TODO(mattfaus): Filter this by language with the 'lr' attribute
        all_captions = self.youtube_client.get_caption_feed(self.caption_feed)
        for caption_entry in all_captions.entry:
            new_track = YouTubeCaptionTrack(caption_entry, self.youtube_client)
            self.caption_tracks[new_track.track_source] = new_track

            if download:
                new_track.download_track()


class YouTubeCaptionTrack(object):

    def __init__(self, caption_entry, youtube_client):
        self.youtube_client = youtube_client
        self.language = caption_entry.content.lang
        self.track_source = caption_entry.content.src
        self.machine_generated = YouTubeCaptionTrack._is_machine_generated(
            caption_entry)

        # Parse the video_id and caption_id out of a url like this:
        # https://gdata.youtube.com/feeds/api/videos/Jom6EtXzRMg/captiondata/Ch4LEO3ZhwUaFQjIic2vrcLuxCYSAmVuGgAiA2Fzcgw
        o = urlparse.urlparse(self.track_source)
        path_parts = o.path.split('/')
        self.video_id = path_parts[path_parts.index('videos') + 1]
        self.track_id = path_parts[path_parts.index('captiondata') + 1]

        self.track_content = None

    @staticmethod
    def _is_machine_generated(caption_entry):
        """Looks for the derived element, and returns True if it is equal to
        speechRecognition.
        """
        # TODO(mattfaus): Move this to TrackEntry within youtube/data.py?
        derived = caption_entry.GetElements(
          tag='derived', namespace='http://gdata.youtube.com/schemas/2007')

        if not derived:
            return False
        else:
            derived = derived[0]
            return derived.text == 'speechRecognition'

    def download_track(self):
        response = self.youtube_client.get_caption_track(
                track_url=self.track_source, client_id=GDATA_API_CLIENT_ID,
                developer_key=secrets.google_developer_key)

        self.track_content = response.read(2 ** 31)
        return self.track_content
