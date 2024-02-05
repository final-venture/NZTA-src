from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from win10toast import ToastNotifier
from twilio.rest import Client
from datetime import datetime
import os
import time
import json
import configparser

if os.name == "nt":
    from win10toast import ToastNotifier

config = configparser.ConfigParser()
config.read('./config.ini')

browser_options = Options()
browser_options.binary_location = "./Chromium/Application/chrome.exe"

def sleep_counter(total_time):
    for remaining_time in range(total_time, 0, -1):
        print(f"Next action in {remaining_time} seconds...", end='\r')
        time.sleep(1)

def limiter(func):
    last_call_time = 0

    def wrapper(*args, **kwargs):
        nonlocal last_call_time
        current_time = time.time()
        remaining_mins = (1200 - int(current_time - last_call_time)) // 60

        # Check if one hour has passed since the last call
        if current_time - last_call_time >= 1200:
            # Call the original function
            result = func(*args, **kwargs)

            # Update the last call time
            last_call_time = current_time

            return result
        else:
            print(f"A new text message can be sent in {remaining_mins}m.")

    return wrapper

@limiter
def send_notification_sms(msg):
    account_sid = config["Twilio"]["account_sid"]
    auth_token = config["Twilio"]["auth_token"]
    client = Client(account_sid, auth_token)

    message = client.messages.create(
    from_ = config["Twilio"]["phone_from"],
    body = msg,
    to = config["Twilio"]["phone_to"]
    )

def send_notification_mac(title, message):
    os.system("""
              osascript -e 'display notification "{}" with title "{}"'
              """.format(message, title))

def send_notification_windows(title, message):
    toaster = ToastNotifier()
    toaster.show_toast(title, message, duration=2.5)

def authenticate():
    # Load Auth Page
    url = "https://online.nzta.govt.nz/licence-test/identification"
    driver.get(url)

    # Send Info
    number = driver.find_element(By.XPATH, '/html/body/div[1]/app-root/block-ui/div/app-identification/div/div/form/div[1]/extended-input[1]/div/div/input')
    number.send_keys(config["Licence"]["number"])

    version = driver.find_element(By.XPATH, '/html/body/div[1]/app-root/block-ui/div/app-identification/div/div/form/div[1]/extended-input[2]/div/div/input')
    version.send_keys(config["Licence"]["version"])

    lastName = driver.find_element(By.XPATH, '//html/body/div[1]/app-root/block-ui/div/app-identification/div/div/form/div[1]/extended-input[3]/div/div/input')
    lastName.send_keys(config["Licence"]["lastName"])

    dob = driver.find_element(By.XPATH, '/html/body/div[1]/app-root/block-ui/div/app-identification/div/div/form/div[1]/extended-input[4]/div/div/input')
    dob.send_keys(config["Licence"]["dob"])

    while not EC.url_changes("https://online.nzta.govt.nz/licence-test/identification")(driver):
            dob.send_keys(Keys.RETURN)
            time.sleep(5)
            if EC.url_changes("https://online.nzta.govt.nz/licence-test/identification")(driver):
                print("Authentication completed! \n")
            else:
                print("Authentication failed. Retrying...")

def getAvailability():
    date_from = datetime.now().strftime("%d/%m/%Y")
    timeslots = []

    for site, id in config["Sites"].items():
        # Load Site Availability
        url = f"https://online.nzta.govt.nz/api/licence-test/slots/availability/Class1R?siteId={id}&dateFrom={date_from}&dateTo={config['Scanner']['date_to']}"
        driver.get(url)

        # Process Information and Print to Console
        available_dates = []
        raw_available_times = driver.find_element(By.XPATH, '/html/body/pre').text
        available_times = json.loads(raw_available_times)

        for slot in available_times["slotAvailability"]:
            date_object = datetime.strptime(slot["slotDate"][:10], "%Y-%m-%d")
            formatted_date = date_object.strftime("%d-%m-%Y")
            available_dates.append(formatted_date)

        availability = f"{site}: {available_dates}"

        if available_dates:
            timeslots.append(availability)
            print(availability)
            if os.name == "nt":
                send_notification_windows("Timeslot(s) Found!", availability)
            elif os.name == "posix":
                send_notification_mac("Timeslot(s) Found!", availability)
        else:
            print(f"No available timeslots from {date_from} to {config['Scanner']['date_to']} for {site}.")
    
    if timeslots:
        msg = f"Timeslots found! {timeslots}"
        send_notification_sms(msg)
    
    print("")

# Program
user_input = input("Would you like the browser to run in headless mode? (Y/N) ").lower()
if not user_input or user_input == "y":
    browser_options.add_argument("--headless")

driver = webdriver.Chrome(options=browser_options)
driver.implicitly_wait(10)

authenticate()
while True:
    try:
        getAvailability()
    except:
        authenticate()

    sleep_counter(5)
        