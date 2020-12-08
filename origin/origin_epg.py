import datetime

import fHDHR.tools


class OriginEPG():

    def __init__(self, fhdhr):
        self.fhdhr = fhdhr

        self.base_api_url = 'https://api.pluto.tv'

    def xmltimestamp_pluto(self, inputtime):
        xmltime = inputtime.replace('Z', '+00:00')
        xmltime = datetime.datetime.fromisoformat(xmltime)
        xmltime = xmltime.strftime('%Y%m%d%H%M%S %z')
        return xmltime

    def duration_pluto_minutes(self, induration):
        return ((int(induration))/1000/60)

    def pluto_calculate_duration(self, start_time, end_time):
        start_time = start_time.replace('Z', '+00:00')
        start_time = datetime.datetime.fromisoformat(start_time)

        end_time = end_time.replace('Z', '+00:00')
        end_time = datetime.datetime.fromisoformat(end_time)

        duration = (end_time - start_time).total_seconds() / 60
        return duration

    def update_epg(self, fhdhr_channels):
        programguide = {}

        todaydate = datetime.datetime.utcnow().date()
        self.remove_stale_cache(todaydate)

        time_list = []
        xtimestart = datetime.datetime.today().replace(hour=0, minute=0, second=0, microsecond=0)
        xtime = xtimestart
        xtimeend = datetime.datetime.utcnow() + datetime.timedelta(hours=6)
        while xtime <= xtimeend:
            guide_time = {"start": str(xtime.strftime('%Y-%m-%dT%H:00:00'))}
            if (xtime + datetime.timedelta(hours=6)) <= xtimeend:
                guide_time["end"] = str((xtime + datetime.timedelta(hours=6)).strftime('%Y-%m-%dT%H:00:00'))
            else:
                guide_time["end"] = str(xtimeend.strftime('%Y-%m-%dT%H:00:00'))
            xtime = xtime + datetime.timedelta(hours=6)
            time_list.append(guide_time)

        cached_items = self.get_cached(time_list)

        for result in cached_items:

            for c in result:

                if (c["isStitched"]
                   and c["visibility"] in ["everyone"]
                   and not c['onDemand']
                   and c["name"] != "Announcement"):

                    cdict = fHDHR.tools.xmldictmaker(c, ["name", "number", "_id", "timelines", "colorLogoPNG"], list_items=["timelines"])

                    chan_obj = fhdhr_channels.get_channel_obj("origin_id", cdict["_id"])

                    if str(chan_obj.dict['number']) not in list(programguide.keys()):

                        programguide[str(chan_obj.dict["number"])] = chan_obj.epgdict

                    for program_item in cdict["timelines"]:

                        progdict = fHDHR.tools.xmldictmaker(program_item, ['_id', 'start', 'stop', 'title', 'episode'])
                        episodedict = fHDHR.tools.xmldictmaker(program_item['episode'], ['duration', 'poster', '_id', 'rating', 'description', 'genre', 'subGenre', 'name'])

                        if not episodedict["duration"]:
                            episodedict["duration"] = self.pluto_calculate_duration(progdict["start"], progdict["stop"])
                        else:
                            episodedict["duration"] = self.duration_pluto_minutes(episodedict["duration"])

                        clean_prog_dict = {
                                            "time_start": self.xmltimestamp_pluto(progdict["start"]),
                                            "time_end": self.xmltimestamp_pluto(progdict["stop"]),
                                            "duration_minutes": episodedict["duration"],
                                            "thumbnail": None,
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
                        try:
                            thumbnail = episodedict["poster"]["path"].split("?")[0]
                        except TypeError:
                            thumbnail = None
                        clean_prog_dict["thumbnail"] = thumbnail

                        clean_prog_dict["genres"].extend(episodedict["genre"].split(" \\u0026 "))
                        clean_prog_dict["genres"].append(episodedict["subGenre"])

                        programguide[str(chan_obj.dict["number"])]["listing"].append(clean_prog_dict)

        return programguide

    def get_cached(self, time_list):
        for times in time_list:
            url = self.base_api_url + '/v2/channels?start=%s.000Z&stop=%s.000Z' % (times["start"], times["end"])
            self.get_cached_item(times["start"], url)
        cache_list = self.fhdhr.db.get_cacheitem_value("cache_list", "offline_cache", "origin") or []
        return [self.fhdhr.db.get_cacheitem_value(x, "offline_cache", "origin") for x in cache_list]

    def get_cached_item(self, cache_key, url):
        cache_key = datetime.datetime.strptime(cache_key, '%Y-%m-%dT%H:%M:%S').timestamp()
        cacheitem = self.fhdhr.db.get_cacheitem_value(str(cache_key), "offline_cache", "origin")
        if cacheitem:
            self.fhdhr.logger.info('FROM CACHE:  ' + str(cache_key))
            return cacheitem
        else:
            self.fhdhr.logger.info('Fetching:  ' + url)
            try:
                resp = self.fhdhr.web.session.get(url)
            except self.fhdhr.web.exceptions.HTTPError:
                self.fhdhr.logger.info('Got an error!  Ignoring it.')
                return
            result = resp.json()

            self.fhdhr.db.set_cacheitem_value(str(cache_key), "offline_cache", result, "origin")
            cache_list = self.fhdhr.db.get_cacheitem_value("cache_list", "offline_cache", "origin") or []
            cache_list.append(str(cache_key))
            self.fhdhr.db.set_cacheitem_value("cache_list", "offline_cache", cache_list, "origin")

    def remove_stale_cache(self, todaydate):
        cache_clear_time = todaydate.strftime('%Y-%m-%dT%H:00:00')
        cache_clear_time = datetime.datetime.strptime(cache_clear_time, '%Y-%m-%dT%H:%M:%S').timestamp()
        cache_list = self.fhdhr.db.get_cacheitem_value("cache_list", "offline_cache", "origin") or []
        cache_to_kill = []
        for cacheitem in cache_list:
            if float(cacheitem) < cache_clear_time:
                cache_to_kill.append(cacheitem)
                self.fhdhr.db.delete_cacheitem_value(str(cacheitem), "offline_cache", "origin")
                self.fhdhr.logger.info('Removing stale cache:  ' + str(cacheitem))
        self.fhdhr.db.set_cacheitem_value("cache_list", "offline_cache", [x for x in cache_list if x not in cache_to_kill], "origin")

    def clear_cache(self):
        cache_list = self.fhdhr.db.get_cacheitem_value("cache_list", "offline_cache", "origin") or []
        for cacheitem in cache_list:
            self.fhdhr.db.delete_cacheitem_value(cacheitem, "offline_cache", "origin")
            self.fhdhr.logger.info('Removing cache:  ' + str(cacheitem))
        self.fhdhr.db.delete_cacheitem_value("cache_list", "offline_cache", "origin")
