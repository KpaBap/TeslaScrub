"""
  _______        _        _____                 _
 |__   __|      | |      / ____|               | |
    | | ___  ___| | __ _| (___   ___ _ __ _   _| |__
    | |/ _ \/ __| |/ _` |\___ \ / __| '__| | | | '_ \
    | |  __/\__ \ | (_| |____) | (__| |  | |_| | |_) |
    |_|\___||___/_|\__,_|_____/ \___|_|   \__,_|_.__/

			Where is my Model 3, Elon?
"""
import os
import time
import logging
import requests
import smtplib

from logging.handlers import RotatingFileHandler
from urllib.parse import urlparse
from configparser import ConfigParser
from bs4 import BeautifulSoup

log = logging.getLogger()

config = ConfigParser()
config.read('config.ini')


def setup_logging():
	LOG_PATH = "{}/{}.log".format(os.path.dirname(os.path.realpath(__file__)),
								  os.path.basename(__file__).replace(".py", ""))

	if config.getboolean('Internal', 'Debug'):
		log.setLevel(logging.DEBUG)
	else:
		log.setLevel(logging.INFO)
	formatter = logging.Formatter('[ %(asctime)s ] [ %(levelname)5s ] [ %(name)s.%(funcName)s:%(lineno)s ] %(message)s')
	handler = RotatingFileHandler(LOG_PATH, maxBytes=5 * 1024 ** 2, backupCount=5)
	handler.setFormatter(formatter)
	log.addHandler(handler)

	# Quiet down requests lib as it prints private info
	logging.getLogger("requests.packages.urllib3").setLevel(logging.INFO)

def send_email(subject, body, from_email=config['Email']['FROM'], to_email=config['Email']['TO'], force=False):
	seconds_left_to_boring_email = time.time() % int(config['Email']['BORING_EMAIL_FREQUENCY'])

	if seconds_left_to_boring_email < int(config['Email']['CRONJOB_FREQUENCY']) or force:
		email_text = f"""From: {from_email}\r\nTo: {to_email}\r\nSubject: {subject}\r\n\r\n{body}"""
		log.debug(f"Email contents: {email_text}")
		try:
			server = smtplib.SMTP(config['SMTP']['SERVER'], int(config['SMTP']['PORT']))
			server.ehlo()
			if config.getboolean('SMTP', 'USE_TLS'):
				server.starttls()
			server.login(config['SMTP']['USERNAME'], config['SMTP']['PASSWORD'])
			server.sendmail(from_email, to_email, email_text)
			log.info(f"Email successfully sent to {to_email}")
		except Exception:
			log.exception("Exception while sending email:")
	else:
		minutes_left = round(seconds_left_to_boring_email/60)
		log.info(f"Skipping sending email. Will send it in {minutes_left} minutes.")

class ScrubbingError(Exception):
	pass

class ProfileScrubber():
	def __init__(self, email_to, tesla_username, tesla_password):
		self.session = requests.Session()
		self.tesla_username = tesla_username
		self.tesla_password = tesla_password
		self.email_to = email_to
		self.__reservation_numbers = []
		self.log = logging.getLogger(str(self))
		self.LOGIN_URL = str(config['Tesla']['LOGIN_URL'])

	def __repr__(self):
		return "TeslaProfileScrubber"

	def get_csrf_token(self):
		login_page = self.session.get(self.LOGIN_URL)
		login_page.raise_for_status()

		self.log.debug(f"Login page contents: {login_page.text.encode('utf-8')}")

		login_page = BeautifulSoup(login_page.text, "html.parser")
		self.log.info(f"Loaded Tesla login page from {self.LOGIN_URL}")

		self.csrf_token = ""
		try:
			self.csrf_token = login_page.find('input', {'name':'_csrf'}).get('value')
		except AttributeError:
			pass

		if not self.csrf_token:
			self.error("Could not find CSRF token in login page.")

		self.log.info(f"Found CSRF token.")
		self.log.debug(f"CSRF token value: {self.csrf_token}")

	def log_in(self):
		data = {
			"user": '',
			"_csrf": self.csrf_token,
			"email": self.tesla_username,
			'password': self.tesla_password
		}

		headers = {
			'Origin': "{}://{}".format(*urlparse(self.LOGIN_URL)[0:2]),
			'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/66.0.3359.117 Safari/537.36',
			'Referer': self.LOGIN_URL
		}
		resp = self.session.post(self.LOGIN_URL, data=data, headers=headers)
		resp.raise_for_status()
		self.profile_page = resp.text

		if not self.profile_page:
			self.error("Profile page failed to load.")

		self.log.info(f"Loaded Tesla profile page from {self.LOGIN_URL}")
		self.log.debug(f"Profile page contents: {self.profile_page.encode('utf-8')}")

	def error(self, message):
		self.log.error(message)
		raise ScrubbingError(message)

	def find_reservation_numbers(self):
		account_page = BeautifulSoup(self.profile_page, "html.parser")
		car_links = account_page.find_all(class_='car-link')

		if not car_links:
			self.error("No cars were found in the profile page!")

		for car_link in car_links:
			try:
				self.__reservation_numbers.append(car_link.find('span', class_='notranslate').text.strip())
			except AttributeError:
				pass

		if self.__reservation_numbers:
			self.log.info(f"Found reservation numbers: {self.__reservation_numbers}")
		else:
			self.error("Could not find any reservation numbers on the profile page!")

	def scrub(self):
		self.get_csrf_token()
		self.log_in()
		self.find_reservation_numbers()

		email_body = ""
		subject = config['Email']['BORING_SUBJECT']
		force_email = False

		for rn in self.__reservation_numbers:
			if rn.lower()[0:2] != "rn":
				email_body += (f"Reservation number {rn} missing 'RN'\n")
				subject = config['Email']['EXCITING_SUBJECT']
				force_email = True
			else:
				email_body += (f"Reservation number {rn} is still boring.\n")


		send_email(to_email=self.email_to, body=email_body, subject=subject, force=force_email)


if __name__ == "__main__":
	setup_logging()

	log.info("Starting Tesla profile scrubber...")
	scrubber = ProfileScrubber(email_to=config['Email']['TO'],
							   tesla_username=config['Tesla']['USERNAME'],
							   tesla_password=config['Tesla']['PASSWORD'])
	try:
		scrubber.scrub()
	except ScrubbingError as error:
		send_email(to_email=config['Email']['TO'], body=error, subject='Something went wrong with Tesla profile scrubber',
				   force=True)
		log.debug("Error while scrubbing:", exc_info=error)

	log.info("Exiting Tesla profile scrubber...")