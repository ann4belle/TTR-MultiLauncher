"""Functions to update TTR, then allow the user to login to an account and launch the game."""
import tkinter as tk
from tkinter import filedialog
import json
import os
import time
import requests
import updater

class TTRLauncher(tk.Frame):
    """Main class for the TTR MultiLauncher"""
    def __init__(self, master=None):
        while not os.path.exists('installdir.txt'):
            installdir = filedialog.askdirectory(title='Select TTR Install Directory')
            if installdir is None:
                print('Please provide the installation directory.')
                continue
            with open('installdir.txt', 'a+') as file:
                file.write(installdir)
        with open('installdir.txt', 'r') as file:
            updater.TTRUpdater(file.read())
        super().__init__(master)
        self.master = master
        self.master.minsize(200, 200)
        self.create_widgets()
        self.pack(expand=True)
        self.load_accts()

    def create_widgets(self):
        self.toonlist = tk.Listbox(self)
        self.login_b = tk.Button(self, text='Login', command=self.login)
        self.add_acct_b = tk.Button(self, text='Add Account', command=self.add_acct)
        self.toonlist.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.login_b.pack(side=tk.LEFT)
        self.add_acct_b.pack(side=tk.RIGHT)
        self.grid(padx=2, pady=(0, 2))

    def load_accts(self):
        self.accts = []
        with open('accounts.txt', 'a+') as accfile:
            accfile.seek(0)
            for line in accfile:
                line = line.split(',')
                if not len(line) == 3:
                    continue
                self.accts.append((line[0], line[1], line[2]))
        for acc in self.accts:
            self.toonlist.insert(tk.END, acc[0])

    def login(self):
        self.do_request({'username': self.accts[self.toonlist.curselection()[0]][1].strip(), 'password': self.accts[self.toonlist.curselection()[0]][2].strip()})

    def do_request(self, data):
        resp = json.loads(requests.post('https://www.toontownrewritten.com/api/login?format=json', data=data, headers={'Content-Type': 'application/x-www-form-urlencoded'}).content)
        success = resp.get('success', 'false')
        if success == 'true':
            os.environ['TTR_PLAYCOOKIE'] = resp.get('cookie', 'CookieNotFound')
            os.environ['TTR_GAMESERVER'] = resp.get('gameserver', 'ServerNotFound')
            with open('installdir.txt', 'r') as file:
                os.chdir(file.read())
            #Automated relogging if user requests?
            if os.path.exists('TTREngine.exe'):
                os.system('TTREngine.exe')
            elif os.path.exists('TTREngine'):
                os.system('./TTREngine')
            else:
                print('Platform not supported or TTREngine executable missing!')
        elif success == 'delayed':
            eta = int(resp.get('eta', 30))
            pos = resp.get('position', 'unknown')
            token = resp.get('queueToken', None)
            if token is None:
                print("No queue token was returned. This shouldn't be possible! There may be a problem with the TTR login API.")
                return
            print('Queue position: ' + pos + ' ETA: ' + repr(eta))
            time.sleep(min(eta, 30))
            self.do_request({'queueToken': token})
        elif success == 'partial':
            auth_token = resp.get('responseToken', None)
            if auth_token is None:
                print("A response token was not provided. This shouldn't be possible! There may be a problem with the TTR login API.")
                return
            tg_code = AuthRequestDialog(self).tg_code
            if tg_code is None:
                print("You need to provide a ToonGuard code to log in.")
                return
            self.do_request({'appToken': tg_code, 'authToken': auth_token})
        elif success == 'false':
            print(resp.get('banner', "Login failed without giving a reason. Check TTR status and try again."))

    def add_acct(self):
        dialog = AcctRequestDialog(self)
        print(dialog.label)
        if dialog.label is None:
            return
        self.accts.append((dialog.label, dialog.username, dialog.password))
        self.toonlist.insert(tk.END, dialog.label)
        self.toonlist.pack(side=tk.TOP, fill=tk.BOTH)
        with open('accounts.txt', 'a+') as accfile:
            accfile.write(dialog.label + ',' + dialog.username + ',' + dialog.password + '\n')

class AcctRequestDialog(tk.Toplevel):
    """Simple class to request account information"""
    def __init__(self, parent, title=None):
        tk.Toplevel.__init__(self, parent)
        if title:
            self.title(title)
        self.parent = parent
        self.result = None
        body = tk.Frame(self)
        self.initial_focus = self.body(body)
        body.pack(padx=5, pady=5)
        self.grab_set()
        self.label = None
        self.username = None
        self.password = None
        if not self.initial_focus:
            self.initial_focus = self
        self.protocol('WM_DELETE_WINDOW', self.cancel)
        self.geometry('+%d+%d' % (parent.winfo_rootx()+50, parent.winfo_rooty()+50))
        self.initial_focus.focus_set()
        self.wait_window(self)

    def body(self, master):
        tk.Label(master, text='Label:').grid(row=0)
        tk.Label(master, text='Username:').grid(row=1)
        tk.Label(master, text='Password:').grid(row=2)
        self.label_entry = tk.Entry(master)
        self.user_entry = tk.Entry(master)
        self.pass_entry = tk.Entry(master)
        self.label_entry.grid(row=0, column=1)
        self.user_entry.grid(row=1, column=1)
        self.pass_entry.grid(row=2, column=1)
        box = tk.Frame(self)
        tk.Button(box, text='OK', width=10, command=self.confirm, default=tk.ACTIVE).pack(side=tk.LEFT)
        tk.Button(box, text='Cancel', width=10, command=self.cancel).pack(side=tk.LEFT)
        box.pack(side=tk.BOTTOM, padx=5, pady=5)
        self.bind('<Return>', self.confirm)
        self.bind('<Escape>', self.cancel)
        return self.label_entry

    def confirm(self, event=None):
        if not self.validate():
            self.initial_focus.focus_set()
            return
        self.withdraw()
        self.update_idletasks()
        self.apply()
        self.cancel()

    def cancel(self, event=None):
        self.parent.focus_set()
        self.destroy()

    def validate(self):
        return 1

    def apply(self):
        self.label = self.label_entry.get()
        self.username = self.user_entry.get()
        self.password = self.pass_entry.get()

class AuthRequestDialog(tk.Toplevel):
    """Simple class to request ToonGuard auth code"""
    def __init__(self, parent, title=None):
        tk.Toplevel.__init__(self, parent)
        if title:
            self.title(title)
        self.parent = parent
        self.result = None
        body = tk.Frame(self)
        self.initial_focus = self.body(body)
        body.pack(padx=5, pady=5)
        self.grab_set()
        self.tg_code = None
        if not self.initial_focus:
            self.initial_focus = self
        self.protocol('WM_DELETE_WINDOW', self.cancel)
        self.geometry('+%d+%d' % (parent.winfo_rootx()+50, parent.winfo_rooty()+50))
        self.initial_focus.focus_set()
        self.wait_window(self)

    def body(self, master):
        tk.Label(master, text='ToonGuard Code:').grid(row=0)
        self.tg_entry = tk.Entry(master)
        self.tg_entry.grid(row=0, column=1)
        box = tk.Frame(self)
        tk.Button(box, text='OK', width=10, command=self.confirm, default=tk.ACTIVE).pack(side=tk.LEFT)
        tk.Button(box, text='Cancel', width=10, command=self.cancel).pack(side=tk.LEFT)
        box.pack(side=tk.BOTTOM, padx=5, pady=5)
        self.bind('<Return>', self.confirm)
        self.bind('<Escape>', self.cancel)
        return self.tg_entry

    def confirm(self, event=None):
        if not self.validate():
            self.initial_focus.focus_set()
            return
        self.withdraw()
        self.update_idletasks()
        self.apply()
        self.cancel()

    def cancel(self, event=None):
        self.parent.focus_set()
        self.destroy()

    def validate(self):
        return 1

    def apply(self):
        self.tg_code = self.tg_entry.get()

if __name__ == '__main__':
    ROOT = tk.Tk()
    APP = TTRLauncher(master=ROOT)
    APP.mainloop()
