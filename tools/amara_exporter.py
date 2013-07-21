#!/usr/bin/env python
import os
import sys
import requests

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import secrets

BASE_URL = 'https://staging.universalsubtitles.org'
BASE_URL = 'https://www.universalsubtitles.org'

AMARA_AUTH_HEADERS = {
    'X-api-username': secrets.amara_api_username,
    'X-apikey': secrets.amara_api_key,
    'Accept': 'application/json',  # may be redundant with ?format=json
}



# List video languages
# GET /api2/partners/videos/[video-id]/languages/

# For each video language:
# GET /api2/partners/videos/[video-id]/languages/[lang-identifier]/subtitles/?format=srt
# GET /api2/partners/videos/asfssd/languages/en/subtitles/?format=dfxp
# GET /api2/partners/videos/asfssd/languages/111111/subtitles/?format=ssa

# https://www.youtube.com/watch?feature=player_embedded&v=r4bH66vYjss
# for youtube_id in secrets.khan_youtube_ids:

# Apparently, amara has their own IDs so, you have to issue a /videos call to get that ID
# Then, issue a /languages call to get languages
# Then, finally issue a /subtitles call to get the subtitles

# for youtube_id in ['r4bH66vYjss', '86uCiJbku4v4']:  # r4bH66vYjss == 86uCiJbku4v4, yt_id, amara_id
#     print youtube_id
#     url = BASE_URL + '/api2/partners/videos/' + youtube_id + '/languages/' # + 'en' + '/subtitles/'
#     print url

#     langs_response = requests.get(url, headers=AMARA_AUTH_HEADERS, verify=False)
#     print langs_response, langs_response.text, langs_response.headers, langs_response.status_code


import urllib

url = BASE_URL + '/api2/partners/videos/?video_url=' + urllib.quote('https://www.youtube.com/watch?v=r4bH66vYjss')
# url = BASE_URL + '/api2/partners/videos/?video_url=https://www.youtube.com/watch?v=r4bH66vYjss'
langs_response = requests.get(url, headers=AMARA_AUTH_HEADERS, verify=False)
print langs_response.json()
