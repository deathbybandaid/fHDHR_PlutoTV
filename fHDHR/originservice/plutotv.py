import time
import json
import datetime
import urllib.parse
import m3u8

import fHDHR.tools


class fHDHRservice():
    def __init__(self, settings):
        self.config = settings

        self.web = fHDHR.tools.WebReq()

        self.base_api_url = 'https://api.pluto.tv'
        self.login_url = self.base_api_url + '/v1/auth/local'
        self.web_cache_dir = self.config.dict["filedir"]["epg_cache"]["origin"]["web_cache"]

        self.token = None
        self.userid = None

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

    def get_channels(self):

        url = self.base_api_url + "/v2/channels.json"
        urlopn = self.web.session.get(url)
        pluto_chan_list = urlopn.json()

        channel_list = []
        for channel_dict in pluto_chan_list:

            if (channel_dict["isStitched"]
               and channel_dict["visibility"] in ["everyone"]
               and not channel_dict['onDemand']):

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

    def get_channel_thumbnail(self, channel_id):
        channel_thumb_url = ("http://images.pluto.tv/channels/%s/logo.png" % str(channel_id))
        return channel_thumb_url

    def get_content_thumbnail(self, content_id):
        item_thumb_url = ("https://images.pluto.tv/episodes/%s/poster.jpg" % str(content_id))
        return item_thumb_url

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
        print(m3u8_url)
        bestStream = None
        videoUrlM3u = m3u8.load(m3u8_url)
        if not len(videoUrlM3u.playlists):
            return m3u8_url
        for videoStream in videoUrlM3u.playlists:
            if bestStream is None:
                bestStream = videoStream
            elif ((videoStream.stream_info.resolution[0] > bestStream.stream_info.resolution[0]) and
                  (videoStream.stream_info.resolution[1] > bestStream.stream_info.resolution[1])):
                bestStream = videoStream
            elif ((videoStream.stream_info.resolution[0] == bestStream.stream_info.resolution[0]) and
                  (videoStream.stream_info.resolution[1] == bestStream.stream_info.resolution[1]) and
                  (videoStream.stream_info.bandwidth > bestStream.stream_info.bandwidth)):
                bestStream = videoStream
        if bestStream is not None:
            return bestStream.absolute_uri

    def update_epg(self):
        programguide = {}

        todaydate = datetime.datetime.utcnow().date()
        self.remove_stale_cache(todaydate)

        for x in range(0, 6):
            xdate = todaydate + datetime.timedelta(days=x)
            xtdate = xdate + datetime.timedelta(days=1)

            for i in range(int(24 / 4)):
                start_hour = (i * 4)
                url_start_time = xdate.strftime('%Y-%m-%dT' + str("{:02d}".format(start_hour)) + ':00:00')
                if start_hour + 4 < 24:
                    url_end_time = xdate.strftime('%Y-%m-%dT' + str("{:02d}".format(start_hour + 4)) + ':00:00')
                else:
                    url_end_time = xtdate.strftime('%Y-%m-%dT%H:00:00')

                url = self.base_api_url + '/v2/channels?start=%s.000Z&stop=%s.000Z' % (url_start_time, url_end_time)
                result = self.get_cached(url_start_time, 3, url)

                for c in result:

                    cdict = fHDHR.tools.xmldictmaker(c, ["name", "number", "_id", "timelines"], list_items=["timelines"])

                    if str(cdict['number']) not in list(programguide.keys()):

                        programguide[str(cdict['number'])] = {
                                                                "callsign": cdict["name"],
                                                                "name": cdict["name"],
                                                                "number": str(cdict["number"]),
                                                                "id": cdict["_id"],
                                                                "thumbnail": self.get_channel_thumbnail(cdict["_id"]),
                                                                "listing": [],
                                                                }
                    for program_item in cdict["timelines"]:

                        progdict = fHDHR.tools.xmldictmaker(program_item, ['_id', 'start', 'stop', 'title', 'episode'])
                        episodedict = fHDHR.tools.xmldictmaker(program_item['episode'], ['duration', 'poster', '_id', 'rating', 'description', 'genre', 'subGenre', 'name'])

                        clean_prog_dict = {
                                            "time_start": self.xmltimestamp_pluto(progdict["start"]),
                                            "time_end": self.xmltimestamp_pluto(progdict["stop"]),
                                            "duration_minutes": self.duration_pluto_minutes(episodedict["duration"]),
                                            "thumbnail": self.get_content_thumbnail(progdict["_id"]),
                                            "title": progdict['title'] or "Unavailable",
                                            "sub-title": episodedict['name'] or "Unavailable",
                                            "description": episodedict['description'] or "Unavailable",
                                            "rating": episodedict['rating'] or "N/A",
                                            "episodetitle": None,
                                            "releaseyear": None,
                                            "genres": [],
                                            "seasonnumber": None,
                                            "episodenumber": None,
                                            "isnew": False,
                                            "id": episodedict['_id'] or self.xmltimestamp_pluto(progdict["start"]),
                                            }

                        clean_prog_dict["genres"].extend(episodedict["genre"].split(" \\u0026 "))
                        clean_prog_dict["genres"].append(episodedict["subGenre"])

                        programguide[str(cdict["number"])]["listing"].append(clean_prog_dict)

        return programguide

    def get_cached(self, cache_key, delay, url):
        cache_key = datetime.datetime.strptime(cache_key, '%Y-%m-%dT%H:%M:%S').timestamp()
        cache_path = self.web_cache_dir.joinpath(str(cache_key))
        if cache_path.is_file():
            print('FROM CACHE:', str(cache_path))
            with open(cache_path, 'rb') as f:
                return json.load(f)
        else:
            print('Fetching:  ', url)
            urlopn = self.web.session.get(url)
            result = urlopn.json()
            with open(cache_path, 'wb') as f:
                f.write(json.dumps(result).encode("utf-8"))
            time.sleep(int(delay))
            return result

    def remove_stale_cache(self, todaydate):
        cache_clear_time = todaydate.strftime('%Y-%m-%dT%H:00:00')
        cache_clear_time = datetime.datetime.strptime(cache_clear_time, '%Y-%m-%dT%H:%M:%S').timestamp()
        for p in self.web_cache_dir.glob('*'):
            try:
                cachedate = float(p.name)
                if cachedate >= cache_clear_time:
                    continue
            except Exception as e:
                print(e)
                pass
            print('Removing stale cache file:', p.name)
            p.unlink()

    def xmltimestamp_pluto(self, inputtime):
        xmltime = inputtime.replace('Z', '+00:00')
        xmltime = datetime.datetime.fromisoformat(xmltime)
        xmltime = xmltime.strftime('%Y%m%d%H%M%S %z')
        return xmltime

    def duration_pluto_minutes(self, induration):
        return ((int(induration))/1000/60)
