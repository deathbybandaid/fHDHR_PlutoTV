import json
import urllib.parse
import m3u8

import fHDHR.tools


class OriginService():

    def __init__(self, settings):
        self.config = settings

        self.web = fHDHR.tools.WebReq()

        self.base_api_url = 'https://api.pluto.tv'
        self.login_url = self.base_api_url + '/v1/auth/local'

        self.token = None
        self.userid = None

        self.login()

    def login(self):
        print("Logging into PlutoTV")
        if (not self.config.dict["origin"]["username"] or not self.config.dict["origin"]["password"]):
            print("No Username/Password set, will operate in Guest Mode.")
            return True

        form_data = {
                      'optIn': 'true',
                      'password': self.config.dict["origin"]["password"],
                      'synced': 'false',
                      'email': self.config.dict["origin"]["username"]
                      }
        try:
            loginreq = self.web.session.post(self.login_url, data=form_data)
            loginresp = json.loads(loginreq.content)
            if "accessToken" not in list(loginresp.keys()):
                print("Login Failed, will use Guest Mode.")
                return True
            print("Login Success!")
        except Exception as e:
            print("Login Failed, will use Guest Mode. " + str(e))
            return True
        self.userid = loginresp["_id"]
        self.token = loginresp["accessToken"]
        return True

    def get_status_dict(self):
        ret_status_dict = {
                            "Login": "Success" if self.userid else "Guest Mode",
                            "Username": self.config.dict["origin"]["username"],
                            }
        return ret_status_dict

    def get_channels(self):

        url = self.base_api_url + "/v2/channels.json"
        urlopn = self.web.session.get(url)
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

    def get_channel_stream(self, chandict, allchandict):
        caching = True
        streamlist = []
        streamdict = {}

        url = self.base_api_url + "/v2/channels.json"
        urlopn = self.web.session.get(url)
        pluto_chan_list = urlopn.json()
        pluto_chandict = self.get_channel_dict_pluto(pluto_chan_list, "_id", chandict["id"])

        streamurl = pluto_chandict["stitched"]["urls"][0]["url"]
        streamurl = self.channel_stream_url_cleanup(streamurl)
        if self.config.dict["origin"]["force_best"]:
            streamurl = self.m3u8_beststream(streamurl)
        streamdict = {"number": str(chandict["number"]), "stream_url": streamurl}
        streamlist.append(streamdict)
        return streamlist, caching

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
        paramdict["sid"] = self.config.dict["main"]["uuid"]
        paramdict["userId"] = self.userid or ''

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
