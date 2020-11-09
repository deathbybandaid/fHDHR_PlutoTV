import json


class OriginService():

    def __init__(self, settings, logger, web):
        self.config = settings
        self.logger = logger
        self.web = web

        self.base_api_url = 'https://api.pluto.tv'
        self.login_url = self.base_api_url + '/v1/auth/local'

        self.token = None
        self.userid = None

        self.login()

    def login(self):
        self.logger.info("Logging into PlutoTV")
        if (not self.config.dict["origin"]["username"] or not self.config.dict["origin"]["password"]):
            self.logger.warning("No Username/Password set, will operate in Guest Mode.")
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
                self.logger.warning("Login Failed, will use Guest Mode.")
                return True
            self.logger.info("Login Success!")
        except Exception as e:
            self.logger.warning("Login Failed, will use Guest Mode. " + str(e))
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
