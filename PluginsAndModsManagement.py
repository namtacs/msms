import base64
import shutil
import tkinter as tk
from tkinter import scrolledtext
from tkinter import ttk
from tkinter import messagebox
from tkinter import filedialog
import os
import logging as log
import json
import requests
import time
from mtranslate import translate
import webbrowser
import threading
from difflib import SequenceMatcher


class PluginsManagement(tk.Tk):
	def __init__(self, servers):
		super().__init__()
		self.title("Plugins Management")
		self.tab_control = ttk.Notebook(self)
		self.all_tab = ttk.Frame(self.tab_control)
		self.installed_tab = ttk.Frame(self.tab_control)
		self.tab_control.add(self.all_tab, text="All")
		self.tab_control.add(self.installed_tab, text="Installed")
		self.tab_control.pack()
		self.servers = servers
		self.page_size = 18
		self.page_columns = 3
		# Installed tab
		self.installed_topbar = tk.Frame(self.installed_tab)
		self.installed_topbar.grid(column=int(self.page_columns / 2), row=0)
		self.install_from_file_btn = tk.Button(self.installed_topbar, text="Install plugin from file", command=self.install_plugin_from_file)
		self.install_from_file_btn.grid(column=0, row=0)
		self.installed_plugins = []
		self.installed_plugins_ids = []
		thread = threading.Thread(target=self.load_installed_plugins)
		thread.start()
		# All tab
		self.page_plugins = []
		self.page_data = []
		self.all_topbar = tk.Frame(self.all_tab)
		self.all_topbar.grid(column=int(self.page_columns / 2), row=0)
		self.search_entry = tk.Entry(self.all_topbar)
		self.search_entry.grid(column=0, row=0)
		self.search_btn = tk.Button(self.all_topbar, text="Search", command=self.get_page)
		self.search_btn.grid(column=1, row=0)
		self.page_spinbox = tk.Spinbox(self.all_tab, from_=1, to=255, command=self.get_page)
		self.page_spinbox.grid(column=int(self.page_columns / 2), row=int(self.page_size / self.page_columns) + 1)
		self.get_page()
		self.mainloop()

	def load_installed_plugins(self):
		for i in self.installed_plugins:
			i.destroy()
		column = 0
		row = 1
		for s in self.servers:
			for p in os.listdir(os.path.join(s["dir"], "plugins")):
				try:
					split = p[:p.rindex(".")].rsplit("-", maxsplit=2)
					name, id, version = split[0], split[-2], split[-1]
				except ValueError: continue
				except IndexError: continue
				else:
					if id in self.installed_plugins_ids:
						continue
					else:
						try:
							plugin = json.loads(requests.get("https://api.spiget.org/v2/resources/" + str(id)).text)
						except Exception as err:
							log.error('Error "{0}" while parsing installed plugin {1}'.format(str(err), name))
							continue
						plugin = self.plugin_parse(plugin)
						log.debug("Found installed plugin {0} with id {1}".format(name, id))
						if int(version) < plugin["versions"][0]["id"]:
							frame = tk.Frame(self.installed_tab, relief="raised", borderwidth=2, bg="Orange")
						else:
							frame = tk.Frame(self.installed_tab, relief="raised", borderwidth=2)
						if len(name) > 20:
							name_font = ("Liberation Sans Narrow", 13, "bold")
						else:
							name_font = ("FreeMono", 16, "bold")
						tk.Label(frame, text=name, font=name_font).pack()
						tk.Label(frame, text=plugin["tag"], font=("Liberation Sans Narrow", 10, "italic")).pack()
						tk.Label(frame, text=plugin["updateDateFormatted"]).pack()
						tk.Label(frame, text=plugin["releaseDateFormatted"], fg="gray").pack()
						frame.bind("<Button-1>", lambda e, p=plugin, s=self.servers: Plugin(p, s, self.install_plugin_from_file))
						frame.grid(column=column, row=row)
						column += 1
						if column > self.page_columns - 1:
							column = 0
							row += 1
						self.installed_plugins_ids.append(id)
						self.installed_plugins.append(frame)

	def get_page(self):
		for i in self.page_plugins:
			i.destroy()
		search = self.search_entry.get()
		if search == "":
			self.page_data = json.loads(requests.get("https://api.spiget.org/v2/resources/free?size=" + str(
				self.page_size) + "&page=" + self.page_spinbox.get() + "&sort=-updateDate").text)
		else:
			self.page_data = json.loads(
				requests.get("https://api.spiget.org/v2/search/resources/" + search + "?size=" + str(
					self.page_size) + "&page=" + self.page_spinbox.get() + "&sort=-updateDate").text)
		column = 0
		row = 1
		for plugin in self.page_data:
			plugin = self.plugin_parse(plugin)
			frame = ttk.Frame(self.all_tab, relief="raised", borderwidth=2)
			if len(plugin["name"]) > 25:
				name_font = ("Liberation Sans Narrow", 13, "bold")
			else:
				name_font = ("FreeMono", 16, "bold")
			tk.Label(frame, text=plugin["nameAscii"], font=name_font).pack()
			tk.Label(frame, text=plugin["tag"], font=("Liberation Sans Narrow", 10, "italic")).pack()
			tk.Label(frame, text=plugin["updateDateFormatted"]).pack()
			tk.Label(frame, text=plugin["releaseDateFormatted"], fg="gray").pack()
			frame.bind("<Button-1>", lambda e, p=plugin, s=self.servers: Plugin(p, s, self.install_plugin_from_file))
			frame.grid(column=column, row=row)
			column += 1
			if column > self.page_columns - 1:
				column = 0
				row += 1
			self.page_plugins.append(frame)

	def plugin_parse(self, plugin):
		struct_time = time.localtime(plugin["updateDate"])
		plugin["updateDateFormatted"] = "{0}-{1}-{2}".format(str(struct_time.tm_mday), str(struct_time.tm_mon),
															 str(struct_time.tm_year))
		struct_time = time.localtime(plugin["releaseDate"])
		plugin["releaseDateFormatted"] = "{0}-{1}-{2}".format(str(struct_time.tm_mday), str(struct_time.tm_mon),
															  str(struct_time.tm_year))
		plugin["nameAscii"] = plugin["name"].encode('ascii', 'ignore').decode('ascii')
		return plugin

	def install_plugin_from_file(self, name=None, id=None, version=None):
		files = filedialog.askopenfilenames(parent=self, filetypes = (("Plugins", "*.jar"), ("All files", "*.*")))
		for s in self.servers:
			dir = os.path.join(s["dir"], "plugins")
			plugins = [f for f in os.listdir(dir) if os.path.isfile(os.path.join(dir, f))]
			for p in files:
				similarity = {}
				for i in plugins:
					if len(i.rsplit("-", maxsplit=2)) == 3:
						ratio = similar(os.path.basename(p), i.rsplit("-", maxsplit=2)[0] + i[i.rindex("."):])
					else:
						ratio = similar(os.path.basename(p), i)
					print(p, i, ratio)
					if ratio > 0.6:
						similarity[ratio] = i
				list_keys = list(similarity.keys())
				list_keys.sort(reverse=True)
				if list_keys:
					old_plugin = similarity[list_keys[0]]
					log.info("Found old plugin " + old_plugin + " on server dir " + s["dir"] + ", replacing")
					os.remove(os.path.join(dir, old_plugin))
				if name and id and version:
					shutil.copy(p, os.path.join(dir, name + "-" + str(id) + "-" + str(version) + p[p.rindex("."):]))
				else:
					shutil.copy(p, dir)


class Plugin(tk.Tk):
	def __init__(self, plugin, servers, install_plugin_from_file_func):
		log.debug("Loading plugin " + plugin["name"])
		super().__init__()
		self.plugin = json.loads(requests.get("https://api.spiget.org/v2/resources/" + str(plugin["id"])).text)
		self.plugin["nameAscii"] = plugin["nameAscii"]
		self.servers = servers
		self.install_plugin_from_file = install_plugin_from_file_func
		self.title(plugin["name"])
		tk.Label(self, text=self.plugin["name"], font=("Free Avant Garde", 24)).grid(column=0, row=0)
		self.tag_lbl = tk.Label(self, text=self.plugin["tag"])
		self.tag_lbl.grid(column=0, row=1)
		self.dates_topbar = tk.Frame(self)
		self.dates_topbar.grid(column=0, row=2)
		tk.Label(self.dates_topbar, text="Update date: " + plugin["updateDateFormatted"]).grid(column=0, row=0)
		tk.Label(self.dates_topbar, text="Release date: " + plugin["releaseDateFormatted"]).grid(column=1, row=0)
		if not self.plugin["external"]: tk.Label(self.dates_topbar, text="Size: " + str(plugin["file"]["size"]) + plugin["file"]["sizeUnit"]).grid(column=2, row=0)
		self.sec_topbar = tk.Frame(self)
		self.sec_topbar.grid(column=0, row=3)
		all_servers_supported = True
		for s in self.servers:
			if not [v for v in plugin["testedVersions"] if s["version"].startswith(v)]:
				all_servers_supported = False
				break
		if all_servers_supported:
			tk.Label(self.sec_topbar, text="Supported versions: " + " ".join(plugin["testedVersions"])).grid(column=0, row=0)
		else:
			tk.Label(self.sec_topbar, text="Supported versions: " + " ".join(plugin["testedVersions"]), bg="Red").grid(column=0, row=0)
		self.btns_topbar = tk.Frame(self)
		self.btns_topbar.grid(column=0, row=4)
		tk.Button(self.btns_topbar, text="Translate", command=self.desc_translate).grid(column=0, row=0)
		tk.Button(self.btns_topbar, text="Original", command=self.open_original).grid(column=1, row=0)
		self.desc = scrolledtext.ScrolledText(self, width=100)
		self.desc.insert("insert", self.parse_desc(base64.b64decode(self.plugin["description"])))
		self.desc["state"] = "disabled"
		self.desc.grid(column=0, row=5)
		self.name_pattern = plugin["nameAscii"].replace("/", "|") + "-" + str(self.plugin["id"]) + "-"
		self.load()
		self.bind("<Return>", lambda e, p=self.plugin: log.debug("Plugin data: " + str(p)))
		self.mainloop()

	def parse_desc(self, desc):
		def del_tag(text, tag):
			try:
				tag_index = text.index(tag)
				tag_end_index = text[tag_index:].index(">") + tag_index + 1
				text = text[:tag_index] + text[tag_end_index:]
			except ValueError:
				return text
			else:
				return del_tag(text, tag)

		def parse_urls(text):
			try:
				a_index = text.index("<a ")
				a_href_index = text[a_index:].index('href="') + a_index + 6
				a_href_end_index = text[a_href_index:].index('"') + a_href_index
				a_end_index = text[a_href_end_index:].index("</a>") + a_href_end_index + 4
				link = text[:a_href_end_index][a_href_index:]
				text = text[:a_index] + link + text[a_end_index:]
			except ValueError:
				return text
			else:
				return parse_urls(text)

		desc = desc.decode("utf-8", "ignore")
		desc = desc.replace("<br>", "\n")
		desc = desc.replace("<b>", "")
		desc = desc.replace("</b>", "")
		desc = desc.replace("<i>", "")
		desc = desc.replace("</i>", "")
		desc = desc.replace("</span>", "")
		desc = desc.replace("&nbsp;", " ")
		desc = desc.replace("&lt;", "<")
		desc = desc.replace("&gt;", ">")
		desc = desc.replace("</div>", "")
		desc = desc.replace("<li>", "•")
		desc = desc.replace("</li>", "")
		desc = desc.replace("<ul>", "")
		desc = desc.replace("</ul>", "")
		desc = desc.replace("&amp;", "&")
		desc = desc.replace("<ol>", "")
		desc = desc.replace("</ol>", "")
		splited = desc.split("\n")
		i = 0
		for line in splited:
			line = del_tag(line, "<span")
			line = del_tag(line, "<div")
			line = del_tag(line, "<img")
			line = parse_urls(line)
			splited[i] = line
			i += 1
		desc = "\n".join(splited)
		return desc

	def update_plugin(self):
		self.remove_plugin()
		self.install_plugin()
		log.info("Plugin " + self.plugin["name"] + " successfully updated")
		self.load()

	def install_plugin(self):
		if self.plugin["external"]:
			messagebox.showinfo("External install",
								"You will be directed to the site from which you will have to download the plugin and select it")
			webbrowser.open_new_tab(self.plugin["file"]["externalUrl"])
			self.install_plugin_from_file(self.plugin["nameAscii"], self.plugin["id"], self.plugin["versions"][0]["id"])
		else:
			data = requests.get(
				"https://api.spiget.org/v2/resources/{0}/download".format(str(self.plugin["id"]))).content
			for s in self.servers:
				with open(os.path.join(s["dir"], "plugins",
									   self.name_pattern + str(self.plugin["versions"][0]["id"]) + self.plugin["file"][
										   "type"]), "wb") as f:
					f.write(data)
			self.load()

	def remove_plugin(self):
		for s in self.servers:
			for file in os.listdir(os.path.join(s["dir"], "plugins")):
				if file.startswith(self.name_pattern):
					log.info("Deleting plugin file " + file)
					os.remove(os.path.join(s["dir"], "plugins", file))
		self.load()

	def load(self):
		installed_versions = []
		for s in self.servers: installed_versions += [
			int(i[len(self.name_pattern):0 - len(self.plugin["file"]["type"])]) for i in
			os.listdir(os.path.join(s["dir"], "plugins")) if i.startswith(self.name_pattern)]
		if installed_versions:
			if installed_versions[0] < self.plugin["versions"][0]["id"]:
				self.update_btn = tk.Button(self, text="Update", bg="green", command=self.update_plugin)
				self.update_btn.grid(column=1, row=4)
			else:
				self.version_lbl = tk.Label(self, text="Latest version installed")
				self.version_lbl.grid(column=1, row=4)
			self.remove_btn = tk.Button(self, text="Remove", command=self.remove_plugin)
			self.remove_btn.grid(column=1, row=5)
		else:
			self.install_btn = tk.Button(self, text="Install", command=self.install_plugin)
			self.install_btn.grid(column=1, row=4)

	def desc_translate(self):
		def translate_desc():
			self.desc["state"] = "normal"
			text = self.desc.get(1.0, "end")
			self.desc.delete(1.0, "end")
			self.desc.insert("insert", translate(text, entry.get()))
			self.desc["state"] = "disabled"
			self.tag_lbl["text"] = translate(self.tag_lbl["text"], entry.get())
			lang_entry.destroy()

		lang_entry = tk.Tk()
		lang_entry.title("Language")
		entry = tk.Entry(lang_entry)
		entry.grid(column=0, row=0)
		btn = tk.Button(lang_entry, text="Translate", command=translate_desc)
		btn.grid(column=1, row=0)
		lang_entry.mainloop()

	def open_original(self):
		webbrowser.open_new_tab("https://spigotmc.org/resources/" + str(self.plugin["id"]))


def similar(a, b): return SequenceMatcher(None, a, b).ratio()


log.basicConfig(level=log.DEBUG, format="%(name)s - %(levelname)s - %(message)s")