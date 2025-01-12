from ansible.plugins.callback import CallbackBase
import json
import os
from datetime import datetime


class CallbackModule(CallbackBase):
    """
    Ein Callback-Plugin, das Host-Statistiken aggregiert und im JSON-Format in eine Log-Datei schreibt.
    Zusätzliche Felder `playbook_name` und `last_run` werden für jeden Host-Eintrag hinzugefügt.
    """

    CALLBACK_VERSION = 2.0
    CALLBACK_TYPE = 'stdout'
    CALLBACK_NAME = 'minimal_success_failures'

    def __init__(self):
        super(CallbackModule, self).__init__()
        self.host_results = {}
        self.log_file = os.environ.get('ANSIBLE_LOG_FILE', '/var/log/ansible.log')
        self.playbook_name = None
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
                            "unreachable": entry.get("unreachable", False)
                        }
            except Exception as e:
                self._display.warning(f"Could not load existing log file {self.log_file}: {e}")

    def set_playbook_name(self, playbook_name):
        """
        Setzt den Playbook-Namen für die Ausgabe.
        """
        self.playbook_name = playbook_name

    def _ensure_host_entry(self, host):
        if host not in self.host_results:
            self.host_results[host] = {
                "success_tasks": 0,
                "failed_tasks": 0,
                "skipped_tasks": 0,
                "unreachable": False
            }

    def v2_runner_on_ok(self, result):
        host = result._host.get_name()
        self._ensure_host_entry(host)
        self.host_results[host]["success_tasks"] += 1

    def v2_runner_on_failed(self, result, ignore_errors=False):
        host = result._host.get_name()
        self._ensure_host_entry(host)
        self.host_results[host]["failed_tasks"] += 1

    def v2_runner_on_unreachable(self, result):
        host = result._host.get_name()
        self._ensure_host_entry(host)
        self.host_results[host]["unreachable"] = True

    def v2_runner_on_skipped(self, result):
        host = result._host.get_name()
        self._ensure_host_entry(host)
        self.host_results[host]["skipped_tasks"] += 1

    def v2_playbook_on_start(self, playbook):
        """
        Wird aufgerufen, wenn ein Playbook gestartet wird.
        Speichert den Playbook-Namen.
        """
        self.set_playbook_name(playbook._file_name)

    def v2_playbook_on_stats(self, stats):
        last_run_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        output = []
        for host, results in self.host_results.items():
            if results["unreachable"]:
                status = "unreachable"
            elif results["failed_tasks"] > 0:
                status = "failed"
            else:
                status = "success"

            # Host-spezifischer Eintrag mit geänderter Reihenfolge
            output.append({
                "host": host,
                "status": status,
                "success_tasks": results["success_tasks"],
                "failed_tasks": results["failed_tasks"],
                "skipped_tasks": results["skipped_tasks"],
                "unreachable": results["unreachable"],
                "playbook_name": self.playbook_name,
                "last_run": last_run_time
            })

        # Schreibe die konsolidierten Ergebnisse in die Log-Datei
        try:
            with open(self.log_file, 'w') as f:
                json.dump(output, f, indent=2)
        except Exception as e:
            self._display.warning(f"Could not write to log file {self.log_file}: {e}")

        # Optional: Auch auf stdout ausgeben
        print(json.dumps(output, indent=2))
