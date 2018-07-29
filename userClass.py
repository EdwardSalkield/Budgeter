import curses
import csv
import os.path
import sys
import operator
from tempfile import NamedTemporaryFile
import shutil
from itertools import tee
import json
from datetime import datetime
import time
import textwrap
import math
import os
import copy

debugmode = True

def fatalerror(msg):
    sys.exit(msg)

def alert(msg):
    print(msg)

def errormsg(msg):
    print(msg)

def debug(msg):
    if debugmode:
        print(msg)

# Categorises the data in newfile. and adds 
class User:
    default_options = {
        'accounts': {},
        'dupratio': 0.2,
        'fields': ['Transaction Date', 'Transaction Type', 'Sort Code', 'Account Number', 'Transaction Description', 'Debit Amount', 'Credit Amount', 'Balance', 'Category'],
        'currency': '£',
        'dateformat': '%d/%m/%Y',
        'username': ''
    }

    options = copy.deepcopy(default_options)

    MAINCONFIGLOCATION = "main.config"
    USERDATA = None
    OPTIONSEXTENSION = None
    DATAEXTENSION = None

    csvlocation = None
    optionslocation = None

    mainprint = None
    maininput = None

    default_user_set = False
    user_loaded = False

    def setup_message_system(self, msgbox, error, fatalerror):
        self.msgbox = msgbox
        self.errormsg = error
        self.fatalerrormsg = fatalerror

    def __init__(self, userdatapath, optionsextension, dataextension):
        self.USERDATA = userdatapath
        self.OPTIONSEXTENSION = optionsextension
        self.DATAEXTENSION = dataextension



        # Race condition if userdatapath is created between os.path.exists and os.makedirs
        if not os.path.exists(self.USERDATA):
            os.makedirs(self.USERDATA)

        # Find whether a default user exists
        main_options_location = self.USERDATA + self.MAINCONFIGLOCATION
        self.default_user_set = os.path.isfile(main_options_location)

    def load_default(self):
        main_options_location = self.USERDATA + self.MAINCONFIGLOCATION
        # Load default user
        if self.default_user_set:
            with open(main_options_location, 'r') as optionsfile:
                # Assumes the config file is well formatted TODO
                globaloptions = json.loads(optionsfile.read())
                self.switchUser(globaloptions["default_name"])
            return True

        else:
            return False
        
    def saveDefaultOptions(self, username):
        optionslocation = self.USERDATA + username + self.OPTIONSEXTENSION

        with open(optionslocation, 'w', newline='') as optionsfile:
            options = copy.deepcopy(self.default_options)
            options['username'] = username
            options_str = json.dumps(options)
            optionsfile.write(options_str)

    def saveOptions(self, username=None):
        if username == None:
            username = self.options['username']

        optionslocation = self.USERDATA + username + self.OPTIONSEXTENSION

        with open(optionslocation, 'w', newline='') as optionsfile:
            options = json.dumps(self.options)
            optionsfile.write(options)

        

    # Manipulating user accounts
    def get_user_list(self):
        f = []
        for (dirpath, dirnames, filenames) in os.walk(self.USERDATA):
            f.extend(filenames)
            break

        userloclist = list(filter(lambda x: self.OPTIONSEXTENSION in x, f))
        users = list(map(lambda user: user.replace(self.OPTIONSEXTENSION, ''), userloclist))

        return users

    def userExists(self, username):
        f = self.get_user_list()
        return username in f

    def set_default_user(self, username):
        main_options_location = self.USERDATA + self.MAINCONFIGLOCATION
        main_options = {
            "default_name": username
        }
        main_options_str = json.dumps(main_options)

        # Find the name of the default user
        with open(main_options_location, 'w') as optionsfile:
            # Assumes the config file is well formatted TODO
            optionsfile.write(main_options_str)

        self.default_user_set = True

    def registerUser(self, username):
        main_options_location = self.USERDATA + self.MAINCONFIGLOCATION
        csvlocation = self.USERDATA + username + self.DATAEXTENSION
        optionslocation = self.USERDATA + username + self.OPTIONSEXTENSION

        if self.userExists(username):
            self.msgbox("Duplicate user", "User " + username + " already exists!")
            return False

        # Register a new user
        if not os.path.isfile(csvlocation):
            self.msgbox("Alert", "No user csv file detected. Creating " + csvlocation + "...")

            with open(csvlocation, 'w+') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=self.options['fields'])
                row = {}
                for field in self.options['fields']:
                    row[field] = field
                writer.writerow(row)

        if not os.path.isfile(optionslocation):
            self.msgbox("Alert", "No main optionslocation file detected. Creating " + optionslocation + "...")
            self.saveDefaultOptions(username)

        # If first user, write them as default
        if not self.default_user_set:
            self.set_default_user(username)
        return True


    def switchUser(self, username):
        self.user_loaded = True
        csvlocation = self.USERDATA + username + self.DATAEXTENSION
        optionslocation = self.USERDATA + username + self.OPTIONSEXTENSION

        if self.userExists(username):
            self.csvlocation = csvlocation
            self.optionslocation = csvlocation

            with open(optionslocation, 'r', newline='') as optionsfile:
                self.options = json.loads(optionsfile.read())

            return True

        else:
            self.errormsg("Cannot switch user - " + username + " does not exist!")
            return False
        
    # Returns unrecognised accounts and transactions
    def get_uncat_data(self, newcsvlocation):
        new_accounts = []
        new_transactions = []

        if not os.path.isfile(newcsvlocation):
            self.errormsg("No .csv file found at " + newfile + ".")
            return None

        with open(newcsvlocation, 'r', newline='') as newcsvfile:
            newreader = csv.DictReader(newcsvfile, fieldnames=self.options['fields'])
            next(newreader) # Skip the fields
                
            with open(self.csvlocation, 'r') as csvfile:
                reader = csv.DictReader(csvfile, fieldnames=self.options['fields'])

                # Get list from main spreadsheet without categories
                mainreaderlistnocat = []
                for row in reader:
                    newrow = dict(row)
                    newrow.pop('Category', None)
                    mainreaderlistnocat.append(newrow)

                duprows = []
                for row in newreader:
                    rownocat = dict(row)
                    rownocat.pop('Category', None)
                    accno = row['Account Number']

                    if rownocat in mainreaderlistnocat:
                        debug("Duplicate row")
                        duprows.append(row)
                    else:
                        new_transactions.append(row)

                    if accno not in self.options['accounts'].keys():
                        new_accounts.append(accno)


                ratio = len(duprows)/(len(new_transactions) + len(duprows)) 
                if ratio >= self.options['dupratio']:
                    self.msgbox("WARNING!", "This .csv file appears to be a duplicate of a previously merged change. Proceed with caution.")

        new_accounts = list(set(new_accounts))
        new_transactions = list(set(map(lambda x: x['Transaction Description'], new_transactions)))

        return (new_accounts, new_transactions)


        
    def set_uncat_data(self, newcsvlocation, account_dict, transaction_dict):
        if not os.path.isfile(newcsvlocation):
            self.errormsg("No .csv file found at " + newfile + ".")

        tempfile = NamedTemporaryFile(mode='w', delete=False)

        with open(newcsvlocation, newline='') as newcsvfile:
            newreader = csv.DictReader(newcsvfile, fieldnames=self.options['fields'])
            next(newreader) #Skip the header line

            with open(self.csvlocation, 'r') as csvfile, tempfile:
                reader = csv.DictReader(csvfile, fieldnames=self.options['fields'])
                writer = csv.DictWriter(tempfile, fieldnames=self.options['fields'])
                
                mainreaderlistnocat = []
                for row in reader:
                    newrow = dict(row)
                    newrow.pop('Category', None)
                    mainreaderlistnocat.append(newrow)
                    writer.writerow(row)

                
                rows = []
                duprows = []
                for row in newreader:
                    rownocat = dict(row)
                    rownocat.pop('Category', None)
                    accno = row['Account Number']
                    if rownocat in mainreaderlistnocat:
                        debug("Duplicate row")
                        duprows.append(row)
                    else:
                        rows.append(row)

                    if accno not in self.options['accounts'].keys():
                        self.options['accounts'][accno] = account_dict[accno]
                        self.saveOptions()

                for row in duprows:
                    writer.writerow(row)
                
                for row in rows:
                    writer.writerow(row)
                    
            self.msgbox("Alert", "Writing changes...")
            shutil.move(tempfile.name, self.csvlocation)




    # Attempts to find the category of the transaction described by transdescription and transtype
    # Guessesby  mode
    def categorylookup(self, reader, transdescription, transtype):
        cats = []
        for row in reader:
            if row['Transaction Description'] == transdescription and row['Transaction Type'] == transtype:
                if row['Category'] != '':
                    cats.append(row['Category'])

        if cats != []:
            mode = max(set(cats), key=cats.count)

        if cats == [] or mode == '':
            return maininput("What is the category of:" + transdescription + ", " + transtype + "? ")
        else:
            # Return the most probable category
            return mode


    # Categorises data in the main spreadsheet
    def categorise(self):
        tempfile = NamedTemporaryFile(mode='w', delete=False)

        self.options['fields'] = ['Transaction Date', 'Transaction Type', 'Sort Code', 'Account Number', 'Transaction Description', 'Debit Amount', 'Credit Amount', 'Balance', 'Category']

        with open(self.csvlocation, 'r') as csvfile, tempfile:
            reader0 = csv.DictReader(csvfile, fieldnames=self.options['fields'])
            reader0, reader = tee(reader0)
            writer = csv.DictWriter(tempfile, fieldnames=self.options['fields'])
            for row in reader:
                if row['Category'] == '':
                    reader0, categoryreader = tee(reader0)
                    tdesc = row['Transaction Description']
                    ttype = row['Transaction Type']

                    category = self.categorylookup(categoryreader, tdesc, ttype)
                    row['Category'] = category
                writer.writerow(row)

        shutil.move(tempfile.name, self.csvlocation)


    # Functions to search through spreadsheet data
    # Returnss all rows from main.csv that satisfy filterrow
    def getRows(self, filterrow):
        rows = []
        with open(self.csvlocation, 'r') as csvfile:
            reader = csv.DictReader(csvfile, fieldnames=self.options['fields'])
            for row in reader:
                if filterrow(row):
                    rows.append(row)

        return rows

    # Returns the row immediately before a given time
    def getRowAtTime(self, accno, time):
        try:
            date = datetime.strptime(time, self.options['dateformat'])
        except Exception:
            self.errormsg("Invalid date")
            return

        upDate = datetime(1970, 1, 1)

        def timefilter(row):
            nonlocal upDate
            try:
                rowdate = datetime.strptime(row['Transaction Date'], self.options['dateformat'])
            except Exception:
                return False

            if row['Account Number'] == accno and rowdate >= upDate and rowdate <= date:
                upDate = rowdate
                return True
            else:
                return False
            
        rows = self.getRows(timefilter)
        
        if rows == []:
            return None
        else:
            return rows[-1]

    def getBalance(self, accno, time):
        row = self.getRowAtTime(accno, time)
        if row == None:
            return None
        else:
            return row['Balance']

