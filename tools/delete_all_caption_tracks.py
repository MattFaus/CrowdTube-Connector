#!/usr/bin/env python
"""
Deletes all non-machine-generated caption tracks from a youtube video.
"""
import optparse
import os
import sys
import traceback

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import youtube
import secrets



def main():
    parser = optparse.OptionParser()
    options, args = parser.parse_args()

    yt_client = youtube.YouTubeCaptionEditor(secrets.google_email,
        secrets.google_password, secrets.youtube_username)

    for video_id in args:
        print 'Processing', video_id

        try:
            video = yt_client.get_video(video_id)

            video.get_caption_tracks()
            tracks = video.caption_tracks.values()
            for track in [t for t in tracks if not t.machine_generated]:
                print '-- Deleting track', track.language
                yt_client.delete_track(video.video_id, track.track_id)

        except Exception, e:
            traceback.print_exc()

if __name__ == '__main__':
    main()
