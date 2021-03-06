import os
import urlparse

from lib import gdata
import lib.gdata.youtube.client
import secrets

GDATA_API_CLIENT_ID = 'CrowdTube-Connector'

class YouTubeCaptionEditor(object):

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

    def get_video(self, video_id):
        video_entry = self.youtube_client.get_video_entry(video_id=video_id)
        return YouTubeVideo(video_entry, self.youtube_client)

    def delete_track(self, video_id, track_id):
        """Deletes an existing track."""
        # TODO(mattfaus): Take google_developer_key as a constructor arg?
        response = self.youtube_client.delete_track(video_id, track_id,
            client_id=GDATA_API_CLIENT_ID,
            developer_key=secrets.google_developer_key)

        # http://docs.python.org/release/2.2.3/lib/httpresponse-objects.html
        if response.status != 200:
            print response.status, response.msg
            return False
        return True

    def add_track(self, video_id, title, language, track_content):
        """Adds a caption track.

        If a track with the same title already exists, this will silently fail.
        """
        # TODO(mattfaus): Take google_developer_key as a constructor arg?
        track_content = track_content.encode('utf-8')
        response = self.youtube_client.create_track(video_id, title, language,
            track_content, client_id=GDATA_API_CLIENT_ID,
            developer_key=secrets.google_developer_key, fmt='sub')

        # Returns a TrackEntry object
        return response

    def update_track(self, video_id, track_id, track_content):
        """Adds a caption track."""
        # TODO(mattfaus): Take google_developer_key as a constructor arg?
        track_content = track_content.encode('utf-8')
        response = self.youtube_client.update_track(video_id, track_id,
            track_content, client_id=GDATA_API_CLIENT_ID,
            developer_key=secrets.google_developer_key, fmt='sub')

        # Returns a TrackEntry object
        return response



# TODO(mattfaus): Suck these two classes into the YouTubeCaptionEditor, above
# make the YouTubeCaptionEditor behave more like a full-fledged youtube client
# Shouldn't have to pass the youtube_client object around to the sub-classes
# No need to have dictionaries where an array would do just fine (YouTubeVideo.caption_tracks)
class YouTubeVideo(object):

    def __init__(self, video_entry, youtube_client=None):
        self.youtube_client = youtube_client
        # tag:youtube.com,2008:video:SNrEiiJwD4Y
        id_parts = video_entry.GetId().split(':')
        self.video_id = id_parts[id_parts.index('video') + 1]
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

    def get_caption_tracks(self, download=False):
        # Don't check self.has_entries.  It may be False when only a
        # machine-generated caption track exists.

        if not self.youtube_client:
            raise ValueError('No youtube client available!')

        # STOPSHIP(mattfaus): get_caption_feed() only returns the first 24 caption tracks
        # so we must iterate to read more

        # TODO(mattfaus): Filter this by language with the 'lr' attribute
        all_captions = self.youtube_client.get_caption_feed(self.caption_feed)
        for caption_entry in all_captions.entry:
            new_track = YouTubeCaptionTrack(caption_entry, self.youtube_client)
            self.caption_tracks[new_track.track_source] = new_track

            if download:
                new_track.download_track()

    def get_machine_generated_track(self):
        self.get_caption_tracks()
        for src, caption_track in self.caption_tracks.iteritems():
            print src, caption_track
            if caption_track.machine_generated:
                caption_track.download_track()
                return caption_track



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
