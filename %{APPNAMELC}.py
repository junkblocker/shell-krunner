#!/usr/bin/python3
"""A Plasma runner for markdown files."""

import subprocess
from contextlib import suppress
from pathlib import Path

import dbus.service
# import q
from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import GLib

DBusGMainLoop(set_as_default=True)

objpath = "/runner"  # Default value for X-Plasma-DBusRunner-Path metadata property
iface = "org.kde.krunner1"


class Runner(dbus.service.Object):
    def __init__(self):
        dbus.service.Object.__init__(
            self,
            dbus.service.BusName("org.kde.%{APPNAMELC}", dbus.SessionBus()),
            objpath,
        )
        # read config match_*** functions """
        self.config = f"{Path.home()}/.config/krunnershell.sh"
        self.actions = ()
        self.prefix = ""
        self.size = 0
        self.loadConfig()

    def loadConfig(self):
        self.actions = ()
        self.prefix = ""
        self.size = 0
        if not Path(self.config).exists():
            with open(self.config, "w") as file_out:
                cmd = r"cmds=($(set | awk -F'_| ' '/^match_.*\(\)/ {print $2}'));echo 'keys:' ${cmds[@]}"
                _ = file_out.write(
                    "\nmatch_about(){\n\t" + cmd + "\n\tuname -smrn\n}\n"
                )
        with suppress(FileNotFoundError):
            with open(self.config) as file_in:
                for line in file_in:
                    if line.startswith("match_"):
                        name = line[6:].rsplit("(", 1)[0]
                        if name:
                            self.actions += (name,)
            self.size = Path(self.config).stat().st_size
            print(self.actions)

    @dbus.service.method(iface, in_signature="s", out_signature="a(sssida{sv})")
    def Match(self, query: str):
        """get the matches and returns a packages list"""
        self.prefix = ""
        query = query.strip().lower()

        try:
            if self.size != Path(self.config).stat().st_size:
                self.loadConfig()
        except FileNotFoundError:
            self.loadConfig()

        # print(f"match: {query}...")
        if not self.actions or not ":" in query:
            return []

        # TEST plugin without datas
        # return [tuple([n, n, "", 32, 0.5, {"subtext": ""}]) for n in self.actions]

        self.prefix = query.split(":", 1)[0].replace(" ", "_")
        if self.prefix not in self.actions:
            return []
        query = query[len(self.prefix) + 1 :].strip()

        out, _ = subprocess.Popen(
            f"bash -c 'source {self.config} && match_{self.prefix} \"{query}\"'",
            shell=True,
            text=True,
            stdout=subprocess.PIPE,
        ).communicate()
        # print(f"stdout cmd: match_{self.prefix} \"{query}\" : {out}")

        ret = []
        rel = 1
        for node in out.splitlines():
            if (
                "||" in node
            ):  # if title != to run, split line and set [0] in data(link) and [1] in titre
                data = node.split("||", 2)
                for _ in range(len(data), 3):
                    data.append("")
            else:
                data = [node, node, ""]
            ret.append(tuple([data[0], data[1], "", 32, rel, {"subtext": data[2]}]))
            rel = rel - 0.02

        return ret

    @dbus.service.method(iface, in_signature="ss")
    def Run(self, data: str, _action_id: str):
        """click on item, run command"""
        subprocess.Popen(
            f"bash -c 'source {self.config} && run_{self.prefix} {data}'", shell=True
        ).pid


runner = Runner()
loop = GLib.MainLoop()
loop.run()
