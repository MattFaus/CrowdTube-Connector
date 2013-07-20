#!/usr/bin/python
import os

import crowdin
import format
import secrets
import youtube


def main():
    # TODO(mattfaus): Add a bunch of options to download single videos, only
    # machine-generated tracks, to a specific destination directory,
    # transform into different file formats, etc.

    fetcher = youtube.YouTubeCaptionFetcher(secrets.google_email,
        secrets.google_password, secrets.youtube_username)

    fetcher.get_videos()
    print 'Found %i videos' % len(fetcher.videos)
    videos_with_tracks = [v for k,v in fetcher.videos.iteritems() if v.has_entries]

    # Unlisted / Private videos don't return captions, even tho they have them
    print 'Found %i videos with caption tracks' % len(videos_with_tracks)

    for v in videos_with_tracks:
        v.get_caption_tracks()

        print '%s has the following caption tracks' % v.title

        for src, caption_track in v.caption_tracks.iteritems():
            if not caption_track.track_content:
                continue  # It's not downloaded yet

            num_lines = len(caption_track.track_content.split('\n'))

            file_name = '%s_%i_%s_%s.srt' % (
                caption_track.language, num_lines,
                caption_track.machine_generated, caption_track.track_id)

            root_dir = '/tmp/downloaded_subtitles'
            file_name = os.path.join(root_dir, file_name)
            print '\t%s: %i lines, Machine generated = %s, written to %s' % (
                caption_track.language, num_lines,
                caption_track.machine_generated, file_name)

            if caption_track.machine_generated:
                reader = format.SubTranscriptReader(caption_track.track_content)

                writer = format.PotTranscriptWriter(reader)
                # print writer.pot_content

                files_to_add = {
                    'test1/test.pot': writer.get_file(),
                    'test1/test2.pot': writer.get_file(),
                }

                print 'Syncing to CrowdIn'
                ci_client = crowdin.CrowdInClient(secrets.crowdin_ident, secrets.crowdin_key)
                ci_client.sync_files(files_to_add)


if __name__ == "__main__":
    main()
