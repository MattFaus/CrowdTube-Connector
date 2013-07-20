#!/usr/bin/python
from lib import gdata
import lib.gdata.youtube.client as youtube_client


client = youtube_client.YouTubeClient()
feed = client.GetUserFeed(username='mattfauska')
print feed



