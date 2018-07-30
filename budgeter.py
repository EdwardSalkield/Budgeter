import urwid
from os import walk
import os
import userClass
import browser
import sys
from datetime import datetime
import copy
import collections

USERDATA = "./userdata/"
OPTIONSEXTENSION = ".json"
DATAEXTENSION = ".csv"

fb = browser.FileBrowser(os.getcwd())


def titlebar():
    txt = urwid.Text("Budgeter v0.2          © Edward Salkield 2018")
    return urwid.Pile([txt, urwid.Divider()])

def menu_button(caption, callback, user_data=None):
    button = urwid.Button(caption)
    urwid.connect_signal(button, 'click', callback, user_data)
    return urwid.AttrMap(button, None, focus_map='reversed')

def back_button():
    def go_back(button):
        return top.go_back()
    return menu_button(u'Back', go_back)

def exit_button():
    def go_back(button):
        return top.go_back()
    return menu_button(u'Exit', exit_program)

# Takes a function or urwid object contents which returns/is the menu
def general_sub_menu(caption, contents):
    def open_menu(button):
        return top.open_box(contents)
    return menu_button([caption, u'...'], open_menu)


def sub_menu(caption, choices):
    choices += [back_button()]
    contents = menu(caption, choices)
    return general_sub_menu(caption, contents)

def menu(title, choices):
    body = [urwid.Text(title)]
    body.extend(choices)
    return urwid.ListBox(urwid.SimpleFocusListWalker(body))

def item_chosen(button):
    response = urwid.Text([u'You chose ', button.label, u'\n'])
    done = menu_button(u'Ok', exit_program)
    top.open_box(urwid.Filler(urwid.Pile([response, done])))

def exit_program(button=None):
    raise urwid.ExitMainLoop()

def switchuser(button, username):
    user.switchUser(username) 
    top.go_back()


def newuser(button):
    def registercallback(button):
        menu = top.original_widget.body
        register(menu[0].edit_text, menu[1].edit_text)

    response = urwid.ListBox(urwid.SimpleFocusListWalker([
        urwid.Edit("Username: "),
        urwid.Edit("Password (Currently unused): "),
        urwid.Divider(),
        menu_button("Register", registercallback),
        back_button()
    ]))
    top.open_box(response)
    

def register(username, password):
    if user.registerUser(username):
        user.switchUser(username)
        top.back_to_top()

def msgbox(header, msg, button):
    box = urwid.LineBox(
            urwid.Filler(
                urwid.Pile([
                    urwid.Text(header),
                    urwid.Divider(),
                    urwid.Text(msg),
                    urwid.Divider(),
                    button()
                ]),
                'top'
            )
        )
    return box

# UI Tests

def testmsgbox(header, msg):
    def displaymsgbox(button):
        nonlocal header
        nonlocal msg
        top.msgbox(header, msg)
    return menu_button('msgbox', displaymsgbox)

def testerrormsg(msg):
    def displayerrormsg(button):
        nonlocal msg
        top.errormsg(msg)
    return menu_button('errormsg', displayerrormsg)

def testfatalerrormsg(msg):
    def displayfatalerrormsg(button):
        nonlocal msg
        top.fatalerrormsg(msg)
    return menu_button('fatalerrormsg', displayfatalerrormsg)


# Recalled every time the menu is opened
def gen_user_menu(button=None):
    userbuttons = list(map(lambda user: menu_button(user, switchuser, user), user.get_user_list()))

    user_menu = menu(u'New/Change User', [
            menu_button(u'New User', newuser),
        ] + userbuttons + [back_button()])
    return user_menu

def addData(dir_file):

    account_dict = {}
    transaction_dict = {}

    def change_account_data(edit, text, accname):
        account_dict[accname] = text

    def change_transaction_data(edit, text, trname):
        transaction_dict[trname] = text
    # Finished gathering user data
    def confirmed_data(button):
        def callback():
            top.go_back()
        user.set_uncat_data(dir_file, account_dict, transaction_dict)
        top.wait_for_dialogues(callback)

    def render():
        edit_accounts = []
        edit_transactions = []

        for acc in accounts:
            accedit = urwid.Edit(acc + ": ")
            urwid.connect_signal(accedit, 'change', change_account_data, acc)
            edit_accounts.append(accedit)

        for tr in transactions:
            tredit = urwid.Edit(tr + ": ")
            urwid.connect_signal(tredit, 'change', change_transaction_data, tr)
            edit_transactions.append(tredit)


        if edit_accounts != []:
            edit_accounts.insert(0, urwid.Text(account_text))
        else:
            edit_accounts = [urwid.Text("No new accounts detected")]

        if edit_transactions != []:
            edit_transactions.insert(0, urwid.Text(transactions_text))
        else:
            edit_transactions = [urwid.Text("No new transaction types detected")]

        menu = urwid.ListBox(urwid.SimpleFocusListWalker(
            [urwid.Pile(edit_accounts)] + [urwid.Divider()] +
            [urwid.Pile(edit_transactions)] + [urwid.Divider()] +
            [
                menu_button("Save", confirmed_data),
                back_button()
            ]))

        top.open_box(menu)

    account_text = "Please enter aliases for the following unrecognised accounts (leave blank for no alias):"
    transactions_text = "Please enter the category for the following unrecognised transaction descriptions:"

    (accounts, transactions) = user.get_uncat_data(dir_file)
    top.wait_for_dialogues(render)

        # Go straing through and add the new data

# Returns a file browser urwid object
def file_browser(freturn):
    def refresh():
        top.go_back()
        top.open_box(file_browser(freturn))

    def up(button):
        fb.up()
        refresh()

    # User has selected directory dirname
    def cd(button, dirname):
        fb.cd(dirname)
        refresh()

    # User has selected file fname
    def select(button, fname):
        top.go_back()
        freturn(fb.pwd() + fname)

    (dirnames, filenames) = fb.ls()
    relevantnames = list(filter(lambda x: DATAEXTENSION in x, filenames))
    othernames = list(set(filenames) - set(relevantnames))

    relevantbuttons = list(map(lambda x: menu_button(x, select, x), relevantnames))
    filebuttons = list(map(lambda x: menu_button(x, select, x), othernames))
    dirbuttons = list(map(lambda x: menu_button(x, cd, x), dirnames))


    menu = urwid.ListBox(urwid.SimpleFocusListWalker([
            urwid.Text("Please select the .cvs file to import"),
            urwid.Divider(),
            menu_button("..", up)
        ] + relevantbuttons + [urwid.Divider()] + dirbuttons + [urwid.Divider()] + filebuttons + [
            urwid.Divider(),
            back_button()
        ]))

    return menu


def get_balances():
    balances = {}
    for no, name in user.options['accounts'].items():
        balances[name + " (" + no + ")"] = user.getBalance(no, datetime.now())
    return balances

def gen_balances():
    items = []
    for k, v in get_balances().items():
        items.append(urwid.Text(k + ": " + user.options['currency'] + str(v)))

    text = urwid.Text("Account breakdown:")

    return urwid.Pile([text] + items)
        






def gen_budget_viewer():
    edit_from = urwid.Edit("From:  ", bviewer.from_date)
    edit_until = urwid.Edit("Until: ", bviewer.until_date)
    

    def search(button):
        #try:
        try:
            from_date = datetime.strptime(bviewer.from_date, user.options['dateformat'])
            until_date = datetime.strptime(bviewer.until_date, user.options['dateformat'])
        except Exception:
            top.errormsg("Invalid date format. Should be: " + user.options['dateformat'] + ". This can be changed in the \"Options\" menu.")

        #except Exception:
        budget = user.getBudgetBreakdown(from_date, until_date, bviewer.selected_categories, bviewer.selected_accounts)
        def keyf(x):
            (k, v) = x
            return v

        orderedbudget = collections.OrderedDict(sorted(budget.items(), key=keyf, reverse=True))

        # Display budget breakdown
        breakdown = []
        for cat, x in orderedbudget.items():
            breakdown.append(urwid.Text(cat + ": " + str(x)))

        bviewer.breakdown = breakdown

        top.refresh_current_menu()

            
        
    # (No., name) pairs
    account_select = []
    account_select.append(urwid.Text("Accounts:"))
    for no, name in user.options['accounts'].items():
        state = no in bviewer.selected_accounts
        account_select.append(urwid.CheckBox(name + " (" + no + ")", state=state, on_state_change=bviewer.change_account, user_data=no))

    category_select = []
    category_select.append(urwid.Text("Categories:"))
    for cat in sorted(user.options["categories"]):
        state = cat in bviewer.selected_categories
        category_select.append(urwid.CheckBox(cat, state=state, on_state_change=bviewer.change_category, user_data=cat))

    def update_text(edit, text, which):
        if which == "from":
            from_text = text
            top.msgbox("from", bviewer.from_date)
        elif which == "until":
            until_text = text
            top.msgbox("until", bviewer.until_date)


    urwid.connect_signal(edit_from, 'change', update_text, "from")
    urwid.connect_signal(edit_from, 'change', update_text, "until")

    return urwid.ListBox(urwid.SimpleFocusListWalker(account_select + [urwid.Divider()] + category_select + \
        [
            urwid.Divider(),
            edit_from,
            edit_until,
            urwid.Divider(),
            menu_button("Go!", search),
            urwid.Divider(),
            urwid.Text("Breakdown:")
        ] + bviewer.breakdown + \
        [
            urwid.Divider(),
            back_button()
        ]
    ))


    


def gen_main_menu(button=None):
    if not user.user_loaded:
        username = "new user"
    else:
        username = user.options["username"]

    welcomemessage = "Welcome " + username + "!"

    menu_top = menu(u'Main Menu', [
        urwid.Text(welcomemessage),
        urwid.Divider(),
        gen_balances(),
        urwid.Divider(),
        general_sub_menu(u'New/Change User', gen_user_menu),
        general_sub_menu(u'Import New Data', file_browser(addData)),
        general_sub_menu(u'View Budgets', gen_budget_viewer),
        sub_menu(u'Options', [
            menu_button(u'Change Default Currency', item_chosen),
            menu_button(u'Change Default User', item_chosen)
        ]),
        sub_menu(u'Manage categories', []),
        sub_menu(u'UI Test', [
            testmsgbox("Header", "message"),
            testerrormsg("Error message"),
            testfatalerrormsg("Fatal error message")
        ]),
        menu_button(u'Exit', exit_program)
    ])
    return menu_top




class PaneSelector(urwid.WidgetPlaceholder):
    stack = []
    current_refresh_callback = None# The callback to refresh the currently displayed menu. None if not generated by function


    dialogues = 0 # The number of currently open dialogue boxes
    max_dialogues = 5
    waiting = []    # Queue of waiting processes for dialogues to be dismissed


    def __init__(self, box):
        super(PaneSelector, self).__init__(urwid.SolidFill(u'/'))
        self.box_level = 0
        self.change_window(box)

    def change_window(self, box):
        if callable(box):
            self.current_refresh_callback = box
            self.original_widget = box()
        else:
            self.current_refresh_callback = None
            self.original_widget = box

    def open_box(self, box):
        # Save old screen
        if callable(self.current_refresh_callback):
            self.stack += [self.current_refresh_callback]
        else:
            self.stack += [self.original_widget]

        self.box_level += 1
        # Display new screen
        self.change_window(box)

    def refresh_current_menu(self):
        if callable(self.current_refresh_callback):
            self.original_widget = self.current_refresh_callback()


    def msgbox(self, header, msg):
        message = urwid.Overlay(
            msgbox(header, msg, back_button),
            self.original_widget,
            align='center', width=('relative', 50),
            valign='middle', height=('relative', 50),
            min_width=24, min_height=8,
            left = self.dialogues * 3,
            right = (self.max_dialogues - self.dialogues - 1) * 3,
            top = self.dialogues * 2,
            bottom = (self.max_dialogues - self.dialogues - 1) * 2
            )
        self.dialogues += 1
        self.open_box(message)

    def errormsg(self, msg):
        self.msgbox("Error", msg)

    def fatalerrormsg(self, msg):
        def quit():
            sys.exit(1)
        self.msgbox("Fatal Error!", msg)
        
        self.wait_for_dialogues(quit)

    def keypress(self, size, key):
        if key == 'esc':
            self.go_back()
        else:
            return super(PaneSelector, self).keypress(size, key)

    def wait_for_dialogues(self, callback):
        if self.dialogues == 0:
            callback()
        else:
            self.waiting += [callback]

    def returncallbacks(self):
        if self.waiting != []:
            for callback in self.waiting:
                callback()
    
    def go_back(self):
        if self.box_level == 0:
            exit_program()

        box = self.stack[-1]
        self.stack = self.stack[:-1]
        self.box_level -= 1

        self.change_window(box)

        if self.dialogues > 0:
            self.dialogues -= 1
            if self.dialogues == 0:
                self.returncallbacks()


    def back_to_top(self):
        self.box_level = 0
        box = self.stack[0]
        self.stack = []
        self.dialogues = 0
        self.change_window(box)


user = userClass.User(USERDATA, OPTIONSEXTENSION, DATAEXTENSION)       # Currently active user
user.load_default()



class BudgetBrowser():
    breakdown = [urwid.Text("[Blank - select 'Go!' to search]")]
    selected_accounts = copy.deepcopy(user.options['accounts']).keys()
    selected_categories = user.options['categories']
    until_date = datetime.strftime(datetime.now(), user.options['dateformat'])
    from_date = datetime.strftime(datetime.strptime("01/01/1970", "%d/%m/%Y"), "%d/%m/%Y")

    def reset(self):
        selected_accounts = []
        selected_categories = []


    def change_account(self, checkbox, state, no):
        if state:
            self.selected_accounts.append(no)
        else:
            self.selected_accounts.remove(no)
        

    def change_category(self, checkbox, state, cat):
        if state:
            self.selected_categories.append(cat)
        else:
            self.selected_categories.remove(cat)
        





bviewer = BudgetBrowser()

top = PaneSelector(gen_main_menu)
ui = urwid.Frame(top, header=titlebar())

user.setup_message_system(top.msgbox, top.errormsg, top.fatalerrormsg)
# Load the default user if one exists


urwid.MainLoop(ui, palette=[('reversed', 'standout', '')]).run()
