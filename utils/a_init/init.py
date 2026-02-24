import os
import datetime
import time
import random

# this function is used to initialize the project, it will create the necessary folders and files for the project to run

def init ():

    # Wait between 1 and 10 minutes before starting
    #time.sleep(random.randint(60, 600))

    date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"folder at {date}...")
    # create the necessary folder for the project inside the outputs folder
    if not os.path.exists("outputs"):
        os.mkdir("outputs")
    if not os.path.exists(f"outputs/data[{date}]"):
        os.mkdir(f"outputs/data[{date}]")
    if not os.path.exists(f"outputs/data[{date}/pdf]"):
        os.mkdir(f"outputs/data[{date}]/pdf")

    return date
