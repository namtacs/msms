#!/usr/bin/env python3
import base64
import json
import os
import logging as log
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import subprocess
import shutil
import psutil
import requests
import threading
import PluginsAndModsManagement as pammanage

VERSION = 3
NAME = "MSMS"
CONFIG_NAME = "config.json"
DEFAULT_CONFIG = {"servers": {}, "version": VERSION}


class ServerCreateHelper(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Create server")
        nameEntry = tk.Entry(self)
        nameEntry.grid(column=0, row=0)
        typeComboBox = ttk.Combobox(self, values=("BungeeCord", "Forge", "Spigot", "Paper", "Official"))
        typeComboBox.current(2)
        typeComboBox.grid(column=1, row=0)
        lbl = tk.Label(self, text="Version:", padx=5)
        lbl.grid(column=2, row=0)
        versionEntry = tk.Entry(self, width=5)
        versionEntry.grid(column=3, row=0)
        btn = tk.Button(self, text="Create",
                        command=lambda: self.create(nameEntry.get(), typeComboBox.get(), versionEntry.get()))
        btn.grid(column=0, row=1)
        self.mainloop()

    def create(self, name, type, version):
        log.debug("Create called with parameters: " + name + ", " + type + ", " + version)
        serverDir = os.path.join("servers", name)
        os.mkdir(serverDir)
        if type == "Forge":
            cmd = ["java", "-jar", os.path.join("serverfiles", "forge" + version + ".jar"), "--installServer",
                   serverDir]
            log.info("The installation log will be written to the installer.log file")
            log.info(cmd)
            cfg["servers"][name] = {"type": type.lower(), "version": version, "dir": serverDir, "gui": True,
                                    "state": "Inactive"}
            thread = threading.Thread(target=self.creating_thread, args=(name, cmd))
            thread.start()
        elif type == "Spigot":
            latest_build = json.loads(requests.get("https://hub.spigotmc.org/jenkins/job/BuildTools/lastSuccessfulBuild/api/json").text)["number"]
            log.debug("Latest BuildTools build is " + str(latest_build))
            installed = [int(i[11:][:-4]) for i in os.listdir("serverfiles") if i[:10] == "BuildTools"]
            log.debug("BuildTools installed versions: " + " ".join(str(i) for i in installed))
            latest_installed_build = sorted(installed + [0], reverse=True)[0]
            if latest_installed_build < latest_build:
                log.info("Updating BuildTools version from " + str(latest_installed_build) + " to " + str(latest_build))
                data = requests.get("https://hub.spigotmc.org/jenkins/job/BuildTools/lastSuccessfulBuild/artifact/target/BuildTools.jar").content
                with open(os.path.join("serverfiles", "BuildTools-" + str(latest_build) + ".jar"), "wb") as f:
                    f.write(data)
            cmd = ["java", "-jar", os.path.join("serverfiles", "BuildTools-" + str(latest_build) + ".jar"), "-o", serverDir, "--rev", version]
            log.info("The installation log will be written to the BuildTools.log.txt file")
            log.info(cmd)
            cfg["servers"][name] = {"type": type.lower(), "version": version, "dir": serverDir, "gui": True,
                                    "state": "Inactive"}
            thread = threading.Thread(target=self.creating_thread, args=(name, cmd))
            thread.start()
        elif type == "Paper":
            jarfile = os.path.join("serverfiles", "paper-" + version + ".jar")
            if os.path.isfile(jarfile):
                log.info("Found cached paper " + version)
            else:
                latest_build = str(
                    json.loads(requests.get("https://papermc.io/api/v2/projects/paper/versions/" + version).text)[
                        "builds"][-1])
                log.info("Latest build is " + latest_build)
                log.info("Downloading")
                with open(jarfile, "wb") as f:
                    f.write(requests.get(
                        "https://papermc.io/api/v2/projects/paper/versions/" + version + "/builds/" + latest_build + "/downloads/paper-" + version
                        + "-" + latest_build + ".jar").content)
            shutil.copy(jarfile, serverDir)
            cfg["servers"][name] = {"type": type.lower(), "version": version, "dir": serverDir, "gui": True,
                                    "state": "normal"}
        with open(os.path.join(serverDir, "eula.txt"), "w") as f:
            f.write("eula=true")
        config_update()
        window.refresh_servers_list()
    def creating_thread(self, name, cmd):
        execute(cmd)
        log.info("Server " + name + " is completely ready")
        cfg["servers"][name]["state"] = "normal"
        config_update()


class ServerPropertiesEditor(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Server properties editor")
        self.btn_save = tk.Button(self, text="Save", bg="#00d2d2", activebackground="LightGoldenrodYellow",
                                  command=self.save)
        self.btn_save.grid(column=0, row=0)
        self.file = os.path.join("servers", window.servers_list.item(window.servers_list.selection()[0])["values"][0],
                                 "server.properties")
        self.ccodes = [
            (r"\u00a74", "&dark_red"),
            (r"\u00a7c", "&red"),
            (r"\u00a76", "&gold"),
            (r"\u00a7e", "&yellow"),
            (r"\u00a72", "&dark_green"),
            (r"\u00a7a", "&green"),
            (r"\u00a7b", "&aqua"),
            (r"\u00a73", "&dark_aqua"),
            (r"\u00a71", "&dark_blue"),
            (r"\u00a79", "&blue"),
            (r"\u00a7d", "&light_purple"),
            (r"\u00a75", "&dark_purple"),
            (r"\u00a7f", "&white"),
            (r"\u00a77", "&gray"),
            (r"\u00a78", "&dark_gray"),
            (r"\u00a70", "&black")]
        self.keys = []
        self.entrys = []
        with open(self.file, "r") as file:
            for line in file:
                if line[0] != "#":
                    key, value = line[:-1].split("=")
                    self.keys.append(key)
                    i = len(self.entrys) + 1
                    tk.Label(self, text=key).grid(column=0, row=i)
                    entry = tk.Entry(self, bg="#D3D3D3", bd=0)
                    if key == "motd":
                        value = json.loads('"' + value + '"')
                        value = self.replace_ccodes(value)
                    entry.insert(0, value)
                    entry.grid(column=1, row=i)
                    self.entrys.append(entry)
        self.mainloop()

    def replace_ccodes(self, text, reverse=False):
        for ccode in self.ccodes:
            if reverse:
                text = text.replace(ccode[1], ccode[0])
            else:
                text = text.replace(ccode[0], ccode[1])
        return text

    def save(self):
        with open(self.file, "w") as file:
            file.write("# Edited with " + NAME + "\n")
            for i in range(len(self.keys)):
                value = self.entrys[i].get()
                if self.keys[i] == "motd":
                    value = json.dumps(value)[1:-1]
                    value = self.replace_ccodes(value, True)
                file.write(self.keys[i] + "=" + value + "\n")

class App(tk.Tk):
    def __init__(self):
        pass

    def fixed_map(self, option):
        return [elm for elm in self.servers_list_style.map("Treeview", query_opt=option) if
                elm[:2] != ("!disabled", "!selected")]

    def gui(self):
        super().__init__()
        self.title(NAME)
        self.iconphoto(True, tk.PhotoImage(file='icon.png'))
        mainmenu = tk.Menu(self)
        servicemenu = tk.Menu(mainmenu)
        servicemenu.add_command(label="Delete unregistred servers", command=self.delete_unregistred_servers)
        mainmenu.add_cascade(label="Service", menu=servicemenu)
        self.config(menu=mainmenu)
        self.servers_list = ttk.Treeview(self, columns=("name", "type", "state"), show="headings")
        self.servers_list.heading('name', text='Server Name')
        self.servers_list.heading('type', text='Type')
        self.servers_list.heading('state', text='State')
        self.servers_list.grid(column=0, row=0)
        self.servers_list_style = ttk.Style()
        self.servers_list_style.map("Treeview", foreground=self.fixed_map("foreground"),
                                    background=self.fixed_map("background"))
        self.servers_list.tag_configure('running', background='#9dee9d')
        self.servers_list.tag_configure('stopped', background='#ee9d9d')
        self.servers_list.tag_configure('inactive', background='#D3D3D3')
        self.gui_var = tk.BooleanVar()
        self.chkbtn_gui = ttk.Checkbutton(self, text = "Gui", var = self.gui_var, command = self.chkbox_gui_change)
        self.chkbtn_gui.grid(column=1, row=0)
        self.btn_create = tk.Button(self, text="Create server", activebackground="LightGoldenrodYellow",
                                    command=ServerCreateHelper, bg = "#00d2d2")
        self.btn_create.grid(column=0, row=1)
        self.btn_props = tk.Button(self, text="Server properties", bg="#00d2d2",
                                   activebackground="LightGoldenrodYellow", command=ServerPropertiesEditor)
        self.btn_props.grid(column=1, row=1)
        self.btn_start = tk.Button(self, text="Start", bg="#00d2d2", activebackground="LightGoldenrodYellow",
                                   command=self.start_server)
        self.btn_start.grid(column=2, row=1)
        self.btn_stop = tk.Button(self, text="Stop", bg="#00d2d2", activebackground="LightGoldenrodYellow",
                                  command=self.stop_server)
        self.btn_stop.grid(column=3, row=1)
        self.btn_plugins = tk.Button(self, text="Plugins & mods", bg="#00d2d2", activebackground="LightGoldenrodYellow",
                                  command=self.open_plugins)
        self.btn_plugins.grid(column=4, row=1)
        self.btn_kill = tk.Button(self, text="Kill process", bg="#ca0000", activebackground="LightGoldenrodYellow",
                                  command=lambda: self.stop_server(True))
        self.btn_kill.grid(column=5, row=1)
        self.btn_del = tk.Button(self, text="Delete", bg="#00d2d2", activebackground="LightGoldenrodYellow",
                                 command=self.delete_server)
        self.btn_del.grid(column=1, row=2)
        self.refresh_servers_list_idle_task()
        self.bind('<<TreeviewSelect>>', self.servers_list_select)
        if cfg["version"] < VERSION:
            msg = "Config version({0}) less than {1} version({2})".format(str(cfg["version"]), NAME, str(VERSION))
            log.warning(msg)
            messagebox.showwarning("Version warning", msg)
            cfg["version"] = VERSION
            config_update()
        self.mainloop()

    def refresh_servers_list(self):
        log.debug("Refreshing servers list")
        for item in self.servers_list.get_children():
            self.servers_list.delete(item)
        if len(cfg["servers"]) > 0:
            for data in self.get_servers_state():
                self.servers_list.insert("", "end", values=(data["name"], data["data"]["type"], data["state"]), tags=(data["state"].lower(),))
            if self.btn_create["bg"] == "Yellow": self.btn_create.configure(bg = "#00d2d2")
        else:
            if self.btn_create["bg"] == "#00d2d2": self.btn_create.configure(bg = "Yellow")
        self.btn_del.configure(state = tk.DISABLED)
        self.btn_start.configure(state = tk.DISABLED)
        self.btn_stop.configure(state = tk.DISABLED)
        self.btn_kill.configure(state=tk.DISABLED)
        self.btn_props.configure(state = tk.DISABLED)
        self.btn_plugins.configure(state=tk.DISABLED)
        self.chkbtn_gui.configure(state = tk.DISABLED)

    def get_servers_state(self):
        running_sh = []
        running_java = []
        for pid in psutil.pids():
            try:
                p = psutil.Process(pid)
                name = p.name()
                if name == "sh":
                    running_sh.append(p.cmdline()[1])
                elif name == "java":
                    running_java.append(p.cmdline()[2])
            except:
                pass
        for server in cfg["servers"]:
            data = cfg["servers"][server]
            if data["type"] == "forge":
                runfile = "run.sh"
                running = running_sh
            elif data["type"] == "spigot":
                runfile = "spigot-" + data["version"] + ".jar"
                running = running_java
            elif data["type"] == "paper":
                runfile = "paper-" + data["version"] + ".jar"
                running = running_java
            else:
                runfile = ""
            if data["state"].startswith("run/text"):
                for run in data["state"][8:].split("run"): exec(run)
                state = "normal"
            elif data["state"].startswith("run/b64"):
                exec(base64.b64decode(data["state"][7:]))
                state = "normal"
            if data["state"] == "normal":
                if os.path.join(os.getcwd(), data["dir"], runfile) in running:
                    state = "Running"
                else:
                    state = "Stopped"
            else:
                state = data["state"]
            yield {"name": server, "data": data, "state": state, "runfile": runfile}

    def servers_list_select(self, event):
        self.btn_del.configure(state=tk.NORMAL)
        self.btn_start.configure(state=tk.NORMAL)
        self.btn_stop.configure(state=tk.NORMAL)
        self.btn_kill.configure(state=tk.NORMAL)
        self.btn_props.configure(state=tk.NORMAL)
        self.btn_plugins.configure(state=tk.NORMAL)
        self.chkbtn_gui.configure(state=tk.NORMAL)
        self.gui_var.set(cfg["servers"][self.servers_list.item(self.servers_list.selection()[0])["values"][0]]["gui"])

    def delete_server(self):
        for selected_item in self.servers_list.selection():
            name = self.servers_list.item(selected_item)["values"][0]
            try: shutil.rmtree(os.path.join("servers", name))
            except: pass
            del cfg["servers"][name]
            log.info("Server '" + name + "' deleted successfully")
        config_update()
        self.refresh_servers_list()

    def delete_unregistred_servers(self):
        for d in os.listdir("servers"):
            path = os.path.join("servers", d)
            if os.path.isdir(path):
                if not d in cfg["servers"]:
                    shutil.rmtree(path)
                    log.info("Server '" + d + "' deleted successfully")
                    messagebox.showinfo("Server deleted", "Server '" + d + "' deleted successfully")

    def start_server(self):
        for selected_item in self.servers_list.selection():
            name, type = self.servers_list.item(selected_item)["values"][0], \
                         self.servers_list.item(selected_item)["values"][1]
            data = cfg["servers"][name]
            serverDir = data["dir"]
            if serverDir.startswith("run/text"):
                for run in serverDir[8:].split("run"): exec(run)
            elif serverDir.startswith("run/b64"):
                exec(base64.b64decode(serverDir[7:]))
            else:
                cwd = os.path.join(os.getcwd(), serverDir)
                userargs = []
                if not data["gui"]: userargs.append("nogui")
                if type == "forge":
                    subprocess.Popen(['"' + os.path.join(cwd, "run.sh") + '"'] + userargs, cwd=cwd, shell=True,
                                     stdout=subprocess.DEVNULL, stdin=subprocess.DEVNULL)
                elif type == "spigot":
                    subprocess.Popen(
                        ["java", "-jar", os.path.join(cwd, "spigot-" + data["version"] + ".jar")] + userargs, cwd=cwd,
                        stdout=subprocess.DEVNULL, stdin=subprocess.DEVNULL)
                elif type == "paper":
                    subprocess.Popen(
                        ["java", "-jar", os.path.join(cwd, "paper-" + data["version"] + ".jar")] + userargs, cwd=cwd,
                        stdout=subprocess.DEVNULL, stdin=subprocess.DEVNULL)
                log.info("Server '" + name + "' started")
        self.refresh_servers_list()

    def stop_server(self, kill=False):
        running_java = []
        for pid in psutil.pids():
            try:
                p = psutil.Process(pid)
                if p.name() == "java":
                    running_java.append((pid, p.cwd(), p.cmdline()))
            except:
                pass
        for selected_item in self.servers_list.selection():
            name, type = self.servers_list.item(selected_item)["values"][0], \
                         self.servers_list.item(selected_item)["values"][1]
            cwd = os.path.join(os.getcwd(), "servers", name)
            for p in running_java:
                if p[1] == cwd:
                    if kill:
                        os.kill(p[0], 9)
                    else:
                        os.kill(p[0], 2)
                    log.debug("Killed " + str(p[0]) + " " + ' '.join(p[2]))
        if kill:
            self.refresh_servers_list()

    def refresh_servers_list_idle_task(self):
        self.refresh_servers_list()
        self.after(10000, self.refresh_servers_list_idle_task)

    def chkbox_gui_change(self):
        for selected_item in self.servers_list.selection():
            name = self.servers_list.item(selected_item)["values"][0]
            cfg["servers"][name]["gui"] = self.gui_var.get()
        config_update()
    def open_plugins(self):
        servers = []
        for selected_item in self.servers_list.selection():
            name = self.servers_list.item(selected_item)["values"][0]
            servers.append(cfg["servers"][name])
        pammanage.PluginsManagement(servers)


def execute(cmd, shell=False, cwd=None):
    popen = subprocess.Popen(cmd, shell=shell, cwd=cwd)
    return_code = popen.wait()
    if return_code:
        log.error("Command " + ' '.join(cmd) + " returned error code " + str(return_code))
        messagebox.showerror('The operation was performed unsuccessfully',
                             'Command ' + ' '.join(cmd) + ' returned error code ' + str(return_code))


def config_update():
    log.info("Writing config " + CONFIG_NAME)
    json.dump(cfg, open(CONFIG_NAME, "w"))


log.basicConfig(level=log.DEBUG, format="%(name)s - %(levelname)s - %(message)s")
log.getLogger("urllib3").setLevel(log.WARNING)
if os.path.isfile(CONFIG_NAME):
    cfg = json.load(open(CONFIG_NAME, "r"))
else:
    log.info(CONFIG_NAME + " not found, creating")
    json.dump(DEFAULT_CONFIG, open(CONFIG_NAME, "w"))
    cfg = DEFAULT_CONFIG
if not os.path.isdir("servers"):
    log.debug("'servers' not found, creating")
    os.mkdir("servers")
if __name__ == '__main__':
    window = App()
    window.gui()