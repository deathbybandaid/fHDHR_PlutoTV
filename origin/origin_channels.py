import urllib.parse
import m3u8
import time


class OriginChannels():

    def __init__(self, fhdhr, origin):
        self.fhdhr = fhdhr
        self.origin = origin

        self.base_api_url = 'https://api.pluto.tv'

    def get_channels(self):

        url = "%s/v2/channels.json" % self.base_api_url
        urlopn = self.fhdhr.web.session.get(url)
        pluto_chan_list = urlopn.json()

        channel_list = []
        for channel_dict in pluto_chan_list:

            if (channel_dict["isStitched"]
               and channel_dict["visibility"] in ["everyone"]
               and not channel_dict['onDemand']
               and channel_dict["name"] != "Announcement"):

                thumbnails = []
                for thumb_opt in ["colorLogoPNG", "colorLogoSVG", "solidLogoSVG",
                                  "solidLogoPNG", "thumbnail", "logo", "featuredImage"]:

                    try:
                        thumbnail = channel_dict[thumb_opt]["path"].split("?")[0]
                    except TypeError:
                        thumbnail = None
                    if thumbnail:
                        thumbnails.append(thumbnail)
                if not len(thumbnails):
                    thumbnails = [None]

                clean_station_item = {
                                     "name": channel_dict["name"],
                                     "callsign": channel_dict["name"],
                                     "number": str(channel_dict["number"]),
                                     "id": str(channel_dict["_id"]),
                                     "thumbnail": thumbnails[0]
                                     }
                channel_list.append(clean_station_item)
        return channel_list

    def get_channel_stream(self, chandict, stream_args):
        url = "%s/v2/channels.json" % self.base_api_url
        urlopn = self.fhdhr.web.session.get(url)
        pluto_chan_list = urlopn.json()
        pluto_chandict = self.get_channel_dict_pluto(pluto_chan_list, chandict)
        if not pluto_chandict:
            return None

        streamurl = pluto_chandict["stitched"]["urls"][0]["url"]
        streamurl = self.channel_stream_url_cleanup(streamurl)
        if self.fhdhr.config.dict["origin"]["force_best"]:
            streamurl = self.m3u8_beststream(streamurl)

        stream_info = {"url": streamurl}

        return stream_info

    def get_channel_dict_pluto(self, pluto_chan_list, chandict):
        for item in pluto_chan_list:
            if str(item["_id"]) == str(chandict["origin_id"]):
                return item
        for item in pluto_chan_list:
            if str(item["number"]) == str(chandict["origin_number"]):
                return item
        return None

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

        return "%s?%s" % (streamurl_base, urllib.parse.urlencode(paramdict))

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
            print(videoStream.stream_info.resolution)
            print(videoStream.stream_info.resolution[0])
            print(videoStream.stream_info.resolution[1])

        if not bestStream:
            return bestStream.absolute_uri
        else:
            return m3u8_url
