import datetime

import fHDHR.tools


class OriginEPG():

    def __init__(self, fhdhr):
        self.fhdhr = fhdhr

        self.base_api_url = 'https://api.pluto.tv'

    def xmltimestamp_pluto(self, inputtime):
        xmltime = inputtime.replace('Z', '+00:00')
        xmltime = datetime.datetime.fromisoformat(xmltime).timestamp()
        return xmltime

    def duration_pluto_minutes(self, induration):
        return ((int(induration))/1000/60)

    def update_epg(self, fhdhr_channels):
        programguide = {}

        xtime = datetime.datetime.utcnow()

        guide_time = {
                    "start": str(xtime.strftime('%Y-%m-%dT%H:00:00')),
                    "end": str((xtime + datetime.timedelta(hours=8)).strftime('%Y-%m-%dT%H:00:00')),
                    }

        epgurl = '%s/v2/channels?start=%s.000Z&stop=%s.000Z' % (self.base_api_url, guide_time["start"], guide_time["end"])

        result = self.fhdhr.web.session.get(epgurl).json()

        for c in result:

            if (c["isStitched"]
               and c["visibility"] in ["everyone"]
               and not c['onDemand']
               and c["name"] != "Announcement"):

                cdict = fHDHR.tools.xmldictmaker(c, ["name", "number", "_id", "timelines", "colorLogoPNG"], list_items=["timelines"])

                chan_obj = fhdhr_channels.get_channel_obj("origin_id", cdict["_id"])

                if str(chan_obj.dict['number']) not in list(programguide.keys()):

                    programguide[str(chan_obj.number)] = chan_obj.epgdict

                for program_item in cdict["timelines"]:

                    progdict = fHDHR.tools.xmldictmaker(program_item, ['_id', 'start', 'stop', 'title', 'episode'])
                    episodedict = fHDHR.tools.xmldictmaker(program_item['episode'], ['duration', 'poster', '_id', 'rating', 'description', 'genre', 'subGenre', 'name'])

                    if episodedict["duration"]:
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
                                            "id": str(episodedict['_id'] or "%s_%s" % (chan_obj.dict['origin_id'], self.xmltimestamp_pluto(progdict["start"])))
                                            }
                        try:
                            thumbnail = episodedict["poster"]["path"].split("?")[0]
                        except TypeError:
                            thumbnail = None
                        clean_prog_dict["thumbnail"] = thumbnail

                        clean_prog_dict["genres"].extend(episodedict["genre"].split(" \\u0026 "))
                        clean_prog_dict["genres"].append(episodedict["subGenre"])

                        if not any((d['time_start'] == clean_prog_dict['time_start'] and d['id'] == clean_prog_dict['id']) for d in programguide[chan_obj.number]["listing"]):
                            programguide[str(chan_obj.number)]["listing"].append(clean_prog_dict)

        return programguide
