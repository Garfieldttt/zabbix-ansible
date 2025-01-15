from datetime import datetime
from ansible.plugins.callback import CallbackBase
import json
import os

class CallbackModule(CallbackBase):
    """
    Aggregiertes Callback-Plugin:
      - Lädt beim Start vorhandene Daten aus dem Logfile.
      - Hält pro Host kumulative Erfolg/Fehl/Skip/Unreachable-Zähler.
      - Holt sich bei v2_playbook_on_stats() die finalen Zahlen aus stats.summarize(host),
        so dass garantiert "offline" Hosts als unreachable auftauchen, wenn Ansible sie
        auch wirklich als unreachable erkannt hat.
      - Schreibt den Gesamtstatus am Ende in eine JSON-Datei.
    """

    CALLBACK_VERSION = 2.0
    CALLBACK_TYPE = 'stdout'
    CALLBACK_NAME = 'aggregated_success_failures'

    def __init__(self):
        super(CallbackModule, self).__init__()
        self.log_file = os.environ.get('ANSIBLE_LOG_FILE', '/var/log/ansible.log')
        self.host_results = {}
        self.job_name = None
        self._load_existing_results()

    def _load_existing_results(self):
        """
        Lädt bestehende Ergebnisse aus der Logdatei, falls vorhanden,
        und führt sie in self.host_results zusammen.
        """
        if os.path.exists(self.log_file):
            try:
                with open(self.log_file, 'r') as f:
                    existing_data = json.load(f)
                    # existing_data wird als Liste von Dicts erwartet
                    for entry in existing_data:
                        host = entry["host"]
                        self.host_results[host] = {
                            "success_tasks": entry.get("success_tasks", 0),
                            "failed_tasks": entry.get("failed_tasks", 0),
                            "skipped_tasks": entry.get("skipped_tasks", 0),
                            "unreachable": entry.get("unreachable", False),
                            "job_name": entry.get("job_name", None),
                            "last_run": entry.get("last_run", None)
                        }
            except Exception as e:
                self._display.warning(
                    f"Could not load existing log file {self.log_file}: {e}"
                )

    def _ensure_host_entry(self, host):
        """
        Legt einen neuen Eintrag in self.host_results an, falls nicht vorhanden.
        """
        if host not in self.host_results:
            self.host_results[host] = {
                "success_tasks": 0,
                "failed_tasks": 0,
                "skipped_tasks": 0,
                "unreachable": False,
                "job_name": None,
                "last_run": None
            }

    def v2_playbook_on_start(self, playbook):
        """
        Wird aufgerufen, wenn das Playbook startet.
        - Merkt sich den Playbook-Namen.
        - Sorgt dafür, dass alle Inventory-Hosts bereits in self.host_results stehen.
        """
        self.job_name = playbook._file_name
        inventory_manager = getattr(playbook, 'inventory_manager', None)
        if inventory_manager:
            all_hosts = inventory_manager.get_hosts()
            for host_obj in all_hosts:
                self._ensure_host_entry(host_obj.name)

    def v2_playbook_on_stats(self, stats):
        """
        Wird aufgerufen, wenn das Playbook beendet ist.
        Hier nehmen wir die finalen Zahlen direkt aus dem Stats-Objekt, sodass 
        unreachable-Hosts auch wirklich als unreachable auftauchen.
        """
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # stats.processed enthält alle Hosts, die Ansible kennt (und zu verarbeiten versucht hat).
        for host in stats.processed:
            self._ensure_host_entry(host)

            # Hole dir die "Endstats" von Ansible
            summary = stats.summarize(host)
            # summary ist z.B. { "ok": ..., "failures": ..., "unreachable": ..., "skipped": ..., "rescued": 0, "ignored": 0 }

            # Kumulative Zählung (alte + neue Werte)
            self.host_results[host]["success_tasks"] += summary["ok"]
            self.host_results[host]["failed_tasks"] += summary["failures"]
            self.host_results[host]["skipped_tasks"] += summary["skipped"]
            
            # Falls unreachable > 0, dann ist der Host wirklich unreachable
            if summary["unreachable"] > 0:
                self.host_results[host]["unreachable"] = True
            else:
                # Ansonsten ggf. wieder auf False setzen (wenn Host diesmal erreichbar war)
                # Nur wenn du das möchtest!
                self.host_results[host]["unreachable"] = False

            # Speichere job_name / last_run (immer oder nur, wenn summary != 0)
            self.host_results[host]["job_name"] = self.job_name
            self.host_results[host]["last_run"] = now_str

        # Jetzt bestimmen wir den "status" pro Host. 
        # Du kannst ihn auch beim Schreiben in die Ausgabe kalkulieren.
        output = []
        for host, results in self.host_results.items():
            # Beispiel-Logik (wie bisher): 
            # Falls 'failed_tasks' > 0 und es gibt gleichzeitig "einige" success_tasks -> 
            #   -> "vergiss" die Fehler (lösche sie oder lass sie stehen, je nach Gusto).
            if results["failed_tasks"] > 0 and results["success_tasks"] > 0:
                results["failed_tasks"] = 0

            # Finaler Status
            if results["failed_tasks"] == 0 and not results["unreachable"]:
                status = "success"
            elif results["unreachable"]:
                status = "unreachable"
            else:
                status = "failed"

            # Zusammenbauen für das finale JSON
            output.append({
                "host": host,
                "status": status,
                "success_tasks": results["success_tasks"],
                "failed_tasks": results["failed_tasks"],
                "skipped_tasks": results["skipped_tasks"],
                "unreachable": results["unreachable"],
                "job_name": results["job_name"],
                "last_run": results["last_run"]
            })

        # Schreibe Endergebnis in die Logdatei
        try:
            with open(self.log_file, 'w') as f:
                json.dump(output, f, indent=2)
            self._display.display(f"Results written to {self.log_file}")
        except Exception as e:
            self._display.warning(f"Could not write to log file {self.log_file}: {e}")

        # Optional: Auf stdout ausgeben
        print(json.dumps(output, indent=2))
