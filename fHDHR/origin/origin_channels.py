import urllib.parse
import m3u8
import time


class OriginChannels():

    def __init__(self, fhdhr, origin):
        self.fhdhr = fhdhr
        self.origin = origin

        self.base_api_url = 'https://api.pluto.tv'

    def get_channels(self):

        url = self.base_api_url + "/v2/channels.json"
        urlopn = self.fhdhr.web.session.get(url)
        pluto_chan_list = urlopn.json()

        channel_list = []
        for channel_dict in pluto_chan_list:

            if (channel_dict["isStitched"]
               and channel_dict["visibility"] in ["everyone"]
               and not channel_dict['onDemand']
               and channel_dict["name"] != "Announcement"):

                clean_station_item = {
                                     "name": channel_dict["name"],
                                     "callsign": channel_dict["name"],
                                     "number": str(channel_dict["number"]),
                                     "id": str(channel_dict["_id"]),
                                     }
                channel_list.append(clean_station_item)
        return channel_list

    def get_channel_stream(self, chandict):
        url = self.base_api_url + "/v2/channels.json"
        urlopn = self.fhdhr.web.session.get(url)
        pluto_chan_list = urlopn.json()
        pluto_chandict = self.get_channel_dict_pluto(pluto_chan_list, "_id", chandict["origin_id"])

        streamurl = pluto_chandict["stitched"]["urls"][0]["url"]
        streamurl = self.channel_stream_url_cleanup(streamurl)
        if self.fhdhr.config.dict["origin"]["force_best"]:
            streamurl = self.m3u8_beststream(streamurl)
        return streamurl

    def get_channel_dict_pluto(self, chanlist, keyfind, valfind):
        return next(item for item in chanlist if item[keyfind] == valfind)

    def channel_stream_url_cleanup(self, streamurl):

        streamurl = streamurl.replace("\\u0026", "&")
        streamurl_base = streamurl.split("?")[0]
        streamurl_params = streamurl.split("?")[1].split("&")

        paramdict = {}

        for param in streamurl_params:
            paramkey = param.split("=")[0]
            paramval = param.split("=")[1]
            paramdict[paramkey] = paramval

        paramdict["deviceMake"] = "Chrome"
        paramdict["deviceType"] = "web"
        paramdict["deviceModel"] = "Chrome"
        paramdict["sid"] = self.fhdhr.config.dict["main"]["uuid"] + str(time.time())
        paramdict["userId"] = self.origin.userid or ''

        paramdict["serverSideAds"] = "true"

        return streamurl_base + "?" + urllib.parse.urlencode(paramdict)

    def m3u8_beststream(self, m3u8_url):
        bestStream = None
        videoUrlM3u = m3u8.load(m3u8_url)
        if not videoUrlM3u.is_variant:
            return m3u8_url

        for videoStream in videoUrlM3u.playlists:
            if not bestStream:
                bestStream = videoStream
            elif videoStream.stream_info.bandwidth > bestStream.stream_info.bandwidth:
                bestStream = videoStream

        if not bestStream:
            return bestStream.absolute_uri
        else:
            return m3u8_url
