import json


class OriginService():

    def __init__(self, fhdhr):
        self.fhdhr = fhdhr

        self.base_api_url = 'https://api.pluto.tv'
        self.login_url = self.base_api_url + '/v1/auth/local'

        self.token = None
        self.userid = None

        self.login()

    def login(self):
        self.fhdhr.logger.info("Logging into PlutoTV")
        if (not self.fhdhr.config.dict["origin"]["username"] or not self.fhdhr.config.dict["origin"]["password"]):
            self.fhdhr.logger.warning("No Username/Password set, will operate in Guest Mode.")
            return True

        form_data = {
                      'optIn': 'true',
                      'password': self.fhdhr.config.dict["origin"]["password"],
                      'synced': 'false',
                      'email': self.fhdhr.config.dict["origin"]["username"]
                      }
        try:
            loginreq = self.fhdhr.web.session.post(self.login_url, data=form_data)
            loginresp = json.loads(loginreq.content)
            if "accessToken" not in list(loginresp.keys()):
                self.fhdhr.logger.warning("Login Failed, will use Guest Mode.")
                return True
            self.fhdhr.logger.info("Login Success!")
        except Exception as e:
            self.fhdhr.logger.warning("Login Failed, will use Guest Mode. " + str(e))
            return True
        self.userid = loginresp["_id"]
        self.token = loginresp["accessToken"]
        return True
