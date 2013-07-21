#!/usr/bin/env python
import cStringIO
import os
import zipfile

import crowdin
import format
import secrets
import youtube

# http://www.science.co.il/Language/Locale-Codes.asp
DISPLAY_NAMES = {
    'af': 'Afrikaans',
    'ar': 'Arabic',
    'ca': 'Catalan',
    'cs': 'Czech',
    'da': 'Danish',
    'de': 'German',
    'el': 'Greek',
    'en': 'English',
    'es-ES': 'Spanish',
    'fi': 'Finnish',
    'fr': 'French',
    'he': 'Hebrew',
    'hu': 'Hungarian',
    'it': 'Italian',
    'ja': 'Japanese',
    'ko': 'Korean',
    'nl': 'Dutch',
    'no': 'Norwegian',
    'pl': 'Polish',
    'pt-BR': 'Portuguese - Brazil',
    'pt-PT': 'Portuguese - Portugal',
    'ro': 'Romanian',
    'ru': 'Russian',
    'sr': 'Serbian',
    'sv-SE': 'Swedish',
    'tr': 'Turkish',
    'uk': 'Ukrainian',
    'vi': 'Vietnamese',
    'zh-CN': 'Chinese - China',
    'zh-TW': 'Chinese - Taiwan',
}

def get_display_name_for_locale_code(locale_code):
    # TODO(mattfaus): Do something more elegant here
    return DISPLAY_NAMES.get(locale_code) or locale_code


def perform_full_sync(export=False):

    # Initialize client libraries
    yt_client = youtube.YouTubeCaptionEditor(secrets.google_email,
        secrets.google_password, secrets.youtube_username)

    ci_client = crowdin.CrowdInClient(secrets.crowdin_ident, secrets.crowdin_key)

    # Build and download the CrowdIn captions

    if export:
        ci_client.build_export_zip()

    zipped_translations = crowdin.CrowdInZipFile(ci_client.download_translations())
    print 'Found %i translation files' % zipped_translations.get_file_count()

    # Pull the YouTube videos
    yt_client.get_videos()
    print 'Found %i videos on YouTube' % len(yt_client.videos)

    for video_id, video in yt_client.videos.iteritems():
        print 'Processing', video_id

        po_path = crowdin.CrowdInZipFile.get_po_path(video.title, video_id)

        existing_translations = zipped_translations.get_all_translations(po_path)

        if existing_translations:
            print '-- Captions found, updating YouTube with %i translations' % len(existing_translations)

            video.get_caption_tracks()
            for src, caption_track in video.caption_tracks.iteritems():
                # Update existing tracks
                new_po_content = existing_translations.get(caption_track.language)
                if not new_po_content:
                    # How did this track get on YouTube, wasn't this tool!
                    print '-- Corresponding track not found for', caption_track.language
                    continue

                po_reader = format.PotTranscriptReader(new_po_content)
                sub_writer = format.SubTranscriptWriter(po_reader)

                print '-- Uploading an updated track for', caption_track.language
                yt_client.update_track(video_id, caption_track.track_id, sub_writer.content)

                # Remove it from the list, so we know this does not need to
                # be added
                del existing_translations[caption_track.language]

            # These are newly approved translations that need to be added
            for lang, po_content in existing_translations.iteritems():
                po_reader = format.PotTranscriptReader(po_content)
                sub_writer = format.SubTranscriptWriter(po_reader)

                display_name = get_display_name_for_locale_code(lang)

                print '-- Uploading a new track for', display_name
                yt_client.add_track(video_id, display_name, lang, sub_writer.content)
        else:
            print '-- No captions found in CrowdIn, attempting to upload'

            # Get the machine-generated caption-track from YT
            machine_track = video.get_machine_generated_track()

            # Can't do anything of there isn't a machine-generated track
            if not machine_track:
                print '-- Did not have a machine-generated track.'
                continue

            # Convert to .po format
            sub_reader = format.SubTranscriptReader(machine_track.track_content)
            pot_writer = format.PotTranscriptWriter(sub_reader)

            # Upload to CrowdIn
            # TODO(mattfaus): sync_files() can batch things, maybe that's faster?
            print '-- Uploading machine-generated captions to CrowdIn:', po_path
            ci_client.sync_files({
                po_path: pot_writer.get_file()
            })


if __name__ == "__main__":
    # TODO(mattfaus): Add a bunch of options to download single videos, only
    # machine-generated tracks, to a specific destination directory,
    # transform into different file formats, etc.

    perform_full_sync()

    # Do this to build a new export, but it only works every 30 mins
    # perform_full_sync(export=True)
