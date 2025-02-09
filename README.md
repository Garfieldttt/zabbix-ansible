# Zabbix-Ansible
![Zabbix](https://img.shields.io/badge/Zabbix-7.0%2B-blue) ![License](https://img.shields.io/badge/License-GPLv3-blue.svg)

## Notice
This template is designed for use with the **Zabbix Agent (active)**.

# The `template_app_ansible` includes:

| Item                     | Description                                                                 |
|--------------------------|-----------------------------------------------------------------------------|
| **failed-tasks**         | Number of failed tasks.                                                    |
| **last-executed-playbook** | Name of the last executed playbook.                                        |
| **last-run**             | Timestamp of the last playbook run.                                        |
| **skipped-tasks**        | Number of skipped tasks.                                                   |
| **success-tasks**        | Number of successful tasks.                                                |
| **task-status**          | Status of the last task (e.g., success, failed, unreachable).              |
| **unreachable**          | Number of unreachable tasks.                                               |



This repository combines a Zabbix template with a minimal Ansible callback plugin to present Ansible output in a compact JSON format.

---

## Prerequisites

- **Ansible** should already be installed.
- Zabbix Server 7.0 or higher.

---

## Installation & Setup
**Note:** The Ansible user must have write permissions to the file `/var/log/ansible.log`. If this is not the case, adjust the permissions as needed with the following commands:
1. **Create the Ansible log file and set permissions:**

   ```bash
   sudo touch /var/log/ansible.log
   sudo chmod 744 /var/log/ansible.log
   sudo chown $(whoami) /var/log/ansible.log

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

## Trigger Toggle Macros  

The following macros are used to control the activation of triggers in Zabbix:  

| Macro | Description |
|--------|-------------|
| `{$ANSIBLE_TRIGGER_TOGGLE_JOB:"{#ANSIBLE_HOSTNAME}"}=1` | Checks a host-specific macro value to toggle the job-related trigger. |
| `{$ANSIBLE_TRIGGER_TOGGLE_UNREACHABLE:"{#ANSIBLE_HOSTNAME}"}=1` | Checks a host-specific macro value to toggle the unreachable trigger. |

### Macro Requirements  
The macros must have the value `1` to activate the corresponding trigger:  

- `{$ANSIBLE_TRIGGER_TOGGLE_JOB:"{#ANSIBLE_HOSTNAME}"}` must be set to `1` for job-related triggers.  
- `{$ANSIBLE_TRIGGER_TOGGLE_UNREACHABLE:"{#ANSIBLE_HOSTNAME}"}` must be set to `1` for unreachable triggers.  

### Functionality  
These macros allow toggling the respective triggers:  
- If the macro value is `1`, the trigger is **activated**.  
- If the macro value is `0`, the trigger is **deactivated**.  

---

## Installation & Setup  
1. Ensure **Ansible** is installed and configured.  
2. Configure the required macros in your **Zabbix template**.  
3. Apply the template to monitored hosts in **Zabbix Server 7.0+**.  

---

This setup ensures better control over **job and unreachable state monitoring** in **Zabbix-Ansible integration**.

