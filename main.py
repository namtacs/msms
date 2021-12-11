#!/usr/bin/env python3
import json
import os
import logging as log
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import subprocess
import shutil
import psutil
import time

VERSION = 1
NAME = "MSMS"
CONFIG_NAME = "config.json"
DEFAULT_CONFIG = {"servers" : {}, "version" : VERSION}
class ServerCreateHelper(tk.Tk):
	def __init__(self):
		super().__init__()
		self.title("Create server")
		nameEntry = tk.Entry(self)
		nameEntry.grid(column=0, row=0)
		typeComboBox = ttk.Combobox(self, values = ("BungeeCord", "Forge", "Spigot", "Paper", "Official"))
		typeComboBox.current(2)
		typeComboBox.grid(column=1, row=0)
		lbl = tk.Label(self, text = "Version:", padx = 5)
		lbl.grid(column = 2, row = 0)
		versionEntry = tk.Entry(self, width=5)
		versionEntry.grid(column=3, row=0)
		btn = tk.Button(self, text="Create", command = lambda: self.create(nameEntry.get(), typeComboBox.get(), versionEntry.get()))
		btn.grid(column = 0, row = 1)
		self.mainloop()
	def create(self, name, type, version):
		log.debug("Create called with parameters: " + name + ", " + type + ", " + version)
		serverDir = os.path.join("servers", name)
		os.mkdir(serverDir)
		if type == "Forge":
			cmd = ["java", "-jar", os.path.join("serverfiles", "forge" + version + ".jar"), "--installServer", serverDir]
			log.info("The installation log will be written to the installer.log file")
			log.info(cmd)
			execute(cmd)
		elif type == "Spigot":
			cmd = ["java", "-jar", os.path.join("serverfiles", "spigot.jar"), "-o", serverDir, "--rev", version]
			log.info("The installation log will be written to the BuildTools.log.txt file")
			log.info(cmd)
			execute(cmd)
		elif type == "Paper":
			shutil.copy(os.path.join("serverfiles", "paper-" + version + ".jar"), serverDir)
		with open(os.path.join(serverDir, "eula.txt"), "w") as f: f.write("eula=true")
		cfg["servers"][name] = {"type" : type.lower(), "version" : version, "dir" : serverDir}
		config_update()
		window.refresh_servers_list()
class ServerPropertiesEditor(tk.Tk):
	def __init__(self):
		super().__init__()
		self.title("Server properties editor")
		self.btn_save = tk.Button(self, text = "Save", bg = "#00d2d2", activebackground = "LightGoldenrodYellow", command = self.save)
		self.btn_save.grid(column = 0, row = 0)
		self.file = os.path.join("servers", window.servers_list.item(window.servers_list.selection()[0])["values"][0], "server.properties")
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
					tk.Label(self, text = key).grid(column = 0, row = i)
					entry = tk.Entry(self, bg = "#D3D3D3", bd = 0)
					if key == "motd":
						value = json.loads('"' + value + '"')
						value = self.replace_ccodes(value)
					entry.insert(0, value)
					entry.grid(column = 1, row = i)
					self.entrys.append(entry)
		self.mainloop()
	def replace_ccodes(self, text, reverse = False):
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
	def fixed_map(self, option): return [elm for elm in self.servers_list_style.map("Treeview", query_opt=option) if elm[:2] != ("!disabled", "!selected")]
	def gui(self):
		super().__init__()
		self.title(NAME)
		mainmenu = tk.Menu(self)
		servicemenu = tk.Menu(mainmenu)
		servicemenu.add_command(label = "Delete unregistred servers", command = self.delete_unregistred_servers)
		mainmenu.add_cascade(label = "Service", menu = servicemenu)
		self.config(menu = mainmenu)
		self.servers_list = ttk.Treeview(self, columns = ("name", "type", "state"), show = "headings")
		self.servers_list.heading('name', text='Server Name')
		self.servers_list.heading('type', text='Type')
		self.servers_list.heading('state', text='State')
		self.servers_list.grid(column = 0, row = 0)
		self.servers_list_style = ttk.Style()
		self.servers_list_style.map("Treeview", foreground = self.fixed_map("foreground"), background = self.fixed_map("background"))
		self.servers_list.tag_configure('running', background = '#9dee9d')
		self.servers_list.tag_configure('stopped', background = '#ee9d9d')
		self.btn_create = tk.Button(self, text = "Create server", bg = "#00d2d2", activebackground = "LightGoldenrodYellow", command = ServerCreateHelper)
		self.btn_create.grid(column = 0, row = 1)
		self.btn_props = tk.Button(self, text = "Server properties", bg = "#00d2d2", activebackground = "LightGoldenrodYellow", command = ServerPropertiesEditor, state = tk.DISABLED)
		self.btn_props.grid(column = 1, row = 1)
		self.btn_start = tk.Button(self, text = "Start", bg = "#00d2d2", activebackground = "LightGoldenrodYellow", command = self.start_server, state = tk.DISABLED)
		self.btn_start.grid(column = 2, row = 1)
		self.btn_stop = tk.Button(self, text = "Stop", bg = "#00d2d2", activebackground = "LightGoldenrodYellow", command = self.stop_server, state = tk.DISABLED)
		self.btn_stop.grid(column = 3, row = 1)
		self.btn_del = tk.Button(self, text = "Delete", bg = "#00d2d2", activebackground = "LightGoldenrodYellow", command = self.delete_server, state = tk.DISABLED)
		self.btn_del.grid(column = 1, row = 2)
		self.refresh_servers_list_idle_task()
		self.bind('<<TreeviewSelect>>', self.servers_list_select)
		self.mainloop()
	def refresh_servers_list(self):
		log.debug("Refreshing servers list")
		for item in self.servers_list.get_children():
			self.servers_list.delete(item)
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
			except: pass
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
			if os.path.join(os.getcwd(), "servers", server, runfile) in running:
				state = "Running"
			else:
				state = "Stopped"
			self.servers_list.insert("", "end", values=(server, data["type"], state), tags = (state.lower(),))
		self.btn_del.configure(state = tk.DISABLED)
		self.btn_start.configure(state = tk.DISABLED)
		self.btn_stop.configure(state = tk.DISABLED)
		self.btn_props.configure(state = tk.DISABLED)
	def servers_list_select(self, event):
		self.btn_del.configure(state = tk.NORMAL)
		self.btn_start.configure(state = tk.NORMAL)
		self.btn_stop.configure(state = tk.NORMAL)
		self.btn_props.configure(state = tk.NORMAL)

	def delete_server(self):
		for selected_item in self.servers_list.selection():
			name = self.servers_list.item(selected_item)["values"][0]
			shutil.rmtree(os.path.join("servers", name))
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
			name, type = self.servers_list.item(selected_item)["values"][0], self.servers_list.item(selected_item)["values"][1]
			serverDir = os.path.join("servers", name)
			cwd = os.path.join(os.getcwd(), serverDir)
			if type == "forge": subprocess.Popen(['"' + os.path.join(cwd, "run.sh") + '"'], cwd = cwd, shell = True, stdout = subprocess.DEVNULL)
			elif type == "spigot": subprocess.Popen(["java", "-jar", os.path.join(cwd, "spigot-" + cfg["servers"][name]["version"] + ".jar")], cwd = cwd, stdout = subprocess.DEVNULL)
			elif type == "paper": subprocess.Popen(["java", "-jar", os.path.join(cwd, "paper-" + cfg["servers"][name]["version"] + ".jar")], cwd = cwd, stdout = subprocess.DEVNULL)
			log.info("Server '" + name + "' started")
		self.refresh_servers_list()
	def stop_server(self):
		running_java = []
		for pid in psutil.pids():
			try:
				p = psutil.Process(pid)
				if p.name() == "java":
					running_java.append((pid, p.cwd(), p.cmdline()))
			except: pass
		for selected_item in self.servers_list.selection():
			name, type = self.servers_list.item(selected_item)["values"][0], self.servers_list.item(selected_item)["values"][1]
			cwd = os.path.join(os.getcwd(), "servers", name)
			for p in running_java:
				if p[1] == cwd:
					os.kill(p[0], 2)
					log.debug("Killed " + str(p[0]) + " " + ' '.join(p[2]))
	def refresh_servers_list_idle_task(self):
		self.refresh_servers_list()
		self.after(10000, self.refresh_servers_list_idle_task)
def execute(cmd, shell = False, cwd = None):
	popen = subprocess.Popen(cmd, shell = shell, cwd = cwd)
	return_code = popen.wait()
	if return_code:
		log.error("Command " + ' '.join(cmd) + " returned error code " + str(return_code))
		messagebox.showerror("The operation was performed unsuccessfully", "Command " + ' '.join(cmd) + " returned error code " + str(return_code))
def config_update():
	log.info("Writing config " + CONFIG_NAME)
	json.dump(cfg, open(CONFIG_NAME, "w"))

log.basicConfig(level=log.DEBUG, format="%(name)s - %(levelname)s - %(message)s")
if os.path.isfile(CONFIG_NAME):
	cfg = json.load(open(CONFIG_NAME, "r"))
else:
	log.info(CONFIG_NAME + " not found, creating")
	json.dump(DEFAULT_CONFIG, open(CONFIG_NAME, "w"))
	cfg = DEFAULT_CONFIG
if not os.path.isdir("servers"):
	log.debug("'servers'" + " not found, creating")
	os.mkdir("servers")
if __name__ == '__main__':
	window = App()
	window.gui()
