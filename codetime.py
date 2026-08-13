import json
import urllib.request
import urllib.error
import platform

from .events import (
    ACTIVATE_FILE_CHANGED,
    CHANGE_EDITOR_SELECTION,
    CHANGE_EDITOR_VISIBLE_RANGES,
    EDITOR_CHANGED,
    FILE_CREATED,
    FILE_EDITED,
    FILE_ADDED_LINE,
    FILE_REMOVED,
    FILE_SAVED,
)

class CodeTimeError(Exception):
    def __init__(self, message, status_code=None, body=None):
        super(CodeTimeError, self).__init__(message)
        self.status_code = status_code
        self.body = body

class CodeTimeAuthError(CodeTimeError):
    pass

class CodeTimeClient(object):
    def __init__(self, token, base_url="https://api.codetime.dev", timeout=30):
        self.token = token
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _log(self, message):
        print("[CodeTime] " + message)

    def _request(self, method, path, body=None, query=None):
        url = self.base_url + path
        if query:
            qs = "&".join("%s=%s" % (k, urllib.request.quote(str(v))) for k, v in query.items())
            url = url + "?" + qs

        headers = {
            "Authorization": "Bearer " + self.token,
            "User-Agent": "CodeTime Client",
            "Accept": "application/json",
        }

        data = None
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
            headers["Content-Length"] = str(len(data))

        req = urllib.request.Request(url, data=data, headers=headers, method=method)

        self._log("%s %s" % (method, url))
        if body is not None:
            self._log("Body: %s" % json.dumps(body))

        try:
            response = urllib.request.urlopen(req, timeout=self.timeout)
            try:
                response_body = response.read().decode("utf-8")
                self._log("Response %d: %s" % (response.getcode(), response_body[:200]))
                if response_body:
                    return json.loads(response_body)
                return {}
            finally:
                response.close()

        except urllib.error.HTTPError as e:
            body_text = e.read().decode("utf-8") if e.fp else ""
            self._log("HTTP Error %d: %s" % (e.code, body_text))
            if e.code == 401:
                raise CodeTimeAuthError("Authentication failed: " + body_text, e.code, body_text)
            raise CodeTimeError("HTTP %d: %s" % (e.code, body_text), e.code, body_text)

        except urllib.error.URLError as e:
            self._log("Network Error: " + str(e.reason))
            raise CodeTimeError("Network error: " + str(e.reason))

    def send_event(
        self,
        project,
        language,
        relative_file,
        absolute_file,
        event_type,
        editor="Sublime Text 4",
        git_origin=None,
        git_branch=None,
        event_time=None,
    ):
        operation_type = self._get_operation_type(event_type)

        if event_time is None:
            import time as _time
            event_time = int(_time.time() * 1000)

        payload = {
            "project": project,
            "language": language,
            "relativeFile": relative_file,
            "absoluteFile": absolute_file,
            "editor": editor,
            "platform": platform.system(),
            "eventTime": event_time,
            "eventType": event_type,
            "platformArch": platform.machine(),
            "gitOrigin": git_origin or "",
            "gitBranch": git_branch or "",
            "operationType": operation_type,
        }

        self._log("Body: %s" % json.dumps(payload))
        return self._request("POST", "/v3/users/event-log", body=payload)

    def _get_operation_type(self, event_type):
        if event_type in (FILE_CREATED, FILE_EDITED, FILE_ADDED_LINE, FILE_REMOVED, FILE_SAVED):
            return "write"
        return "read"

    def get_minutes(self, minutes=1440):
        return self._request("GET", "/v3/users/self/minutes", query={"minutes": str(minutes)})

    def get_today_minutes(self):
        result = self.get_minutes(minutes=1440)
        return result.get("minutes", 0)

    def get_total_minutes(self):
        result = self.get_minutes(minutes=52560000)
        return result.get("minutes", 0)