from ansible.plugins.callback import CallbackBase
import json
import os

class CallbackModule(CallbackBase):
    """
    Ein Callback-Plugin, das Erfolge, Fehlschläge und unerreichbare Hosts pro Host aggregiert und im JSON-Format in eine Log-Datei schreibt.
    """

    CALLBACK_VERSION = 2.0
    CALLBACK_TYPE = 'stdout'
    CALLBACK_NAME = 'aggregated_success_failures'

    def __init__(self):
        super(CallbackModule, self).__init__()
        self.host_results = {}
        self.log_file = os.environ.get('ANSIBLE_LOG_FILE', '/var/log/ansible.log')
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

    def v2_playbook_on_stats(self, stats):
        output = []
        for host, results in self.host_results.items():
            if results["unreachable"]:
                status = "unreachable"
            elif results["failed_tasks"] > 0:
                status = "failed"
            else:
                status = "success"

            output.append({
                "host": host,
                "status": status,
                "success_tasks": results["success_tasks"],
                "failed_tasks": results["failed_tasks"],
                "skipped_tasks": results["skipped_tasks"],
                "unreachable": results["unreachable"]
            })

        # Schreibe die konsolidierten Ergebnisse in die Log-Datei
        try:
            with open(self.log_file, 'w') as f:
                json.dump(output, f, indent=2)
        except Exception as e:
            self._display.warning(f"Could not write to log file {self.log_file}: {e}")

        # Optional: Auch auf stdout ausgeben
        print(json.dumps(output, indent=2))
