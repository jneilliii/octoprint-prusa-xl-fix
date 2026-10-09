import json

import octoprint.plugin

from .rewrite import printer_ids, rewrite_command, tool_index


class PrusaXLToolFixPlugin(octoprint.plugin.SettingsPlugin,
                           octoprint.plugin.AssetPlugin,
                           octoprint.plugin.TemplatePlugin):
    def get_settings_defaults(self):
        return dict(tool_index=0, printers=["*"])

    def get_template_configs(self):
        return [dict(type="settings", custom_bindings=True)]

    def get_template_vars(self):
        profiles = self._list_profiles()
        return dict(
            profiles=profiles,
            profiles_json=json.dumps(profiles, separators=(",", ":")),
        )

    def get_assets(self):
        return dict(js=["js/prusaxltoolfix.js"])

    def on_settings_save(self, data):
        validated = {}
        if "tool_index" in data:
            validated["tool_index"] = tool_index(data["tool_index"])
        if "printers" in data:
            validated["printers"] = printer_ids(data["printers"])
        super().on_settings_save(validated)

    def _list_profiles(self):
        manager = getattr(self, "_printer_profile_manager", None)
        if manager is None:
            return []
        try:
            all_profiles = manager.get_all() or {}
        except Exception:
            return []
        profiles = []
        for profile in all_profiles.values():
            if not isinstance(profile, dict):
                continue
            printer_id = profile.get("id")
            if not isinstance(printer_id, str) or not printer_id.strip():
                continue
            printer_id = printer_id.strip()
            name = profile.get("name")
            if not isinstance(name, str) or not name.strip():
                name = printer_id
            profiles.append(dict(id=printer_id, name=name.strip()))
        profiles.sort(key=lambda item: item["name"].lower())
        return profiles

    def _printer_id(self, comm_instance):
        manager = getattr(comm_instance, "_printerProfileManager", None)
        if manager is None:
            manager = getattr(self, "_printer_profile_manager", None)
        if manager is None:
            return None
        try:
            profile = manager.get_current_or_default()
        except Exception:
            return None
        if not isinstance(profile, dict):
            return None
        printer_id = profile.get("id")
        if not isinstance(printer_id, str):
            return None
        printer_id = printer_id.strip()
        return printer_id or None

    def rewrite_queuing(self, comm_instance, phase, cmd, cmd_type, gcode,
                        subcode=None, tags=None, *args, **kwargs):
        if phase != "queuing" or subcode is not None:
            return None
        if gcode is None or gcode.upper() not in ("M106", "M107", "M201", "M203", "M221"):
            return None
        try:
            # Invalid manually edited configuration must not crash the hook.
            selected = printer_ids(self._settings.get(["printers"]))
            tool = tool_index(self._settings.get(["tool_index"]))
        except ValueError:
            return None
        printer_id = self._printer_id(comm_instance)
        if "*" not in selected and printer_id not in selected:
            return None
        rewritten = rewrite_command(cmd, tool)
        if rewritten != cmd:
            self._logger.info(
                "Prusa XL tool workaround for %s: %r -> %r",
                printer_id or "unknown printer",
                cmd,
                rewritten,
            )
            return (rewritten,)
        return None

    def get_update_information(self):
        return dict(
            prusaxltoolfix=dict(
                displayName=__plugin_name__,
                displayVersion=self._plugin_version,
                type="github_release",
                user=GITHUB_USER,
                repo=GITHUB_REPO,
                current=self._plugin_version,
                pip=(
                    f"https://github.com/{GITHUB_USER}/{GITHUB_REPO}/releases/download/"
                    "{target_version}/octoprint_prusaxltoolfix-{target_version}.tar.gz"
                ),
            )
        )


GITHUB_USER = "anuzellig"
GITHUB_REPO = "octoprint-prusa-xl-fix"

__plugin_name__ = "Prusa XL/XL+ fix"
__plugin_description__ = "Add an explicit tool to M106/M107/M201/M203/M221 for the Buddy 6.10.x change."
__plugin_pythoncompat__ = ">=3.9,<4"


def __plugin_load__():
    global __plugin_implementation__, __plugin_hooks__
    __plugin_implementation__ = PrusaXLToolFixPlugin()
    __plugin_hooks__ = {
        "octoprint.comm.protocol.gcode.queuing": __plugin_implementation__.rewrite_queuing,
        "octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information,
    }
