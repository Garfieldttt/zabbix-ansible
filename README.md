# Zabbix-Ansible
![Zabbix](https://img.shields.io/badge/Zabbix-7.0%2B-blue) ![License](https://img.shields.io/badge/license-MIT-green)

This repository combines a Zabbix template with a minimal Ansible callback plugin to present Ansible output in a compact JSON format.

---

## Prerequisites

- **Ansible** should already be installed.
- Zabbix Server 7.0 or higher.

---

## Installation & Setup

1. **Create the Ansible log file and set permissions:**

   ```bash
   sudo touch /var/log/ansible.log
   sudo chmod 744 /var/log/ansible.log

2. **Create the callback directory:**

   ```bash
   mkdir -p ~/.ansible/plugins/callback

3. **Modify the Ansible configuration:**

   ```bash
   nano ~/.ansible.cfg

**Add or update the following in your ~/.ansible.cfg:**

   ```bash
[defaults]
callback_plugins = ~/.ansible/plugins/callback
stdout_callback = minimal_success_failures
   ```

4. **Clone the repository and copy the callback plugin:**

   ```bash
   cd /tmp/
   git clone https://github.com/Garfieldttt/zabbix-ansible
   cd /tmp/zabbix-ansible/7.0/ && cp minimal_success_failures.py ~/.ansible/plugins/callback/

