## Server Scripts Enabling : 

```bash
# Access the backend container
docker exec -it frappe-backend-1 bash
```

```bash
# View the site configuration
frappe@bf5ec259fba5:~/frappe-bench$ cat sites/uat-pw.hashiraworks.com/site_config.json
```

```bash
bench set-config -g server_script_enabled 1
```

```bash
# Enable server scripts for the site
bench --site uat-pw.hashiraworks.com set-config server_script_enabled true
```

```bash
# Verify the change in site configuration
cat sites/uat-pw.hashiraworks.com/site_config.json
```
