#!/usr/bin/env python3
import json
import os
import logging as log
import subprocess
import shutil
import time
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from tkinter import scrolledtext
import requests
import threading
import PluginsAndModsManagement as pammanage
from PIL import Image, ImageTk
import platform
from transliterate import translit
from transliterate.exceptions import LanguageDetectionError
import psutil
from bs4 import BeautifulSoup
import jdk_manager as jdk
import argparse
import sys
import webbrowser

VERSION = 6
NAME = "MSMS"
CONFIG_NAME = "config.json"
OS = platform.system()
if OS == "Linux":
    os_lang = os.getenv("LANG")
elif OS == "Windows":
    from locale import windows_locale
    from ctypes import windll

    os_lang = windows_locale[windll.kernel32.GetUserDefaultUILanguage()]
else:
    os_lang = "en"
if "_" in os_lang:
    os_lang = os_lang[:os_lang.index("_")]
DEFAULT_CONFIG = {"servers": {}, "version": VERSION, "lang": os_lang}


class ServerCreateHelper(tk.Tk):
    class ServerTypeSelection(tk.Frame):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            tk.Label(self, text=LANG["ServerCreateHelper"]["type_field"]).grid(column=0, row=0)
            self.typeComboBox = ttk.Combobox(self, values=(
            LANG["ServerCreateHelper"]["game_server"], LANG["ServerCreateHelper"]["proxy"]))
            self.typeComboBox.current(0)
            self.typeComboBox.bind("<<ComboboxSelected>>", self.change)
            self.typeComboBox.grid(column=1, row=0)
            tk.Label(self, text=LANG["ServerCreateHelper"]["compatibility"]).grid(column=0, row=1)
            self.compatibility_slider = ttk.Scale(self, from_=1, to=5, command=self.change)
            self.compatibility_slider.grid(column=1, row=1, sticky="w")
            tk.Label(self, text=LANG["ServerCreateHelper"]["efficiency"]).grid(column=2, row=1)
            self.efficiency_slider = ttk.Scale(self, from_=1, to=5, command=self.change)
            self.efficiency_slider.grid(column=3, row=1, sticky="w")
            self.plugins_var = tk.BooleanVar(self)
            self.mods_var = tk.BooleanVar(self)
            self.plugins_chkbtn = tk.Checkbutton(self, text=LANG["ServerCreateHelper"]["plugins"],
                                                 variable=self.plugins_var,
                                                 command=self.change)
            self.plugins_chkbtn.grid(column=0, row=2)
            self.mods_chkbtn = tk.Checkbutton(self, text=LANG["ServerCreateHelper"]["mods"], variable=self.mods_var,
                                              command=self.change)
            self.mods_chkbtn.grid(column=1, row=2)
            tk.Label(self, text=LANG["ServerCreateHelper"]["suit"], pady=30).grid(column=0, row=3)
            self.done = tk.Label(self)
            self.done.grid(column=1, row=3, sticky="w")
            self.change()

        def change(self, e=None):
            def numrange(one, two):
                if one > two:
                    return one - two
                else:
                    return two - one

            t = self.typeComboBox.current()
            c = self.compatibility_slider.get()
            e = self.efficiency_slider.get()
            plugins = self.plugins_var.get()
            mods = self.mods_var.get()
            minrange = ""
            minranger = 999
            for i in serverrating:
                name = i
                i = serverrating[i]
                if i["type"] != t:
                    continue
                if i["plugins"] != plugins:
                    continue
                if i["mods"] != mods:
                    continue
                r = numrange(i["efficiency"], e) + numrange(i["compatibility"], c)
                if r < minranger:
                    minranger = r
                    minrange = name
            self.done["text"] = minrange

    def __init__(self):
        pass

    def gui(self):
        super().__init__()
        self.title(LANG["ServerCreateHelper"]["create_title"])
        tab_control = ttk.Notebook(self)
        self.tab1 = tk.Frame(tab_control)
        tab2 = self.ServerTypeSelection(tab_control)
        tab_control.add(self.tab1, text=LANG["ServerCreateHelper"]["create_title"])
        tab_control.add(tab2, text=LANG["ServerCreateHelper"]["server_type_selection_tab"])
        self.core_icon = tk_image(self.tab1, res("icons/purpur.png"))
        self.core_icon.grid(column=0, row=0)
        tk.Label(self.tab1, text=LANG["ServerCreateHelper"]["name_field"], padx=5).grid(column=1, row=0)
        nameEntry = tk.Entry(self.tab1)
        nameEntry.grid(column=2, row=0)
        tk.Label(self.tab1, text=LANG["ServerCreateHelper"]["type_field"], padx=5).grid(column=3, row=0)
        self.typeComboBox = ttk.Combobox(self.tab1,
                                         values=("Velocity", "Forge", "Spigot", "Paper", "Purpur", "Vanilla"))
        self.typeComboBox.bind("<<ComboboxSelected>>", self.type_update)
        self.typeComboBox.current(4)
        self.typeComboBox.grid(column=4, row=0)
        tk.Label(self.tab1, text=LANG["ServerCreateHelper"]["version_field"], padx=5).grid(column=5, row=0)
        versionEntry = tk.Entry(self.tab1, width=5)
        versionEntry.grid(column=6, row=0)
        btn = tk.Button(self.tab1, text=LANG["ServerCreateHelper"]["create_button"],
                        command=lambda: self.create(nameEntry.get(), self.typeComboBox.get(), versionEntry.get()))
        btn.grid(column=0, row=1)
        tab_control.grid(column=0, row=0)
        self.mainloop()

    def type_update(self, e=None):
        self.core_icon.destroy()
        type = self.typeComboBox.get()
        if type == "Forge":
            self.core_icon = tk_image(self.tab1, res("icons/forge.png"))
            self.core_icon.grid(column=0, row=0)
        elif type == "Spigot":
            self.core_icon = tk_image(self.tab1, res("icons/spigot.png"))
            self.core_icon.grid(column=0, row=0)
        elif type == "Paper":
            self.core_icon = tk_image(self.tab1, res("icons/paper.png"))
            self.core_icon.grid(column=0, row=0)
        elif type == "Purpur":
            self.core_icon = tk_image(self.tab1, res("icons/purpur.png"))
            self.core_icon.grid(column=0, row=0)

    def update_gui(self, servers_list):
        super().__init__()
        self.title(LANG["ServerCreateHelper"]["update_title"])
        tab_control = ttk.Notebook(self)
        tab1 = tk.Frame(tab_control)
        tab2 = self.ServerTypeSelection(tab_control)
        tab_control.add(tab1, text=LANG["ServerCreateHelper"]["update_title"])
        tab_control.add(tab2, text=LANG["ServerCreateHelper"]["server_type_selection_tab"])
        self.core_icon = tk_image(tab1, res("icons/purpur.png"))
        self.core_icon.grid(column=0, row=0)
        tk.Label(tab1, text=LANG["ServerCreateHelper"]["type_field"], padx=5).grid(column=1, row=0)
        self.typeComboBox = ttk.Combobox(tab1, values=("Velocity", "Forge", "Spigot", "Paper", "Purpur", "Vanilla"))
        self.typeComboBox.bind("<<ComboboxSelected>>", self.type_update)
        self.typeComboBox.current(3)
        self.typeComboBox.grid(column=2, row=0)
        lbl = tk.Label(tab1, text=LANG["ServerCreateHelper"]["version_field"], padx=5)
        lbl.grid(column=3, row=0)
        versionEntry = tk.Entry(tab1, width=5)
        versionEntry.grid(column=4, row=0)
        btn = tk.Button(tab1, text=LANG["ServerCreateHelper"]["update_button"],
                        command=lambda: self.update_server(servers_list, self.typeComboBox.get(), versionEntry.get()))
        btn.grid(column=0, row=1)
        tab_control.grid(column=0, row=0)
        self.mainloop()

    def create(self, name, type, version):
        log.debug("Create called with parameters: " + name + ", " + type + ", " + version)
        try:
            serverDir = os.path.join("servers", translit(name, reversed=True))
        except LanguageDetectionError:
            serverDir = os.path.join("servers", name)
        serverDir = serverDir.replace(" ", "_").replace("'", "")
        os.mkdir(serverDir)
        self.create_core(serverDir, type, version, name)
        with open(os.path.join(serverDir, "eula.txt"), "w") as f:
            f.write("eula=true")
        config_update()

    def update_server(self, servers_list, type, version):
        for s in servers_list.selection():
            name = servers_list.item(s)["values"][0]
            data = cfg["servers"][name]
            self.create_core(data["dir"], type, version)
            cfg["servers"][name]["type"] = type.lower()
            cfg["servers"][name]["version"] = version
            config_update()

    def create_core(self, dir, type, version, name=None):
        if type != "Velocity":
            if not install_jdk(version):
                return
        if type == "Forge":
            java = java_path(version)
            r = requests.get("https://files.minecraftforge.net/net/minecraftforge/forge/index_" + version + ".html")
            soup = BeautifulSoup(r.text, "html.parser")
            link = soup.select(".link-boosted a")[0]["href"]
            link = link[link.index("url=") + 4:]  # Ads skip
            data = requests.get(link).content
            with open(os.path.join("serverfiles", "forge" + version + ".jar"), "wb") as f:
                f.write(data)
            cmd = [java, "-jar", os.path.join("serverfiles", "forge" + version + ".jar"), "--installServer",
                   dir]
            log.info(cmd)
            if name:
                cfg["servers"][name] = {"type": type.lower(), "version": version, "dir": dir, "gui": True,
                                        "state": "Inactive"}
            thread = threading.Thread(target=self.creating_thread, args=(name, cmd))
            thread.start()
        elif type == "Spigot":
            java = java_path(version)
            latest_build = json.loads(
                requests.get("https://hub.spigotmc.org/jenkins/job/BuildTools/lastSuccessfulBuild/api/json").text)[
                "number"]
            log.debug("Latest BuildTools build is " + str(latest_build))
            installed = [int(i[11:][:-4]) for i in os.listdir("serverfiles") if i[:10] == "BuildTools"]
            log.debug("BuildTools installed versions: " + " ".join(str(i) for i in installed))
            latest_installed_build = sorted(installed + [0], reverse=True)[0]
            if latest_installed_build < latest_build:
                log.info("Updating BuildTools version from " + str(latest_installed_build) + " to " + str(latest_build))
                data = requests.get(
                    "https://hub.spigotmc.org/jenkins/job/BuildTools/lastSuccessfulBuild/artifact/target/BuildTools.jar").content
                with open(os.path.join("serverfiles", "BuildTools-" + str(latest_build) + ".jar"), "wb") as f:
                    f.write(data)
            cmd = [java, "-Xmx1024M", "-jar", os.path.join("serverfiles", "BuildTools-" + str(latest_build) + ".jar"),
                   "-o", dir, "--rev", version]
            log.info(cmd)
            if name:
                cfg["servers"][name] = {"type": type.lower(), "version": version, "dir": dir, "gui": True,
                                        "state": "Inactive"}
            thread = threading.Thread(target=self.creating_thread, args=(name, cmd))
            thread.start()
        elif type == "Paper":
            latest_build = str(
                json.loads(requests.get("https://papermc.io/api/v2/projects/paper/versions/" + version).text)[
                    "builds"][-1])
            log.info("Latest build is " + latest_build)
            jarfile = os.path.join("serverfiles", "paper-" + version + "-" + latest_build + ".jar")
            if os.path.isfile(jarfile):
                log.info("Found cached paper " + version + " build " + latest_build)
            else:
                log.info("Downloading")
                with open(jarfile, "wb") as f:
                    f.write(requests.get(
                        "https://papermc.io/api/v2/projects/paper/versions/" + version + "/builds/" + latest_build + "/downloads/paper-" + version
                        + "-" + latest_build + ".jar").content)
            shutil.copy(jarfile, os.path.join(dir, "paper-" + version + ".jar"))
            if name:
                cfg["servers"][name] = {"type": type.lower(), "version": version, "dir": dir, "gui": True,
                                        "state": "normal"}
        elif type == "Purpur":
            latest_build = str(
                json.loads(requests.get("https://api.purpurmc.org/v2/purpur/" + version + "/latest").text)["build"])
            log.info("Latest build is " + latest_build)
            jarfile = os.path.join("serverfiles", "purpur-" + version + "-" + latest_build + ".jar")
            if os.path.isfile(jarfile):
                log.info("Found cached purpur " + version + " build " + latest_build)
            else:
                log.info("Downloading")
                with open(jarfile, "wb") as f:
                    f.write(requests.get(
                        "https://api.purpurmc.org/v2/purpur/" + version + "/" + latest_build + "/download").content)
            shutil.copy(jarfile, os.path.join(dir, "purpur-" + version + ".jar"))
            if name:
                cfg["servers"][name] = {"type": type.lower(), "version": version, "dir": dir, "gui": True,
                                        "state": "normal"}
        elif type == "Velocity":
            version = str(
                json.loads(requests.get("https://papermc.io/api/v2/projects/velocity").text)[
                    "versions"][-1])
            latest_build = str(
                json.loads(requests.get("https://papermc.io/api/v2/projects/velocity/versions/" + version).text)[
                    "builds"][-1])
            log.info("Latest build is " + latest_build)
            jarfile = os.path.join("serverfiles", "paper-" + version + "-" + latest_build + ".jar")
            if os.path.isfile(jarfile):
                log.info("Found cached velocity " + version + " build " + latest_build)
            else:
                log.info("Downloading")
                with open(jarfile, "wb") as f:
                    f.write(requests.get(
                        "https://papermc.io/api/v2/projects/velocity/versions/" + version + "/builds/" + latest_build + "/downloads/velocity-" + version
                        + "-" + latest_build + ".jar").content)
            shutil.copy(jarfile, os.path.join(dir, "velocity-" + version + ".jar"))
            if name:
                cfg["servers"][name] = {"type": type.lower(), "version": version, "dir": dir,
                                        "state": "normal"}

    def creating_thread(self, name, cmd):
        execute(cmd)
        if name:
            log.info("Server " + name + " is completely ready")
            cfg["servers"][name]["state"] = "normal"
            config_update()
        else:
            log.info("Core is completely ready")


class ServerPropertiesEditor(tk.Tk):
    ccodes = [
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

    def __init__(self):
        self.keys = []
        self.entrys = []

    def gui(self, servers_list):
        super().__init__()
        self.title(LANG["ServerPropertiesEditor"]["title"])
        self.btn_save = tk.Button(self, text=LANG["ServerPropertiesEditor"]["save_button"], bg="#00d2d2",
                                  activebackground="LightGoldenrodYellow",
                                  command=self.save)
        self.btn_save.grid(column=0, row=0)
        data = cfg["servers"][servers_list.item(servers_list.selection()[0])["values"][0]]
        if data["type"] == "velocity":
            filename = "velocity.toml"
            self.method = "text"
        else:
            filename = "server.properties"
            self.method = "default"
        self.file = os.path.join(data["dir"],
                                 filename)
        if self.method == "default":
            with open(self.file, "r") as file:
                column = 0
                row = 1
                for line in file:
                    if not line.startswith("#"):
                        key, value = line[:-1].split("=")
                        self.keys.append(key)
                        tk.Label(self, text=key).grid(column=column, row=row)
                        entry = tk.Entry(self, bg="#D3D3D3", bd=0)
                        if key == "motd":
                            value = json.loads('"' + value + '"')
                            value = self.replace_ccodes(value)
                        entry.insert(0, value)
                        entry.grid(column=column + 1, row=row)
                        self.entrys.append(entry)
                        column += 2
                        if column > 4:
                            column = 0
                            row += 1
        elif self.method == "text":
            self.text = scrolledtext.ScrolledText(self)
            with open(self.file, "r") as f:
                self.text.insert("insert", f.read())
            self.text.grid(column=0, row=1)
        self.mainloop()

    def replace_ccodes(self, text, reverse=False):
        for ccode in self.ccodes:
            if reverse:
                text = text.replace(ccode[1], ccode[0])
            else:
                text = text.replace(ccode[0], ccode[1])
        return text

    def save(self, use_get=True):
        if self.method == "default":
            with open(self.file, "w") as file:
                file.write("# Edited with " + NAME + "\n")
                for i in range(len(self.keys)):
                    if use_get:
                        value = self.entrys[i].get()
                    else:
                        value = self.entrys[i]
                    if self.keys[i] == "motd":
                        value = json.dumps(value)[1:-1]
                        value = self.replace_ccodes(value, True)
                    file.write(self.keys[i] + "=" + value + "\n")
        elif self.method == "text":
            with open(self.file, "w") as file:
                file.write(self.text.get("1.0", "end-1c"))


class App:
    def get_servers_state(self):
        running_sh = []
        running_java = []
        for pid in psutil.pids():
            try:
                p = psutil.Process(pid)
                name = p.name()
                if "sh" in name:
                    running_sh.append(p.cmdline()[1])
                elif "java" in name:
                    running_java.append(p.cmdline()[2])
            except:
                pass
        for server in cfg["servers"]:
            data = cfg["servers"][server]
            if data["type"] == "forge":
                if main_version(data["version"]) > 16:
                    runfile = "run.sh"
                    running = running_sh
                else:
                    runfile = "forge-" + data["version"]
                    running = running_java
            elif data["type"] == "spigot":
                runfile = "spigot-" + data["version"] + ".jar"
                running = running_java
            elif data["type"] == "paper":
                runfile = "paper-" + data["version"] + ".jar"
                running = running_java
            elif data["type"] == "purpur":
                runfile = "purpur-" + data["version"] + ".jar"
                running = running_java
            elif data["type"] == "velocity":
                runfile = "velocity-" + data["version"] + ".jar"
                running = running_java
            else:
                runfile = ""
            if data["state"] == "normal":
                if [i for i in running if os.path.join(data["dir"], runfile) in i]:
                    state = "running"
                else:
                    state = "stopped"
            else:
                state = data["state"]
            yield {"name": server, "data": data, "state": state, "runfile": runfile}

    def delete_server(self, namelist):
        for name in namelist:
            shutil.rmtree(cfg["servers"][name]["dir"], ignore_errors=True)
            del cfg["servers"][name]
            log.info("Server '" + name + "' deleted successfully")
        config_update()

    def delete_unregistered_servers(self):
        for d in os.listdir("servers"):
            path = os.path.join("servers", d)
            if os.path.isdir(path):
                if not d in cfg["servers"]:
                    shutil.rmtree(path)
                    log.info("Server '{0}' deleted successfully".format(d))
                    messagebox.showinfo(LANG["App"]["server_deleted"],
                                        LANG["App"]["server_deleted_successfully"].format(d))

    def start_server(self, cfglist):
        for data in cfglist:
            type = data["type"]
            serverDir = data["dir"]
            cwd = os.path.abspath(serverDir)
            userargs = []
            java = java_path(data["version"])
            log.debug("Java path: " + java)
            if "gui" in data and not data["gui"]: userargs.append("nogui")
            if type == "forge":
                if main_version(data["version"]) > 16:
                    if OS == "Linux":
                        subprocess.Popen(['"' + os.path.join(cwd, "run.sh") + '"'] + userargs, cwd=cwd, shell=True)
                    elif OS == "Windows":
                        lines = []
                        with open(os.path.join(cwd, "run.bat"), "r") as f:
                            for line in f:
                                if not "pause" in line:
                                    lines.append(line)
                                else:
                                    log.debug("Removed pause in run.bat")
                        with open(os.path.join(cwd, "run.bat"), "w") as f:
                            for line in lines:
                                f.write(line)
                        subprocess.Popen(["run.bat"] + userargs, cwd=cwd, shell=True)
                else:
                    forgefile = [i for i in os.listdir(serverDir) if
                                 i.startswith("forge-" + data["version"]) and i.endswith(".jar")][0]
                    subprocess.Popen(
                        [java, "-jar", os.path.join(cwd, forgefile)] + userargs, cwd=cwd)
            elif type == "spigot":
                subprocess.Popen(
                    [java, "-jar", os.path.join(cwd, "spigot-" + data["version"] + ".jar")] + userargs, cwd=cwd)
            elif type == "paper":
                subprocess.Popen(
                    [java, "-jar", os.path.join(cwd, "paper-" + data["version"] + ".jar")] + userargs, cwd=cwd)
            elif type == "purpur":
                subprocess.Popen(
                    [java, "-jar", os.path.join(cwd, "purpur-" + data["version"] + ".jar")] + userargs, cwd=cwd)
            elif type == "velocity":
                subprocess.Popen(
                    [java, "-jar", os.path.join(cwd, "velocity-" + data["version"] + ".jar")] + userargs, cwd=cwd)
            log.info("Server " + data["type"] + " " + data["version"] + " started")

    def stop_server(self, cfglist, kill=False):
        running_java = []
        for pid in psutil.pids():
            try:
                p = psutil.Process(pid)
                name = p.name()
                if "java" in name:
                    running_java.append((pid, p.cwd(), p.cmdline()))
            except:
                pass
        for data in cfglist:
            cwd = os.path.abspath(data["dir"])
            for p in running_java:
                if p[1] == cwd:
                    if kill:
                        os.kill(p[0], 9)
                    else:
                        os.kill(p[0], 2)
                    log.debug("Killed {0} {1}".format(str(p[0]), ' '.join(p[2])))


class AppTk(tk.Tk, App):
    def __init__(self):
        super().__init__()
        self.title(NAME)
        self.iconphoto(True, tk.PhotoImage(file=res("icons/icon.png")))
        mainmenu = tk.Menu(self)
        servicemenu = tk.Menu(mainmenu)
        infomenu = tk.Menu(mainmenu)

        def settings_open(): AppSettingsTk(self)

        servicemenu.add_command(label=LANG["App"]["settings"],
                                command=settings_open)
        servicemenu.add_command(label=LANG["App"]["delete_unregistered_servers"],
                                command=self.delete_unregistered_servers)
        mainmenu.add_cascade(label=LANG["App"]["service"], menu=servicemenu)
        mainmenu.add_cascade(label=LANG["App"]["info"], menu=infomenu)
        self.config(menu=mainmenu)
        self.servers_list = ttk.Treeview(self, columns=("name", "type", "state", "version"), show="headings")
        self.servers_list.heading('name', text=LANG["App"]["server_name"])
        self.servers_list.heading('type', text=LANG["App"]["server_type"])
        self.servers_list.column('type', width=72)
        self.servers_list.heading('state', text=LANG["App"]["server_state"])
        self.servers_list.column('state', width=64)
        self.servers_list.heading('version', text=LANG["App"]["server_version"])
        self.servers_list.column('version', width=64)
        self.servers_list.grid(column=0, row=0)
        self.servers_list_style = ttk.Style()
        self.servers_list_style.map("Treeview", foreground=self.fixed_map("foreground"),
                                    background=self.fixed_map("background"))
        self.servers_list.tag_configure('running', background='#9dee9d')
        self.servers_list.tag_configure('stopped', background='#ee9d9d')
        self.servers_list.tag_configure('inactive', background='#D3D3D3')
        self.options_frame = tk.Frame(self)
        self.options_frame.grid(column=1, row=0, sticky="nw")
        self.gui_var = tk.BooleanVar()
        self.chkbtn_gui = tk.Checkbutton(self.options_frame, text=LANG["App"]["gui"], variable=self.gui_var,
                                         command=self.chkbox_gui_change)
        self.chkbtn_gui.grid(column=0, row=0)

        def btn_create_press(): ServerCreateHelper().gui()

        self.btn_create = tk.Button(self, text=LANG["App"]["create_server_button"],
                                    activebackground="LightGoldenrodYellow",
                                    command=btn_create_press, bg="#00d2d2")
        self.btn_create.grid(column=0, row=1)
        self.actions_frame = tk.Frame(self)
        self.actions_frame.grid(column=1, row=1)

        def btn_props_press(): ServerPropertiesEditor().gui(self.servers_list)

        self.btn_props = tk.Button(self.actions_frame, text=LANG["App"]["server_properties_button"], bg="#00d2d2",
                                   activebackground="LightGoldenrodYellow", command=btn_props_press)
        self.btn_props.grid(column=0, row=0)

        def btn_start_press():
            self.start_server([cfg["servers"][self.servers_list.item(selected_item)["values"][0]] for selected_item in
                               self.servers_list.selection()])

        self.btn_start = tk.Button(self.actions_frame, text=LANG["App"]["start_button"], bg="#00d2d2",
                                   activebackground="LightGoldenrodYellow",
                                   command=btn_start_press)
        self.btn_start.grid(column=1, row=0)

        def btn_stop_press():
            self.stop_server([cfg["servers"][self.servers_list.item(selected_item)["values"][0]] for selected_item in
                              self.servers_list.selection()])

        self.btn_stop = tk.Button(self.actions_frame, text=LANG["App"]["stop_button"], bg="#00d2d2",
                                  activebackground="LightGoldenrodYellow",
                                  command=btn_stop_press)
        self.btn_stop.grid(column=2, row=0)
        self.btn_plugins = tk.Button(self.actions_frame, text=LANG["App"]["plugins_button"], bg="#00d2d2",
                                     activebackground="LightGoldenrodYellow",
                                     command=self.open_plugins)
        self.btn_plugins.grid(column=3, row=0)

        def btn_kill_press():
            self.stop_server([cfg["servers"][self.servers_list.item(selected_item)["values"][0]] for selected_item in
                              self.servers_list.selection()], True)

        self.btn_kill = tk.Button(self.actions_frame, text=LANG["App"]["kill_button"], bg="#ca0000",
                                  activebackground="LightGoldenrodYellow",
                                  command=btn_kill_press)
        self.btn_kill.grid(column=4, row=0)
        self.btn_del = tk.Button(self.actions_frame, text=LANG["App"]["delete_button"], bg="#00d2d2",
                                 activebackground="LightGoldenrodYellow",
                                 command=self.delete_server)
        self.btn_del.grid(column=0, row=1)

        def btn_update_press(): ServerCreateHelper().update_gui(self.servers_list)

        self.btn_update = tk.Button(self.actions_frame, text=LANG["App"]["update_button"], bg="#00d2d2",
                                    activebackground="LightGoldenrodYellow",
                                    command=btn_update_press)
        self.btn_update.grid(column=1, row=1)
        self.previous_servers_list = []
        self.refresh_servers_list_idle_task()
        self.bind('<<TreeviewSelect>>', self.servers_list_select)
        if cfg["version"] < VERSION:
            msg = LANG["App"]["config_version_warning"].format(str(cfg["version"]), NAME, str(VERSION))
            log.warning(msg)
            messagebox.showwarning(LANG["App"]["version_warning"], msg)
            cfg["version"] = VERSION
            config_update()
        self.mainloop()

    def refresh_servers_list_idle_task(self):
        self.refresh_servers_list()
        self.after(5000, self.refresh_servers_list_idle_task)

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

    def servers_list_select(self, event):
        self.btn_del.configure(state=tk.NORMAL)
        self.btn_start.configure(state=tk.NORMAL)
        self.btn_stop.configure(state=tk.NORMAL)
        self.btn_kill.configure(state=tk.NORMAL)
        self.btn_props.configure(state=tk.NORMAL)
        if all(cfg["servers"][self.servers_list.item(sel)["values"][0]]["type"] in ["spigot", "paper", "purpur"] for
                sel in self.servers_list.selection()):
            self.btn_plugins.configure(state=tk.NORMAL)
        else:
            self.btn_plugins.configure(state=tk.DISABLED)
        self.btn_update.configure(state=tk.NORMAL)
        self.chkbtn_gui.configure(state=tk.NORMAL)
        self.gui_var.set(cfg["servers"][self.servers_list.item(self.servers_list.selection()[0])["values"][0]]["gui"])

    def fixed_map(self, option):
        return [elm for elm in self.servers_list_style.map("Treeview", query_opt=option) if
                elm[:2] != ("!disabled", "!selected")]

    def refresh_servers_list(self):
        list = [data for data in self.get_servers_state()]
        if self.previous_servers_list != list:
            log.debug("Servers list changed, refreshing")
            for item in self.servers_list.get_children():
                self.servers_list.delete(item)
            if len(cfg["servers"]) > 0:
                for data in list:
                    self.servers_list.insert("", "end", values=(
                    data["name"], data["data"]["type"], LANG["App"][data["state"]], data["data"]["version"]),
                                             tags=(data["state"],))
                if self.btn_create["bg"] == "Yellow": self.btn_create.configure(bg="#00d2d2")
            else:
                if self.btn_create["bg"] == "#00d2d2": self.btn_create.configure(bg="Yellow")
            self.btn_del.configure(state=tk.DISABLED)
            self.btn_start.configure(state=tk.DISABLED)
            self.btn_stop.configure(state=tk.DISABLED)
            self.btn_kill.configure(state=tk.DISABLED)
            self.btn_props.configure(state=tk.DISABLED)
            self.btn_plugins.configure(state=tk.DISABLED)
            self.btn_update.configure(state=tk.DISABLED)
            self.chkbtn_gui.configure(state=tk.DISABLED)
            self.previous_servers_list = list


class AppSettingsTk(tk.Tk):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.title(LANG["AppSettings"]["title"])
        tk.Label(self, text=LANG["AppSettings"]["language_field"], padx=5).grid(column=0, row=0)
        self.lang = ttk.Combobox(self, values=languages)
        self.lang.current(languages.index(os_lang))
        self.lang.bind("<<ComboboxSelected>>", self.lang_select)
        self.lang.grid(column=1, row=0)
        self.mainloop()

    def lang_select(self, e=None):
        global LANG, os_lang
        os_lang = self.lang.get()
        cfg["lang"] = os_lang
        config_update()
        LANG = json.load(open("lang.json", "r"))[os_lang]


def execute(cmd, shell=False, cwd=None):
    popen = subprocess.Popen(cmd, shell=shell, cwd=cwd)
    return_code = popen.wait()
    if return_code:
        log.error("Command " + ' '.join(cmd) + " returned error code " + str(return_code))
        messagebox.showerror(LANG["operation_unsuccessfully"],
                             LANG["command_error_code"].format(' '.join(cmd), str(return_code)))


def config_update():
    log.info("Writing config " + CONFIG_NAME)
    json.dump(cfg, open(CONFIG_NAME, "w"), indent=2)


def tk_image(master, file):
    image = Image.open(file)
    test = ImageTk.PhotoImage(image, master=master)
    label = tk.Label(master, image=test)
    label.image = test
    return label


def main_version(minecraft_version):
    return int(minecraft_version.split(".")[1])


def install_jdk(minecraft_version):
    version_number = main_version(minecraft_version)
    if version_number > 16 and len(
            [i for i in os.listdir("jdk") if i.startswith("jdk-17")]) == 0 and check_java_version() < 18:
        if messagebox.askokcancel(LANG["install_jdk"], LANG["jdk_required"].format("17")):
            log.info("Installing JDK 17")
            jdk.install(version="17", path="jdk")
        else:
            return False
    return True


def check_java_version():
    out = subprocess.check_output(["java", "-version"], stderr=subprocess.STDOUT).decode()
    out = out[out.index('"') + 1:]
    out = out[:out.index('"')]
    if out.startswith("1.8"):
        out = 8
    else:
        out = int(out[:out.index(".")])
    return out


def java_path(minecraft_version):
    version_number = main_version(minecraft_version)
    if version_number < 17:
        return "java"
    else:
        if check_java_version() == 17:
            return "java"
        else:
            return os.path.join(os.getcwd(), "jdk", [i for i in os.listdir("jdk") if i.startswith("jdk-17")][0], "bin",
                                "java")


def res(path):
    """Pyinstaller bundled data access.
    PyInstaller creates a temp folder and stores path in _MEIPASS."""
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = "."
    return os.path.join(base_path, path)


def browseropen():
    if not args.nobrowseropen:
        time.sleep(0.1)
        webbrowser.open_new_tab("http://localhost:" + str(args.port))


def parse_args():
    parser = argparse.ArgumentParser(description="Minecraft Servers Management System")
    parser.add_argument('--script', type=str, nargs='+', metavar="path",
                        help='Scripts(python code) to run')
    parser.add_argument('--host', type=str, default="",
                        help='Allowed web hosts to connect')
    parser.add_argument('--port', type=int, default="8080",
                        help='Web port')
    parser.add_argument('--nobrowseropen', action="store_true",
                        help="Don't open browser")
    args = parser.parse_args()
    if args.script:
        for i in args.script:
            if os.path.isfile(i):
                log.info("Executing script: " + i)
                with open(i, "r") as f:
                    exec(f.read())
            elif os.path.isdir(i):
                for i in os.listdir(i):
                    if i.endswith(".py") and os.path.isfile(i):
                        log.info("Executing script: " + i)
                        with open(i, "r") as f:
                            exec(f.read())
            else:
                log.error("Script not found: " + i)
    return args


log.basicConfig(level=log.DEBUG, format="%(name)s - %(levelname)s - %(message)s")
log.getLogger("urllib3").setLevel(log.WARNING)
log.getLogger("PIL").setLevel(log.INFO)
args = parse_args()
# Create necessary files and directories
if os.path.isfile(CONFIG_NAME):
    cfg: dict = json.load(open(CONFIG_NAME, "r"))
else:
    log.info(CONFIG_NAME + " not found, creating")
    json.dump(DEFAULT_CONFIG, open(CONFIG_NAME, "w"))
    cfg = DEFAULT_CONFIG
for i in ["servers", "serverfiles", "jdk"]:
    if not os.path.isdir(i):
        log.debug(f"{i} dir not found, creating")
        os.mkdir(i)
# Load language
LANG = json.load(open(res("lang.json"), "r", encoding="UTF-8"))
languages = list(LANG.keys())
os_lang = cfg["lang"]
if not os_lang in languages:
    os_lang = "en"
LANG = LANG[os_lang]
# Launch main app
serverrating = json.load(open(res("serverrating.json"), "r"))
if __name__ == '__main__':
    appinstance = AppTk()
