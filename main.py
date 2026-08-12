import sublime # type: ignore
import sublime_plugin # type: ignore 

from .codetime import CodeTimeClient, CodeTimeError

# Currently CodeTime Error: {} <- The error message is showing json object and need to show the error title only eg,.Token Error, Network Error.
# If CodeTime settings file is forcefully removed, the token is still loaded in memory.
# Some redudent peices of code which needs to be removed.

class CodeTimeSetTokenCommand(sublime_plugin.ApplicationCommand):
    def run(self):
        def on_done(token):
            settings = sublime.load_settings("CodeTime.sublime-settings")
            settings.set("CODETIME_TOKEN", token)
            sublime.save_settings("CodeTime.sublime-settings")
            sublime.message_dialog("CodeTime: Token saved")

        sublime.active_window().show_input_panel(
            "CodeTime Token:",
            "",
            on_done,
            None,
            None
        )

class CodeTime(sublime_plugin.EventListener):
    def __init__(self):
        settings = sublime.load_settings("CodeTime.sublime-settings")
        token = settings.get("CODETIME_TOKEN", "")
        self.client = CodeTimeClient(token=token) if token else None
        self._status = self.get_status()
        self._pending_status = None
        self.update()

    def get_status(self):
        if self.client:
            try:
                minutes = self.client.get_total_minutes()
                hours = minutes // 60
                mins = minutes % 60
                return "%dh %dm" % (hours, mins)
            except CodeTimeError as e:
                return "CodeTime Error: %s" % str(e)
            except Exception as e:
                return "CodeTime Error: %s" % str(e)

        return "CodeTime Error: Not Initialized"

    def _apply_status(self):
        if self._pending_status is not None:
            self._status = self._pending_status
            self._pending_status = None
            for window in sublime.windows():
                for view in window.views():
                    view.set_status("codetime", self._status)

    def _fetch_status(self):
        def callback():
            self._pending_status = self.get_status()
            sublime.set_timeout(self._apply_status, 0)
        sublime.set_timeout_async(callback, 0)

    def update(self):
        self._fetch_status()
        sublime.set_timeout(self.update, 60000)

    def on_activated(self, view):
        view.set_status("codetime", self._status)

    def on_load(self, view):
        view.set_status("codetime", self._status)

    def on_new(self, view):
        view.set_status("codetime", self._status)

    def on_close(self, view):
        view.erase_status("codetime")