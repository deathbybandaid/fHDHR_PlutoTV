
from .plutotv_html import PlutoTV_HTML


class Plugin_OBJ():

    def __init__(self, fhdhr, plugin_utils):
        self.fhdhr = fhdhr
        self.plugin_utils = plugin_utils

        self.plutotv_html = PlutoTV_HTML(fhdhr, plugin_utils)
