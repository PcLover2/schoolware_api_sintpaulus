import requests
from datetime import date, datetime, timedelta
from playwright.sync_api import sync_playwright
import threading
import logging
import json


class schoolware:

    def __init__(self, config) -> None:
        """Pass config dict to init class
        Args:
        | Key | Description |
        | --- | --- |
        | domain | domain name of schoolware
        | user | school microsoft email
        | password | school microsoft password

        | telegram_bot_token | telegram bot token to enable telegram bot
        | telegram_chat_id | id to send messages to
        | verbose | show a some more info, when what function is run
        | debug | show a lot more info, all networking info

        | jaartotaal | Enable jaartotaal
        |  | 
        """
        self.token = ""
        self.cookie = ""
        self.rooster = []
        self.todo_list = []
        self.scores = []

        self.config = config
        required_keys = ['domain', 'user', 'password']

        optional_keys = {
            'debug': False,
            'debugMicro': False,
            'verbose': False,
            'schoolware_login': False,

            "telegram_enabled": False,
            "telegram_bot_token": "",
            "telegram_chat_id": "",
            'telegram_msg': "",
        }

        # check required keys
        for key in required_keys:
            if key not in config:
                raise ValueError(
                    f"Required key '{key}' is missing in the config file.")
            else:
                setattr(self, key, config[key])

        # check optional keys
        for key, default_value in optional_keys.items():
            value = config.get(key, default_value)
            setattr(self, key, value)

        if (self.debug):
            logging.basicConfig(
                format='[%(levelname)s] %(asctime)s - %(message)s', level=logging.DEBUG)

        elif (self.verbose):
            logging.basicConfig(
                format='[%(levelname)s] %(asctime)s - %(message)s', level=logging.INFO)
        else:
            logging.basicConfig(
                format='[%(levelname)s] %(asctime)s - %(message)s', level=logging.WARNING)


        self.verbose_print(message="starting schoolware_api", level=1)

        if (self.telegram_enabled):
            self.prev_scores = self.punten()
            self.telegram_setup()


# Token&cookie stuff

    def get_new_token(self):
        ########## VERBOSE##########
        self.verbose_print("get_token")
        ########## VERBOSE##########

        with sync_playwright() as p:
            if(self.debugMicro):
                browser = p.chromium.launch(headless=False)
        
            else:
                browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:108.0) Gecko/20100101 Firefox/108.0")
            page = context.new_page()
            try:
                page.goto(
                    f"https://{self.domain}/webleerling/start.html#!fn=llagenda")
                page.locator("#ext-comp-1014-btnEl").click()
                page.get_by_role("textbox").fill(self.user)
                page.get_by_text("Next").click()
                page.get_by_placeholder("Password").fill(self.password)
                page.get_by_text("Sign In").click()
                page.wait_for_load_state()
                if (context.cookies()[0]["name"] == "FPWebSession"):
                    self.token = context.cookies()[0]["value"]
                    self.cookie = dict(FPWebSession=self.token)
            except:
                page.screenshot(path="playwright.png", full_page=True)
                raise Exception("error when getting token, check email and password")
            browser.close()
            ########## VERBOSE##########
            self.verbose_end("get_token")
            ########## VERBOSE##########
            return self.token

    def get_new_token_schoolware(self):
        ########## VERBOSE##########
        self.verbose_print("get_token_schoolware")
        ########## VERBOSE##########
        url = f"https://{self.domain}/webleerling/bin/server.fcgi/RPC/ROUTER/"
        payload = "{action: \"WisaUserAPI\", method: \"Authenticate\", data: [\"" + \
            self.user+"\",\""+self.password+"\"], type: \"rpc\", tid: 1}"
        r = requests.request("POST", url, data=payload)
        self.cookie = requests.utils.dict_from_cookiejar(r.cookies)
        self.token = self.cookie["FPWebSession"]
        ########## VERBOSE##########
        self.verbose_end("get_token_schoolware")
        ########## VERBOSE##########
        return self.token

    def get_token(self):
        self.make_request(
            "https://{self.domain}/webleerling/bin/server.fcgi/REST/myschoolwareaccount")
        return self.token

    def make_request(self, url):
        r = requests.get(url, cookies=self.cookie)

        if (r.status_code != 200):
            if (r.status_code == 401):
                ########## VERBOSE##########
                self.verbose_end("check_token invalid")
                ########## VERBOSE##########
                if (not self.schoolware_login):
                    self.verbose_end("Using Microsoft login")
                    self.get_new_token()
                    r = requests.get(url, cookies=self.cookie)
                else:
                    self.verbose_end("Using Schoolware login")
                    self.get_new_token_schoolware()
                    r = requests.get(url, cookies=self.cookie)
            else:
                self.verbose_end(f"check_token error {r.status_code}")
                raise "error with token"
        else:
            ########## VERBOSE##########
            self.verbose_end("check_token")
            ########## VERBOSE##########
        return r


# todo

    def todo(self):
        """gets all todo items from schoolware

        Returns:
            list: returns all todo items in a list ordered by descending date
        """
        ########## VERBOSE##########
        self.verbose_print("todo")
        ########## VERBOSE##########

        task_data = self.make_request(
            f"https://{self.domain}/webleerling/bin/server.fcgi/REST/AgendaPunt/?_dc=1665240724814&MinVan={date.today()}T00:00:00").json()["data"]
        self.todo_list = []

        for taak in task_data:
            soort = "unknown"  # Initialize soort with a default value
            if (taak["TypePunt"] == 1000):
                soort = "Taak"
            elif (taak["TypePunt"] == 100):
                soort = "Grote toets"
            elif (taak["TypePunt"] == 101):
                soort = "Kleine toets"
            elif (taak["TypePunt"] == 1002):
                soort = "Kleine taak"
            elif (taak["TypePunt"] == 1001):
                soort = "Grote taak"
            elif (taak["TypePunt"] == 9):
                soort = "Aandachtspunt"

            if soort != "unknown":  # Check if the soort is not "unknown"
                    vak = taak["VakNaam"]
                    titel = taak["Titel"]
                    onderwerp = taak["Commentaar"]
                    eind_time = taak["Tot"].split(' ')[0]
                    dt = datetime.strptime(taak["Tot"].split(' ')[0], '%Y-%m-%d')

                    self.todo_list.append({
                        "soort": soort,
                        "vak": vak,
                        "titel": titel,
                        "onderwerp": onderwerp,
                        "datum": eind_time,
                    })
        ########## VERBOSE##########
        self.verbose_end("todo")
        ########## VERBOSE##########
        return self.todo_list

# punten
    def punten(self):
        """Gets points from the whole year

        Returns:
            list: A list containing the points orderd by descending date
        """
        ########## VERBOSE##########
        self.verbose_print("punten")
        ########## VERBOSE##########

        punten_data = self.make_request(
            f"https://{self.domain}/webleerling/bin/server.fcgi/REST/PuntenbladGridLeerling?BeoordelingMomentVan=1990-09-01+00:00:00")
        punten_data = punten_data.json()["data"]
        self.scores = []
        for vak in punten_data:

            for punt in vak["Beoordelingen"]:
                try:
                    vak = punt["IngerichtVakNaamgebruiker"]
                    try:
                        DW = punt["DagelijksWerkCode"]
                        EX = None
                    except:
                        DW = None
                        EX = punt["ExamenCode"]
                    totale_score = float(punt["BeoordelingMomentNoemer"])
                    gewenste_score = float(
                        punt["BeoordelingMomentGewenstAsString"])
                    try:
                        behaalde_score = float(
                            punt["BeoordelingWaarde"]["NumeriekAsString"])
                    except:
                        behaalde_score = "n/a"
                    publicatie_datum = punt["BeoordelingMomentPublicatieDatum"]
                    datum = punt["BeoordelingMomentDatum"]
                    titel = punt["BeoordelingMomentOmschrijving"]
                    dt = datetime.strptime(
                        punt["BeoordelingMomentDatum"].split(' ')[0], '%Y-%m-%d')
                    day = dt.strftime('%A')

                    pub_dt = datetime.strptime(
                        punt["BeoordelingMomentPublicatieDatum"].split(' ')[0], '%Y-%m-%d')
                    pub_day = pub_dt.strftime('%A')
                    if (punt["BeoordelingMomentType_"] == "bmtToets"):
                        soort = "toets"
                    else:
                        soort = "taak"

                    try:
                        cat = punt["BeoordelingMomentCategorieOmschrijving"]
                    except:
                        cat = None

                    self.scores.append({
                        "soort": soort,
                        "vak": vak,
                        "titel": titel,
                        "DW": DW,
                        "EX": EX,
                        "tot_sc": totale_score,
                        "gew_sc": gewenste_score,
                        "score": behaalde_score,
                        "datum": datum,
                        "pub_datum": publicatie_datum,
                        "day": day,
                        "pub_day": pub_day,
                        "cat": cat
                    })
                except:
                    pass
        self.scores.sort(key=lambda x: datetime.strptime(
            x['datum'], '%Y-%m-%d %H:%M:%S'), reverse=True)
        ########## VERBOSE##########
        self.verbose_end("punten")
        ########## VERBOSE##########
        return self.scores

# agenda
    def agenda(self, datum=""):
        """Gets all agenda points of a given date from schoolware

        Args:
            datum (str, optional): Date to get agenda for. Defaults to "".

        Returns:
            list: returns output from filter_agenda
        """
        ########## VERBOSE##########
        self.verbose_print("agenda")
        ########## VERBOSE##########
        # begin en einde week
        day = str(date.today())
        if (datum == ""):
            dt = datetime.strptime(day, '%Y-%m-%d')
        else:
            datum = str(datum).split(' ')[0]
            dt = datetime.strptime(datum, '%Y-%m-%d')
        start = dt.strftime("%Y-%m-%d")
        end = (dt + timedelta(days=1)).strftime("%Y-%m-%d")
        ####
        agenda_data = self.make_request(
            f"https://{self.domain}/webleerling/bin/server.fcgi/REST/AgendaPunt/?MaxVan={end}&MinTot={start}").json()["data"]
        self.rooster = []
        for agenda in agenda_data:
            if (agenda["TypePunt"] == 1 or agenda["TypePunt"] == 2):
                self.rooster.append(agenda)
        ########## VERBOSE##########
        self.verbose_end("agenda")
        ########## VERBOSE##########
        return self.filter_rooster(self.rooster, datum)

    def agenda_week(self, datum=""):
        days = []
        day = str(date.today())
        if (datum == ""):
            dt = datetime.strptime(day, '%Y-%m-%d')
        else:
            datum = str(datum).split(' ')[0]
            dt = datetime.strptime(datum, '%Y-%m-%d')

        # get start of week
        days_to_subtract = dt.weekday()
        start = dt - timedelta(days=days_to_subtract)

        for i in range(5):
            day_week = start + timedelta(days=i)
            days.append({
                "date": day_week.strftime("%A %d/%m"),
                "points": self.agenda(day_week)
            })
        self.verbose_print(days)
        return days

    def filter_rooster(self, rooster, datum=""):
        """Internal function to filter a agenda rooster of a given date

        Args:
            rooster (list): The agenda points to filter
            datum (str, optional): The date to filter agenda points for. Defaults to "".

        Returns:
            list: Filters agenda points for a given date and points
        """
        ########## VERBOSE##########
        self.verbose_print("filter_agenda")
        ########## VERBOSE##########
        today = []
        if (datum == ""):
            datum = datetime.today()
        datum = str(datum).split(' ')[0]
        for agenda in rooster:
            if (str(agenda['Van'].split(' ')[0]) == datum):
                vak = agenda['VakNaam']
                lokaal = agenda['LokaalCode']
                titel = agenda['Titel']
                commentaar = agenda["Commentaar"]
                if (commentaar != ""):
                    commentaar = json.loads(commentaar)
                    commentaar = commentaar["leerlingen"]

                uur = agenda['Van'].split(' ')[1]

                today.append({
                    "vak": vak,
                    "lokaal": lokaal,
                    "titel": titel,
                    "commentaar": commentaar,
                    "uur": uur,
                    "skip": False,
                })
        today_filterd = []

        for index, agenda in enumerate(today):
            if (not agenda["skip"]):

                if (index == (len(today)-1)):
                    today_filterd.append(agenda)
                    continue

                if (agenda["uur"] == today[index+1]["uur"]):
                    if (agenda["vak"] == agenda["titel"]):
                        agenda["skip"] = True
                    elif (today[index+1]["vak"] == today[index+1]["titel"]):
                        today[index+1]["skip"] = True
                        today_filterd.append(agenda)
                else:
                    today_filterd.append(agenda)
        ########## VERBOSE##########
        self.verbose_end("filter-agenda")
        ########## VERBOSE##########

        return today_filterd

    ########## OTHER##########

    # telegram bot
    def telegram_setup(self):
        """The setup function for Telegram
        """
        import telegram
        
        self.bot = telegram.Bot(self.telegram_bot_token)
        telegram = threading.Thread(target=self.telegram_main)
        self.verbose_print("Starting telegram",1)
        telegram.start()

    def telegram_main(self):
        import asyncio
        from time import sleep

        while True:
            try:
                new_scores = self.punten()
                if (len(self.prev_scores) < len(new_scores)):
                    diff_list = [
                        i for i in new_scores if i not in self.prev_scores]
                    diff = len(diff_list)
                    self.prev_scores = new_scores

                    if (self.telegram_msg == ""):
                        msg = f"{diff} New points:\n"
                        for item in diff_list:
                            msg = msg + \
                                f"{item['vak']} {item['titel']}: {float(item['score']) * float(item['tot_sc']) if item['score'] != 'n/a' else 'n/a'}/{item['tot_sc']}\n"
                    else:
                        eval(self.telegram_msg)

                    self.verbose_print(
                        message=f"telegram send msg msg={msg}", level=1)
                    asyncio.run(self.telegram_send_msg(msg))
                else:
                    self.verbose_print(
                        message=f"telegram no new points", level=0)
            except Exception as e:
                logging.error(e)
            sleep(5*60)

    async def telegram_send_msg(self, msg):
        """Function to send a telegram message to a set message-id

        Args:
            msg (string): the message to send in telegram msg
        """
        async with self.bot:
            await self.bot.send_message(text=msg, chat_id=self.telegram_chat_id)

    ########## VERBOSE##########
    def verbose_print(self, message, level=0):
        """Prints starting message

        Args:
            message (string): name to print
            level (int, optional): 1=info, 0=debug. Defaults to 0.
        """
        if (self.verbose):
            logging.debug(f"starting {message}")

        if (level == 1):
            logging.info(f"{message}")

    def verbose_end(self, message):
        """Ends self.verbose_print with done

        Args:
            message (string): name of function to display
        """
        if (self.verbose):
            logging.debug(f"Done {message}")

    ########## VERBOSE##########
