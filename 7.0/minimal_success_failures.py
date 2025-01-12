from datetime import datetime
from ansible.plugins.callback import CallbackBase
import json
import os

class CallbackModule(CallbackBase):
    """
    Ein Callback-Plugin, das Erfolge, Fehlschläge und unerreichbare Hosts pro Host aggregiert,
    sowie den Job-Namen und den Zeitpunkt der letzten Ausführung hinzufügt.
    """

    CALLBACK_VERSION = 2.0
    CALLBACK_TYPE = 'stdout'
    CALLBACK_NAME = 'aggregated_success_failures'

    def __init__(self):
        super(CallbackModule, self).__init__()
        self.host_results = {}
        self.log_file = os.environ.get('ANSIBLE_LOG_FILE', '/var/log/ansible.log')
        self.job_name = None  # Speichert den Job-Namen
        self.last_run = None  # Speichert den Zeitpunkt der letzten Ausführung
        self._load_existing_results()

    def _load_existing_results(self):
        """
        Lädt bestehende Ergebnisse aus der Logdatei, falls vorhanden.
        """
        if os.path.exists(self.log_file):
            try:
                with open(self.log_file, 'r') as f:
                    existing_data = json.load(f)
                    for entry in existing_data:
                        self.host_results[entry["host"]] = {
                            "success_tasks": entry.get("success_tasks", 0),
                            "failed_tasks": entry.get("failed_tasks", 0),
                            "skipped_tasks": entry.get("skipped_tasks", 0),
                            "unreachable": entry.get("unreachable", False),
                            "job_name": entry.get("job_name", None),
                            "last_run": entry.get("last_run", None)
                        }
            except Exception as e:
                self._display.warning(f"Could not load existing log file {self.log_file}: {e}")

    def _ensure_host_entry(self, host):
        if host not in self.host_results:
            self.host_results[host] = {
                "success_tasks": 0,
                "failed_tasks": 0,
                "skipped_tasks": 0,
                "unreachable": False,
                "job_name": None,
                "last_run": None
            }

    def v2_runner_on_ok(self, result):
        host = result._host.get_name()
        self._ensure_host_entry(host)
        self.host_results[host]["success_tasks"] += 1

        # Verbindung war erfolgreich, setze "unreachable" auf False
        self.host_results[host]["unreachable"] = False

    def v2_runner_on_failed(self, result, ignore_errors=False):
        host = result._host.get_name()
        self._ensure_host_entry(host)

        # Prüfe, ob es sich um eine Warnung handelt (keine echte Task-Fehlermeldung)
        if result._result.get("_ansible_no_log", False):
            self._display.warning(f"Ignoring warning for host {host}: {result._result}")
            return

        # Prüfe auf Systemfehler (z. B. fehlender Interpreter oder Exception)
        if not result._task or "exception" in result._result or "module_stderr" in result._result:
            self._display.warning(f"Ignoring system-level error for host {host}")
            return

        # Nur echte Task-Fehler zählen
        self.host_results[host]["failed_tasks"] += 1

    def v2_runner_on_unreachable(self, result):
        # Behandle "unreachable"-Meldungen separat
        host = result._host.get_name()
        self._ensure_host_entry(host)
        self.host_results[host]["unreachable"] = True

    def v2_runner_on_skipped(self, result):
        host = result._host.get_name()
        self._ensure_host_entry(host)
        self.host_results[host]["skipped_tasks"] += 1

    def v2_playbook_on_start(self, playbook):
        """
        Diese Methode wird aufgerufen, wenn das Playbook gestartet wird.
        """
        self.job_name = playbook._file_name  # Speichert den Namen des Playbooks

    def v2_playbook_on_stats(self, stats):
        # Setze den Zeitpunkt der letzten Ausführung
        self.last_run = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        output = []
        for host, results in self.host_results.items():
            # Falls Tasks erfolgreich waren, ist der Host nicht "unreachable"
            if results["success_tasks"] > 0:
                results["unreachable"] = False

            if results["failed_tasks"] > 0:
                status = "failed"
            elif results["unreachable"]:
                status = "unreachable"
            else:
                status = "success"

            output.append({
                "host": host,
                "status": status,
                "success_tasks": results["success_tasks"],
                "failed_tasks": results["failed_tasks"],
                "skipped_tasks": results["skipped_tasks"],
                "unreachable": results["unreachable"],
                "job_name": self.job_name,
                "last_run": self.last_run
            })

        # Schreibe die konsolidierten Ergebnisse in die Log-Datei
        try:
            with open(self.log_file, 'w') as f:
                json.dump(output, f, indent=2)
                self._display.display(f"Results written to {self.log_file}")
        except Exception as e:
            self._display.warning(f"Could not write to log file {self.log_file}: {e}")

        # Optional: Auch auf stdout ausgeben
        print(json.dumps(output, indent=2))
