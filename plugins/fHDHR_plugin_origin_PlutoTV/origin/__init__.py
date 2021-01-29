import urllib.parse
import time
import json


class Plugin_OBJ():

    def __init__(self, plugin_utils):
        self.plugin_utils = plugin_utils

        self.base_api_url = 'https://api.pluto.tv'
        self.login_url = "%s/v1/auth/local" % self.base_api_url

        self.token = None
        self.userid = None

        self.login()

    def login(self):
        self.plugin_utils.logger.info("Logging into PlutoTV")
        if (not self.plugin_utils.config.dict["plutotv"]["username"] or not self.plugin_utils.config.dict["plutotv"]["password"]):
            self.plugin_utils.logger.warning("No Username/Password set, will operate in Guest Mode.")
            return True

        form_data = {
                      'optIn': 'true',
                      'password': self.plugin_utils.config.dict["plutotv"]["password"],
                      'synced': 'false',
                      'email': self.plugin_utils.config.dict["plutotv"]["username"]
                      }
        try:
            loginreq = self.plugin_utils.web.session.post(self.login_url, data=form_data)
            loginresp = json.loads(loginreq.content)
            if "accessToken" not in list(loginresp.keys()):
                self.plugin_utils.logger.warning("Login Failed, will use Guest Mode.")
                return True
            self.plugin_utils.logger.info("Login Success!")
        except Exception as e:
            self.plugin_utils.logger.warning("Login Failed, will use Guest Mode. %s" % e)
            return True
        self.userid = loginresp["_id"]
        self.token = loginresp["accessToken"]
        return True

    def get_channels(self):

        url = "%s/v2/channels.json" % self.base_api_url
        urlopn = self.plugin_utils.web.session.get(url)
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
        urlopn = self.plugin_utils.web.session.get(url)
        pluto_chan_list = urlopn.json()
        pluto_chandict = self.get_channel_dict_pluto(pluto_chan_list, chandict)
        if not pluto_chandict:
            return None

        streamurl = pluto_chandict["stitched"]["urls"][0]["url"]
        streamurl = self.channel_stream_url_cleanup(streamurl)

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
        paramdict["sid"] = self.plugin_utils.config.dict["main"]["uuid"] + str(time.time())
        paramdict["userId"] = self.userid or ''

        paramdict["serverSideAds"] = "true"

        return "%s?%s" % (streamurl_base, urllib.parse.urlencode(paramdict))
