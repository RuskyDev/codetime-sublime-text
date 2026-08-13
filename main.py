import sublime # type: ignore
import sublime_plugin # type: ignore

from .codetime import CodeTimeClient, CodeTimeError

class CodeTimeSetTokenCommand(sublime_plugin.ApplicationCommand):
    def run(self):
        def on_done(token):
            settings = sublime.load_settings("CodeTime.sublime-settings")
            settings.set("CODETIME_TOKEN", token)
            sublime.save_settings("CodeTime.sublime-settings")
            sublime.message_dialog("CodeTime: Token saved")
            if CodeTime.instance:
                CodeTime.instance.refresh()

        sublime.active_window().show_input_panel(
            "CodeTime Token:",
            "",
            on_done,
            None,
            None
        )

class CodeTime(sublime_plugin.EventListener):
    instance = None

    def __init__(self):
        CodeTime.instance = self
        self._status = "CodeTime: Without Token"
        self._pending_status = None
        self.refresh()

    def _load_token(self):
        settings = sublime.load_settings("CodeTime.sublime-settings")
        return settings.get("CODETIME_TOKEN", "")

    def _get_client(self):
        token = self._load_token()
        if token:
            return CodeTimeClient(token=token)
        return None

    def get_status(self):
        client = self._get_client()
        if not client:
            return "CodeTime: Without Token"
        try:
            minutes = client.get_total_minutes()
            hours = minutes // 60
            mins = minutes % 60
            return "%dh %dm" % (hours, mins)
        except CodeTimeError as e:
            if e.status_code == 401:
                return "CodeTime: Auth Failed"
            return "CodeTime: Network Error"
        except Exception:
            return "CodeTime: Network Error"

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

    def refresh(self):
        self._fetch_status()
        sublime.set_timeout(self.refresh, 60000)

    def on_activated(self, view):
        view.set_status("codetime", self._status)

    def on_load(self, view):
        view.set_status("codetime", self._status)

    def on_new(self, view):
        view.set_status("codetime", self._status)

    def on_close(self, view):
        view.erase_status("codetime")