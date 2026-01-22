### Troubleshooting and Resolving Database Privilege Issue for Data Import in Frappe/ERPNext

The following documents the sequence of steps taken to diagnose and resolve a privilege issue preventing data imports from processing in a Frappe/ERPNext setup running in Docker containers. The issue manifested as pending data imports and "Access denied" errors in logs for the database user associated with the site `uat-gvsv2.hashiraworks.com`. Each step includes the command executed (if applicable), the context, and the relevant output.

#### Step 1: Access the Host and Enter the Backend Container
- **Command**: `docker exec -it frappe-hrms-backend-1 bash`
- **Context**: Enter the Frappe backend container to inspect sites and configurations.
- **Output**:
  ```
  frappe@f39322e6d282:~/frappe-bench$
  ```

#### Step 2: List Site Directory Contents
- **Command**: `ls -la sites/`
- **Context**: Verify the sites present in the Frappe bench.
- **Output**:
  ```
  total 36
  drwxr-xr-x 5 frappe frappe 4096 Jan 21 13:20 .
  drwxr-xr-x 1 frappe frappe 4096 Jan 21 12:45 ..
  -rw-r--r-- 1 frappe frappe 707 Jan 21 13:17 apps.json
  -rw-r--r-- 1 frappe frappe 19 Jan 21 13:17 apps.txt
  drwxr-xr-x 5 frappe frappe 4096 Jan 21 13:07 assets
  -rw-r--r-- 1 frappe frappe 269 Jan 21 13:19 common_site_config.json
  drwxr-xr-x 6 frappe frappe 4096 Jan 21 13:20 uat-gvsv2.hashiraworks.com
  drwxr-xr-x 6 frappe frappe 4096 Jan 21 13:08 uat-pwv2.hashiraworks.com
  ```

#### Step 3: Check Pending Jobs for Sites
- **Commands**:
  - `bench --site uat-gvsv2.hashiraworks.com show-pending-jobs`
  - `bench --site uat-pwv2.hashiraworks.com show-pending-jobs`
- **Context**: Identify if there are pending background jobs, which could include data imports.
- **Output**:
  ```
  -----Pending Jobs-----
  -----Pending Jobs-----
  ```

#### Step 4: Enter Frappe Console for Site and Query Recent Data Imports
- **Command**: `bench --site uat-gvsv2.hashiraworks.com console`
- **Context**: Use IPython console to query the database for recent Data Import documents and check their status.
- **Input in Console**:
  ```
  import frappe
  frappe.connect(site='uat-gvsv2.hashiraworks.com')

  # Get recent Data Import attempts
  data_imports = frappe.get_all('Data Import',
  fields=['name', 'status', 'import_type', 'creation', 'reference_doctype'],
  order_by='creation desc',
  limit=5)

  for d in data_imports:
  print(f"\n{d.name}: {d.status}")
  # Get detailed info
  doc = frappe.get_doc('Data Import', d.name)
  if hasattr(doc, 'template_warnings'):
  print(f" Warnings: {doc.template_warnings}")
  if hasattr(doc, 'import_log'):
  print(f" Log: {doc.import_log[:200] if doc.import_log else 'None'}")
  ```
- **Output**:
  ```
  User Import on 2026-01-21 22:46:19.012142: Pending
    Warnings:
  Employee Import on 2026-01-21 18:55:15.963527: Pending
    Warnings:
  ```

#### Step 5: Attempt to Check Logs in Console (Failed Due to Syntax Error)
- **Input in Console**:
  ```
  # Check which site is failing and look at its logs
  tail -50 sites/uat-gvsv2.hashiraworks.com/logs/worker.error.log
  tail -50 sites/uat-pwv2.hashiraworks.com/logs/worker.error.log

  # Also check scheduler logs
  tail -50 sites/uat-gvsv2.hashiraworks.com/logs/scheduler.log
  tail -50 sites/uat-pwv2.hashiraworks.com/logs/scheduler.log
  ```
- **Output**:
  ```
  Cell In[2], line 2
    tail -50 sites/uat-gvsv2.hashiraworks.com/logs/worker.error.log
             ^
  SyntaxError: invalid syntax
  ```
- **Context**: Attempted shell commands in Python console; failed as they are not Python syntax.

#### Step 6: Exit Console and Check Logs Directly
- **Command**: `exit()`
- **Context**: Exit the console to run shell commands.
- **Commands**:
  - `tail -50 sites/uat-gvsv2.hashiraworks.com/logs/worker.error.log`
  - `tail -50 sites/uat-pwv2.hashiraworks.com/logs/worker.error.log`
  - `tail -50 sites/uat-gvsv2.hashiraworks.com/logs/scheduler.log`
  - `tail -50 sites/uat-pwv2.hashiraworks.com/logs/scheduler.log`
- **Output**:
  ```
  tail: cannot open 'sites/uat-gvsv2.hashiraworks.com/logs/worker.error.log' for reading: No such file or directory
  tail: cannot open 'sites/uat-pwv2.hashiraworks.com/logs/worker.error.log' for reading: No such file or directory
  File "/home/frappe/frappe-bench/apps/frappe/frappe/database/mariadb/mysqlclient.py", line 109, in get_connection
    conn = self._get_connection()
  File "/home/frappe/frappe-bench/apps/frappe/frappe/database/mariadb/mysqlclient.py", line 114, in _get_connection
    return self.create_connection()
           ~~~~~~~~~~~~~~~~~~~~~~^^
  File "/home/frappe/frappe-bench/apps/frappe/frappe/database/mariadb/mysqlclient.py", line 117, in create_connection
    return MySQLdb.connect(**self.get_connection_settings())
           ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/frappe/frappe-bench/env/lib/python3.14/site-packages/MySQLdb/__init__.py", line 121, in Connect
    return Connection(*args, **kwargs)
  File "/home/frappe/frappe-bench/env/lib/python3.14/site-packages/MySQLdb/connections.py", line 200, in __init__
    super().__init__(*args, **kwargs2)
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^
  MySQLdb.OperationalError: (1045, "Access denied for user '_dd426f9fff6a3c18'@'172.18.0.9' (using password: YES)")
  2026-01-22 05:00:00,233 ERROR scheduler Exception in Enqueue Events for Site uat-gvsv2.hashiraworks.com
  Traceback (most recent call last):
    File "/home/frappe/frappe-bench/apps/frappe/frappe/utils/scheduler.py", line 120, in enqueue_events_for_site
      enqueue_events()
      ~~~~~~~~~~~~~~^^
    File "/home/frappe/frappe-bench/apps/frappe/frappe/utils/scheduler.py", line 135, in enqueue_events
      all_jobs = frappe.get_all("Scheduled Job Type", filters={"stopped": 0}, fields="*")
    File "/home/frappe/frappe-bench/apps/frappe/frappe/__init__.py", line 1382, in get_all
      return get_list(doctype, *args, **kwargs)
    File "/home/frappe/frappe-bench/apps/frappe/frappe/__init__.py", line 1357, in get_list
      return frappe.model.qb_query.DatabaseQuery(doctype).execute(*args, **kwargs)
             ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^
    File "/home/frappe/frappe-bench/apps/frappe/frappe/model/qb_query.py", line 212, in execute
      result = query.run(debug=debug, as_dict=not as_list, update=update)
    File "/home/frappe/frappe-bench/apps/frappe/frappe/query_builder/utils.py", line 131, in execute_query
      result = frappe.local.db.sql(query, params, *args, **kwargs) # nosemgrep
    File "/home/frappe/frappe-bench/apps/frappe/frappe/database/database.py", line 249, in sql
      self.connect()
      ~~~~~~~~~~~~^^
    File "/home/frappe/frappe-bench/apps/frappe/frappe/database/database.py", line 147, in connect
      self.get_connection()
      ~~~~~~~~~~~~~~~~~~~^^
    File "/home/frappe/frappe-bench/apps/frappe/frappe/database/mariadb/mysqlclient.py", line 109, in get_connection
      conn = self._get_connection()
    File "/home/frappe/frappe-bench/apps/frappe/frappe/database/mariadb/mysqlclient.py", line 114, in _get_connection
      return self.create_connection()
             ~~~~~~~~~~~~~~~~~~~~~~^^
    File "/home/frappe/frappe-bench/apps/frappe/frappe/database/mariadb/mysqlclient.py", line 117, in create_connection
      return MySQLdb.connect(**self.get_connection_settings())
             ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    File "/home/frappe/frappe-bench/env/lib/python3.14/site-packages/MySQLdb/__init__.py", line 121, in Connect
      return Connection(*args, **kwargs)
    File "/home/frappe/frappe-bench/env/lib/python3.14/site-packages/MySQLdb/connections.py", line 200, in __init__
      super().__init__(*args, **kwargs2)
      ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^
  MySQLdb.OperationalError: (1045, "Access denied for user '_dd426f9fff6a3c18'@'172.18.0.9' (using password: YES)")
  ```
- **Key Insight**: Logs reveal access denied errors for user `_dd426f9fff6a3c18` from host `172.18.0.9`, indicating a privilege issue.

#### Step 7: View Site Configuration Files
- **Commands**:
  - `cat sites/uat-gvsv2.hashiraworks.com/site_config.json`
  - `cat sites/uat-pwv2.hashiraworks.com/site_config.json`
- **Context**: Confirm database credentials for the sites.
- **Output** (for uat-gvsv2):
  ```
  {
   "db_name": "_dd426f9fff6a3c18",
   "db_password": "dSlux8gSb1tzBZW4",
   "db_type": "mariadb",
   "db_user": "_dd426f9fff6a3c18",
   "user_type_doctype_limit": {
    "employee_self_service": 40
   }
  }
  ```
- **Output** (for uat-pwv2):
  ```
  {
   "db_name": "_1d7c009cc8b0abe5",
   "db_password": "5i5rDSOf3ZHp23iz",
   "db_type": "mariadb",
   "db_user": "_1d7c009cc8b0abe5",
   "user_type_doctype_limit": {
    "employee_self_service": 40
   }
  }
  ```

#### Step 8: Exit Backend Container and Enter Database Container
- **Command**: `exit`
- **Context**: Return to host.
- **Command**: `docker exec -it frappe-hrms-db-1 mariadb -u root -p`
- **Context**: Enter MariaDB as root (password prompted but not shown).
- **Output**:
  ```
  Welcome to the MariaDB monitor. Commands end with ; or \g.
  Your MariaDB connection id is 26423
  Server version: 11.8.5-MariaDB-ubu2404 mariadb.org binary distribution
  Copyright (c) 2000, 2018, Oracle, MariaDB Corporation Ab and others.
  Type 'help;' or '\h' for help. Type '\c' to clear the current input statement.
  ```

#### Step 9: Verify Database Existence
- **Command**: `SHOW DATABASES LIKE '%dd426f9fff6a3c18%';`
- **Context**: Confirm the database for the affected site exists.
- **Output**:
  ```
  +-------------------------------+
  | Database (%dd426f9fff6a3c18%) |
  +-------------------------------+
  | _dd426f9fff6a3c18 |
  +-------------------------------+
  1 row in set (0.000 sec)
  ```

#### Step 10: Check Existing User Privileges
- **Command**: `SELECT User, Host FROM mysql.user WHERE User = '_dd426f9fff6a3c18';`
- **Context**: Inspect hosts allowed for the database user.
- **Output**:
  ```
  +-------------------+------------+
  | User | Host |
  +-------------------+------------+
  | _dd426f9fff6a3c18 | 172.18.0.6 |
  +-------------------+------------+
  1 row in set (0.001 sec)
  ```
- **Key Insight**: User is only granted for host `172.18.0.6`, but errors show attempts from `172.18.0.9`.

#### Step 11: Grant Privileges to Allow Access from Any Host
- **Command**: `GRANT ALL PRIVILEGES ON `_dd426f9fff6a3c18`.* TO '_dd426f9fff6a3c18'@'%' IDENTIFIED BY 'dSlux8gSb1tzBZW4';`
- **Context**: Extend privileges to allow connections from any host (`%` wildcard).
- **Output**:
  ```
  Query OK, 0 rows affected (0.018 sec)
  ```

#### Step 12: Flush Privileges
- **Command**: `FLUSH PRIVILEGES;`
- **Context**: Apply the privilege changes immediately.
- **Output**:
  ```
  Query OK, 0 rows affected (0.000 sec)
  ```

#### Step 13: Verify Updated User Privileges
- **Command**: `SELECT User, Host FROM mysql.user WHERE User = '_dd426f9fff6a3c18';`
- **Context**: Confirm the new host entry.
- **Output**:
  ```
  +-------------------+------------+
  | User | Host |
  +-------------------+------------+
  | _dd426f9fff6a3c18 | % |
  | _dd426f9fff6a3c18 | 172.18.0.6 |
  +-------------------+------------+
  2 rows in set (0.001 sec)
  ```

#### Step 14: Exit Database Shell
- **Command**: `exit`
- **Output**:
  ```
  Bye
  ```

#### Step 15: Re-enter Backend Container and Test Database Connection
- **Command**: `docker exec -it frappe-hrms-backend-1 bash`
- **Command**: `bench --site uat-gvsv2.hashiraworks.com console`
- **Input in Console**:
  ```
  import frappe
  frappe.connect(site='uat-gvsv2.hashiraworks.com')
  frappe.db.sql("SELECT 1")
  ```
- **Output**:
  ```
  Out[1]: ((1,),)
  ```
- **Context**: Verify database connectivity after privilege fix.

#### Step 16: Clear Cache for the Site
- **Command**: `bench --site uat-gvsv2.hashiraworks.com clear-cache`
- **Context**: Ensure any cached configurations are refreshed.

#### Step 17: Re-check Pending Data Imports
- **Command**: `bench --site uat-gvsv2.hashiraworks.com console`
- **Input in Console**:
  ```
  import frappe
  frappe.connect(site='uat-gvsv2.hashiraworks.com')

  # Check the pending imports
  data_imports = frappe.get_all('Data Import',
  fields=['name', 'status', 'import_type', 'creation'],
  order_by='creation desc',
  limit=5)

  for d in data_imports:
  print(f"{d.name}: {d.status}")
  ```
- **Output**:
  ```
  User Import on 2026-01-21 22:46:19.012142: Pending
  Employee Import on 2026-01-21 18:55:15.963527: Pending
  ```

#### Step 18: Exit Console (Typo in Transcript: "xit" Command Failed)
- **Command**: `xit` (failed), then `exit`
- **Output**:
  ```
  bash: xit: command not found
  ```

#### Step 19: Edit Compose File (Optional/Inspection)
- **Command**: `nano frappe-hrms-compose.yml`
- **Context**: Potentially inspect or edit the Docker Compose file, but no changes shown.

#### Step 20: Restart Queue and Scheduler Services
- **Command**: `docker compose -f frappe-hrms-compose.yml restart queue-long queue-short scheduler`
- **Context**: Restart background workers to pick up changes and process pending jobs.
- **Output**:
  ```
  [+] restart 0/3
   ⠴ Container frappe-hrms-scheduler-1 Restarting 10.5s
   ⠴ Container frappe-hrms-queue-long-1 Restarting 10.5s
   ⠴ Container frappe-hrms-queue-short-1 Restarting 10.5s
  ```

#### Step 21: Re-enter Backend Container and Check Pending Jobs
- **Command**: `docker exec -it frappe-hrms-backend-1 bash`
- **Command**: `bench --site uat-gvsv2.hashiraworks.com show-pending-jobs`
- **Output**:
  ```
  -----Pending Jobs-----
  ```

#### Step 22: Re-check Data Import Status
- **Command**: `bench --site uat-gvsv2.hashiraworks.com console`
- **Input in Console**:
  ```
  import frappe
  frappe.connect(site='uat-gvsv2.hashiraworks.com')

  data_imports = frappe.get_all('Data Import',
  fields=['name', 'status', 'import_type', 'creation'],
  order_by='creation desc',
  limit=5)

  for d in data_imports:
  print(f"{d.name}: {d.status}")
  ```
- **Output**:
  ```
  User Import on 2026-01-21 22:46:19.012142: Pending
  Employee Import on 2026-01-21 18:55:15.963527: Pending
  ```

#### Step 23: Manually Trigger a Pending Import
- **Input in Console**:
  ```
  # Get one of the imports
  doc = frappe.get_doc('Data Import', 'User Import on 2026-01-21 22:46:19.012142')

  # Try to start the import
  doc.start_import()
  frappe.db.commit()

  print("Import triggered. Check status in a few seconds...")
  exit()
  ```
- **Output**:
  ```
  Import triggered. Check status in a few seconds...
  ```

#### Step 24: Verify Import Completion
- **Command**: `bench --site uat-gvsv2.hashiraworks.com console`
- **Input in Console**:
  ```
  import frappe
  frappe.connect(site='uat-gvsv2.hashiraworks.com')

  doc = frappe.get_doc('Data Import', 'User Import on 2026-01-21 22:46:19.012142')
  print(f"Status: {doc.status}")
  ```
- **Output**:
  ```
  Status: Success
  ```

#### Step 25: Exit Container
- **Command**: `exit`

This sequence resolved the privilege issue by granting broader host access to the database user, refreshing services, and manually triggering the import. Data imports transitioned from "Pending" to "Success" after these steps.
