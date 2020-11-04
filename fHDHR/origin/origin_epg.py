import datetime
import json
import time

import fHDHR.tools


class OriginEPG():

    def __init__(self, settings, logger, web):
        self.config = settings
        self.logger = logger
        self.web = web

        self.base_api_url = 'https://api.pluto.tv'
        self.web_cache_dir = self.config.dict["filedir"]["epg_cache"]["origin"]["web_cache"]

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
        xtimeend = xtimestart + datetime.timedelta(days=6)
        xtime = datetime.datetime.today().replace(hour=0, minute=0, second=0, microsecond=0)
        while xtime <= xtimeend:
            guide_time = {
                            "start": str(xtime.strftime('%Y-%m-%dT%H:00:00')),
                            "end": str((xtime + datetime.timedelta(hours=8)).strftime('%Y-%m-%dT%H:00:00')),
                            }
            xtime = xtime + datetime.timedelta(hours=8)
            time_list.append(guide_time)

        for times in time_list:
            url = self.base_api_url + '/v2/channels?start=%s.000Z&stop=%s.000Z' % (times["start"], times["end"])
            result = self.get_cached(times["start"], 3, url)

            for c in result:

                if (c["isStitched"]
                   and c["visibility"] in ["everyone"]
                   and not c['onDemand']
                   and c["name"] != "Announcement"):

                    cdict = fHDHR.tools.xmldictmaker(c, ["name", "number", "_id", "timelines", "colorLogoPNG"], list_items=["timelines"])

                    if str(cdict['number']) not in list(programguide.keys()):

                        programguide[str(cdict['number'])] = {
                                                                "callsign": cdict["name"],
                                                                "name": cdict["name"],
                                                                "number": str(cdict["number"]),
                                                                "id": cdict["_id"],
                                                                "thumbnail": None,
                                                                "listing": [],
                                                                }
                        try:
                            thumbnail = cdict["colorLogoPNG"]["path"].split("?")[0]
                        except TypeError:
                            thumbnail = None
                        programguide[str(cdict['number'])]["thumbnail"] = thumbnail

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

                        programguide[str(cdict["number"])]["listing"].append(clean_prog_dict)

        return programguide

    def get_cached(self, cache_key, delay, url):
        cache_key = datetime.datetime.strptime(cache_key, '%Y-%m-%dT%H:%M:%S').timestamp()
        cache_path = self.web_cache_dir.joinpath(str(cache_key))
        if cache_path.is_file():
            self.logger.info('FROM CACHE:  ' + str(cache_path))
            with open(cache_path, 'rb') as f:
                return json.load(f)
        else:
            self.logger.info('Fetching:  ' + url)
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
                self.logger.error(e)
                pass
            self.logger.info('Removing stale cache file:' + p.name)
            p.unlink()
