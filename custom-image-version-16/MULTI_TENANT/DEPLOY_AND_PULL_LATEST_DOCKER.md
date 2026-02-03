# 🔄 Frappe HRMS v16 – Upgrade Guide (Multi-Tenant Production)

> **Purpose**: Deploy latest code changes from forked repositories to existing production multi-tenant setup  
> **Scenario**: You have commits in your forks (frappe/erpnext/hrms) that need to be deployed  
> **Sites**: `uat-pwv2.hashiraworks.com`, `uat-gvsv2.hashiraworks.com`

---


## ✅ What We Are Going to Do (BEFORE UPGRADE)

We will:

1. Add a CLI flag: `--no-cache`
2. Pass it into `build_image(...)`
3. Append `--no-cache` to the `docker build` command **only when requested**

That’s it.

---

## 🔧 Patch `easy-install.py` (One-Time Setup)

> ⚠️ **Do this once before running the upgrade steps below**

---

### 1️⃣ Add `--no-cache` flag to the build parser

#### 🔹 Edit `add_build_parser(...)`

Add this **exact block**:

```python
parser.add_argument(
    "--no-cache",
    action="store_true",
    help="Build Docker image without using cache",
)
```

📍 Place it near other build flags (`--push`, `--deploy`, etc.)

---

### 2️⃣ Update `build_image()` signature

#### 🔹 Change this:

```python
def build_image(
    push: bool,
    frappe_path: str,
    frappe_branch: str,
    containerfile_path: str,
    apps_json_path: str,
    tags: List[str],
    python_version: str,
    node_version: str,
):
```

#### ✅ To this:

```python
def build_image(
    push: bool,
    frappe_path: str,
    frappe_branch: str,
    containerfile_path: str,
    apps_json_path: str,
    tags: List[str],
    python_version: str,
    node_version: str,
    no_cache: bool = False,
):
```

---

### 3️⃣ Inject `--no-cache` into the Docker build command

#### 🔹 Find this block:

```python
command = [
    which("docker"),
    "build",
    "--progress=plain",
]
```

#### ✅ Modify it to:

```python
command = [
    which("docker"),
    "build",
    "--progress=plain",
]

if no_cache:
    command.append("--no-cache")
```

✔ Behaviour remains **unchanged** unless `--no-cache` is explicitly passed.

---

### 4️⃣ Pass the flag from `__main__`

#### 🔹 Update the `build_image(...)` call

Change this:

```python
build_image(
    push=args.push,
    frappe_path=args.frappe_path,
    frappe_branch=args.frappe_branch,
    apps_json_path=args.apps_json,
    tags=args.tags,
    containerfile_path=args.containerfile,
    python_version=args.python_version,
    node_version=args.node_version,
)
```

#### ✅ To this:

```python
build_image(
    push=args.push,
    frappe_path=args.frappe_path,
    frappe_branch=args.frappe_branch,
    apps_json_path=args.apps_json,
    tags=args.tags,
    containerfile_path=args.containerfile,
    python_version=args.python_version,
    node_version=args.node_version,
    no_cache=args.no_cache,
)
```

---

### 5️⃣ Final `easy-install.py` (Copy & Replace)

✅ After applying the above steps, your `easy-install.py` is now **final** and ready.

* You can **copy the full updated file**
* Replace the existing `easy-install.py`

```bash
#!/usr/bin/env python3

import argparse
import base64
import logging
import os
import platform
import shutil
import subprocess
import sys
import time
import urllib.request
from shutil import move, unpack_archive, which
from typing import Dict, List

logging.basicConfig(
    filename="easy-install.log",
    filemode="w",
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)


def cprint(*args, level: int = 1):
    """
    logs colorful messages
    level = 1 : RED
    level = 2 : GREEN
    level = 3 : YELLOW

    default level = 1
    """
    CRED = "\033[31m"
    CGRN = "\33[92m"
    CYLW = "\33[93m"
    reset = "\033[0m"
    message = " ".join(map(str, args))
    if level == 1:
        print(CRED, message, reset)
    if level == 2:
        print(CGRN, message, reset)
    if level == 3:
        print(CYLW, message, reset)


def clone_frappe_docker_repo() -> None:
    try:
        urllib.request.urlretrieve(
            "https://github.com/frappe/frappe_docker/archive/refs/heads/main.zip",
            "frappe_docker.zip",
        )
        logging.info("Downloaded frappe_docker zip file from GitHub")
        unpack_archive("frappe_docker.zip", ".")
        # Unzipping the frappe_docker.zip creates a folder "frappe_docker-main"
        move("frappe_docker-main", "frappe_docker")
        logging.info("Unzipped and Renamed frappe_docker")
        os.remove("frappe_docker.zip")
        logging.info("Removed the downloaded zip file")
    except Exception as e:
        logging.error("Download and unzip failed", exc_info=True)
        cprint("\nCloning frappe_docker Failed\n\n", "[ERROR]: ", e, level=1)


def get_from_env(dir, file) -> Dict:
    env_vars = {}
    with open(os.path.join(dir, file)) as f:
        for line in f:
            if line.startswith("#") or not line.strip():
                continue
            key, value = line.strip().split("=", 1)
            env_vars[key] = value
    return env_vars


def write_to_env(
    frappe_docker_dir: str,
    out_file: str,
    sites: List[str],
    db_pass: str,
    admin_pass: str,
    email: str,
    cronstring: str,
    erpnext_version: str = None,
    http_port: str = None,
    custom_image: str = None,
    custom_tag: str = None,
) -> None:
    quoted_sites = ",".join([f"`{site}`" for site in sites]).strip(",")
    example_env = get_from_env(frappe_docker_dir, "example.env")
    erpnext_version = erpnext_version or example_env["ERPNEXT_VERSION"]
    env_file_lines = [
        # defaults to latest version of ERPNext
        f"ERPNEXT_VERSION={erpnext_version}\n",
        f"DB_PASSWORD={db_pass}\n",
        "DB_HOST=db\n",
        "DB_PORT=3306\n",
        "REDIS_CACHE=redis-cache:6379\n",
        "REDIS_QUEUE=redis-queue:6379\n",
        "REDIS_SOCKETIO=redis-socketio:6379\n",
        f"LETSENCRYPT_EMAIL={email}\n",
        f"SITE_ADMIN_PASS={admin_pass}\n",
        f"SITES={quoted_sites}\n",
        "PULL_POLICY=missing\n",
        f'BACKUP_CRONSTRING="{cronstring}"\n',
    ]

    if http_port:
        env_file_lines.append(f"HTTP_PUBLISH_PORT={http_port}\n")

    if custom_image:
        env_file_lines.append(f"CUSTOM_IMAGE={custom_image}\n")

    if custom_tag:
        env_file_lines.append(f"CUSTOM_TAG={custom_tag}\n")

    with open(os.path.join(out_file), "w") as f:
        f.writelines(env_file_lines)


def generate_pass(length: int = 12) -> str:
    """Generate random hash using best available randomness source."""
    import math
    import secrets

    if not length:
        length = 56

    return secrets.token_hex(math.ceil(length / 2))[:length]


def get_frappe_docker_path():
    return os.path.join(os.getcwd(), "frappe_docker")


def check_repo_exists() -> bool:
    return os.path.exists(get_frappe_docker_path())


def start_prod(
    project: str,
    sites: List[str] = [],
    email: str = None,
    cronstring: str = None,
    version: str = None,
    image: str = None,
    is_https: bool = True,
    http_port: str = None,
):
    if not check_repo_exists():
        clone_frappe_docker_repo()
    install_container_runtime()

    compose_file_name = os.path.join(
        os.path.expanduser("~"),
        f"{project}-compose.yml",
    )

    env_file_dir = os.path.expanduser("~")
    env_file_name = f"{project}.env"
    env_file_path = os.path.join(
        os.path.expanduser("~"),
        env_file_name,
    )

    frappe_docker_dir = get_frappe_docker_path()

    cprint(
        f"\nPlease refer to {env_file_path} to know which keys to set\n\n",
        level=3,
    )
    admin_pass = ""
    db_pass = ""
    custom_image = None
    custom_tag = None

    if image:
        custom_image = image
        custom_tag = version

    with open(compose_file_name, "w") as f:
        # Writing to compose file
        if not os.path.exists(env_file_path):
            admin_pass = generate_pass()
            db_pass = generate_pass(9)
            write_to_env(
                frappe_docker_dir=frappe_docker_dir,
                out_file=env_file_path,
                sites=sites,
                db_pass=db_pass,
                admin_pass=admin_pass,
                email=email,
                cronstring=cronstring,
                erpnext_version=version,
                http_port=http_port if not is_https and http_port else None,
                custom_image=custom_image,
                custom_tag=custom_tag,
            )
            cprint(
                "\nA .env file is generated with basic configs. Please edit it to fit to your needs \n",
                level=3,
            )
            with open(
                os.path.join(os.path.expanduser("~"), f"{project}-passwords.txt"), "w"
            ) as en:
                en.writelines(f"ADMINISTRATOR_PASSWORD={admin_pass}\n")
                en.writelines(f"MARIADB_ROOT_PASSWORD={db_pass}\n")
        else:
            env = get_from_env(env_file_dir, env_file_name)
            sites = env["SITES"].replace("`", "").split(",") if env["SITES"] else []
            db_pass = env["DB_PASSWORD"]
            admin_pass = env["SITE_ADMIN_PASS"]
            email = env["LETSENCRYPT_EMAIL"]
            custom_image = env.get("CUSTOM_IMAGE")
            custom_tag = env.get("CUSTOM_TAG")

            version = env.get("ERPNEXT_VERSION", version)
            write_to_env(
                frappe_docker_dir=frappe_docker_dir,
                out_file=env_file_path,
                sites=sites,
                db_pass=db_pass,
                admin_pass=admin_pass,
                email=email,
                cronstring=cronstring,
                erpnext_version=version,
                http_port=http_port if not is_https and http_port else None,
                custom_image=custom_image,
                custom_tag=custom_tag,
            )

        try:
            command = [
                "docker",
                "compose",
                "--project-name",
                project,
                "-f",
                "compose.yaml",
                "-f",
                "overrides/compose.mariadb.yaml",
                "-f",
                "overrides/compose.redis.yaml",
                "-f",
                (
                    "overrides/compose.https.yaml"
                    if is_https
                    else "overrides/compose.noproxy.yaml"
                ),
                "-f",
                "overrides/compose.backup-cron.yaml",
                "--env-file",
                env_file_path,
                "config",
            ]

            subprocess.run(
                command,
                cwd=frappe_docker_dir,
                stdout=f,
                check=True,
            )

        except Exception:
            logging.error("Docker Compose generation failed", exc_info=True)
            cprint("\nGenerating Compose File failed\n")
            sys.exit(1)

    try:
        # Starting with generated compose file
        command = [
            "docker",
            "compose",
            "-p",
            project,
            "-f",
            compose_file_name,
            "up",
            "--force-recreate",
            "--remove-orphans",
            "-d",
        ]
        subprocess.run(
            command,
            check=True,
        )
        logging.info(f"Docker Compose file generated at ~/{project}-compose.yml")

    except Exception as e:
        logging.error("Prod docker-compose failed", exc_info=True)
        cprint(" Docker Compose failed, please check the container logs\n", e)
        sys.exit(1)

    return db_pass, admin_pass


def setup_prod(
    project: str,
    sites: List[str],
    email: str,
    cronstring: str,
    version: str = None,
    image: str = None,
    apps: List[str] = [],
    is_https: bool = False,
    http_port: str = None,
) -> None:
    if len(sites) == 0:
        sites = ["site1.localhost"]

    db_pass, admin_pass = start_prod(
        project=project,
        sites=sites,
        email=email,
        cronstring=cronstring,
        version=version,
        image=image,
        is_https=is_https,
        http_port=http_port,
    )

    for sitename in sites:
        create_site(sitename, project, db_pass, admin_pass, apps)

    cprint(
        f"MariaDB root password is {db_pass}",
        level=2,
    )
    cprint(
        f"Site administrator password is {admin_pass}",
        level=2,
    )
    passwords_file_path = os.path.join(
        os.path.expanduser("~"),
        f"{project}-passwords.txt",
    )
    cprint(f"Passwords are stored in {passwords_file_path}", level=3)


def update_prod(
    project: str,
    version: str = None,
    image: str = None,
    cronstring: str = None,
    is_https: bool = False,
    http_port: str = None,
) -> None:
    start_prod(
        project=project,
        version=version,
        image=image,
        cronstring=cronstring,
        is_https=is_https,
        http_port=http_port,
    )
    migrate_site(project=project)


def setup_dev_instance(project: str):
    if not check_repo_exists():
        clone_frappe_docker_repo()
    install_container_runtime()

    try:
        command = [
            "docker",
            "compose",
            "-f",
            "devcontainer-example/docker-compose.yml",
            "--project-name",
            project,
            "up",
            "-d",
        ]
        subprocess.run(
            command,
            cwd=get_frappe_docker_path(),
            check=True,
        )
        cprint(
            "Please go through the Development Documentation: https://github.com/frappe/frappe_docker/tree/main/docs/development.md to fully complete the setup.",
            level=2,
        )
        logging.info("Development Setup completed")
    except Exception as e:
        logging.error("Dev Environment setup failed", exc_info=True)
        cprint("Setting Up Development Environment Failed\n", e)


def install_docker():
    cprint("Docker is not installed, Installing Docker...", level=3)
    logging.info("Docker not found, installing Docker")
    if platform.system() == "Darwin" or platform.system() == "Windows":
        cprint(
            f"""
            This script doesn't install Docker on {"Mac" if platform.system()=="Darwin" else "Windows"}.

            Please go through the Docker Installation docs for your system and run this script again"""
        )
        logging.debug("Docker setup failed due to platform is not Linux")
        sys.exit(1)
    try:
        ps = subprocess.run(
            ["curl", "-fsSL", "https://get.docker.com"],
            capture_output=True,
            check=True,
        )
        subprocess.run(["/bin/bash"], input=ps.stdout, capture_output=True)
        subprocess.run(
            [
                "sudo",
                "usermod",
                "-aG",
                "docker",
                str(os.getenv("USER")),
            ],
            check=True,
        )
        cprint("Waiting Docker to start", level=3)
        time.sleep(10)
        subprocess.run(
            [
                "sudo",
                "systemctl",
                "restart",
                "docker.service",
            ],
            check=True,
        )
    except Exception as e:
        logging.error("Installing Docker failed", exc_info=True)
        cprint("Failed to Install Docker\n", e)
        cprint("\n Try Installing Docker Manually and re-run this script again\n")
        sys.exit(1)


def install_container_runtime(runtime="docker"):
    if which(runtime) is not None:
        cprint(runtime.title() + " is already installed", level=2)
        return
    if runtime == "docker":
        install_docker()


def create_site(
    sitename: str,
    project: str,
    db_pass: str,
    admin_pass: str,
    apps: List[str] = [],
):
    apps = apps or []
    cprint(f"\nCreating site: {sitename} \n", level=3)
    command = [
        "docker",
        "compose",
        "-p",
        project,
        "exec",
        "backend",
        "bench",
        "new-site",
        "--no-mariadb-socket",
        f"--db-root-password={db_pass}",
        f"--admin-password={admin_pass}",
    ]

    for app in apps:
        command.append("--install-app")
        command.append(app)

    command.append(sitename)

    try:
        subprocess.run(
            command,

            check=True,
        )
        logging.info("New site creation completed")
    except Exception as e:
        logging.error(f"Bench site creation failed for {sitename}", exc_info=True)
        cprint(f"Bench Site creation failed for {sitename}\n", e)


def migrate_site(project: str):
    cprint(f"\nMigrating sites for {project}", level=3)

    exec_command(
        project=project,
        command=[
            "bench",
            "--site",
            "all",
            "migrate",

        ],
    )


def exec_command(project: str, command: List[str] = [], interactive_terminal=False):
    if not command:
        command = ["echo", '"Please execute a command"']

    cprint(f"\nExecuting Command:\n{' '.join(command)}", level=3)
    exec_command = [
        "docker",
        "compose",
        "-p",
        project,
        "exec",
    ]

    if interactive_terminal:
        exec_command.append("-it")

    exec_command.append("backend")
    exec_command += command

    try:
        subprocess.run(
            exec_command,
            check=True,
        )
        logging.info("New site creation completed")
    except Exception as e:

        logging.error(f"Exec command failed for {project}", exc_info=True)
        cprint(f"Exec command failed for {project}\n", e)



def add_project_option(parser: argparse.ArgumentParser):
    parser.add_argument(
        "-n",
        "--project",
        help="Project Name",
        default="frappe",
    )
    return parser


def add_setup_options(parser: argparse.ArgumentParser):
    parser.add_argument(
        "-a",
        "--app",
        dest="apps",
        default=[],
        help="list of app(s) to be installed",
        action="append",
    )
    parser.add_argument(
        "-s",
        "--sitename",
        help="Site Name(s) for your production bench",
        default=[],
        action="append",
        dest="sites",
    )
    parser.add_argument("-e", "--email", help="Add email for the SSL.")

    return parser


def add_common_parser(parser: argparse.ArgumentParser):
    parser = add_project_option(parser)
    parser.add_argument(
        "-g",
        "--backup-schedule",
        help='Backup schedule cronstring, default: "@every 6h"',
        default="@every 6h",
    )
    parser.add_argument("-i", "--image", help="Full Image Name")
    parser.add_argument(
        "-m", "--http-port", help="Http port in case of no-ssl", default="8080"
    )
    parser.add_argument("-q", "--no-ssl", action="store_true", help="No https")
    parser.add_argument(
        "-v",
        "--version",
        help="ERPNext or image version to install, defaults to latest stable",
    )
    parser.add_argument(
        "-l",
        "--force-pull",
        action="store_true",
        help="Force pull frappe_docker",
    )
    return parser


def add_build_parser(subparsers: argparse.ArgumentParser):
    parser = subparsers.add_parser("build", help="Build custom images")
    parser = add_common_parser(parser)
    parser = add_setup_options(parser)
    parser.add_argument(
        "-p",
        "--push",
        help="Push the built image to registry",
        action="store_true",
    )
    parser.add_argument(
        "-r",
        "--frappe-path",
        help="Frappe Repository to use, default: https://github.com/frappe/frappe",
        default="https://github.com/Yaswanth-Vempuluru-7916/frappe",
    )
    parser.add_argument(
        "-b",
        "--frappe-branch",
        help="Frappe branch to use, default: version-15",
        default="version-16",
    )
    parser.add_argument(
        "-j",
        "--apps-json",
        help="Path to apps json, default: frappe_docker/development/apps-example.json",
        default="frappe_docker/development/apps-example.json",
    )
    parser.add_argument(
        "-t",
        "--tag",
        dest="tags",
        help="Full Image Name(s), default: custom-apps:latest",
        action="append",
    )
    parser.add_argument(
        "-c",
        "--containerfile",
        help="Path to Containerfile: images/custom/Containerfile",
        default="images/custom/Containerfile",
    )
    parser.add_argument(
        "-y",
        "--python-version",
        help="Python Version, default: 3.14",
        default="3.14",
    )
    parser.add_argument(
        "-d",
        "--node-version",
        help="NodeJS Version, default: 24.1.0",
        default="24.1.0",
    )
    parser.add_argument(
        "-x",
        "--deploy",
        help="Deploy after build",
        action="store_true",
    )
    parser.add_argument(
        "-u",
        "--upgrade",
        help="Upgrade after build",
        action="store_true",
    )
    parser.add_argument(
    	"--no-cache",
    	action="store_true",
    	help="Build Docker image without using cache",
    )


def add_deploy_parser(subparsers: argparse.ArgumentParser):
    parser = subparsers.add_parser("deploy", help="Deploy using compose")
    parser = add_common_parser(parser)
    parser = add_setup_options(parser)


def add_develop_parser(subparsers: argparse.ArgumentParser):
    parser = subparsers.add_parser("develop", help="Development setup using compose")
    parser.add_argument(
        "-n", "--project", default="frappe", help="Compose project name"
    )


def add_upgrade_parser(subparsers: argparse.ArgumentParser):
    parser = subparsers.add_parser("upgrade", help="Upgrade existing project")
    parser = add_common_parser(parser)


def add_exec_parser(subparsers: argparse.ArgumentParser):
    parser = subparsers.add_parser("exec", help="Exec into existing project")
    parser = add_project_option(parser)


def build_image(
    push: bool,
    frappe_path: str,
    frappe_branch: str,
    containerfile_path: str,
    apps_json_path: str,
    tags: List[str],
    python_version: str,
    node_version: str,
    no_cache: bool = False,
):
    if not check_repo_exists():
        clone_frappe_docker_repo()
    install_container_runtime()

    if not tags:
        tags = ["custom-apps:latest"]

    apps_json_base64 = None
    try:
        with open(apps_json_path, "rb") as file_text:
            file_read = file_text.read()
            apps_json_base64 = (
                base64.encodebytes(file_read).decode("utf-8").replace("\n", "")
            )
    except Exception as e:
        logging.error("Unable to base64 encode apps.json", exc_info=True)
        cprint("\nUnable to base64 encode apps.json\n\n", "[ERROR]: ", e, level=1)

    command = [
        which("docker"),
        "build",
        "--progress=plain",
    ]

    if no_cache :
            cprint("Building Docker image without using cache", level=2)
            command.append("--no-cache")

    for tag in tags:
        command.append(f"--tag={tag}")

    command += [
        f"--file={containerfile_path}",
        f"--build-arg=FRAPPE_PATH={frappe_path}",
        f"--build-arg=FRAPPE_BRANCH={frappe_branch}",
        f"--build-arg=PYTHON_VERSION={python_version}",
        f"--build-arg=NODE_VERSION={node_version}",
        f"--build-arg=APPS_JSON_BASE64={apps_json_base64}",
        ".",
    ]

    try:
        subprocess.run(
            command,
            check=True,
            cwd="frappe_docker",
        )
    except Exception as e:
        logging.error("Image build failed", exc_info=True)
        cprint("\nImage build failed\n\n", "[ERROR]: ", e, level=1)

    if push:
        try:
            for tag in tags:
                subprocess.run(
                    [which("docker"), "push", tag],
                    check=True,
                )
        except Exception as e:
            logging.error("Image push failed", exc_info=True)
            cprint("\nImage push failed\n\n", "[ERROR]: ", e, level=1)


def get_args_parser():
    parser = argparse.ArgumentParser(
        description="Easy install script for Frappe Framework"
    )
    # Setup sub-commands
    subparsers = parser.add_subparsers(dest="subcommand")
    # Build command
    add_build_parser(subparsers)
    # Deploy command
    add_deploy_parser(subparsers)
    # Upgrade command
    add_upgrade_parser(subparsers)
    # Develop command
    add_develop_parser(subparsers)
    # Exec command
    add_exec_parser(subparsers)

    return parser


if __name__ == "__main__":
    parser = get_args_parser()
    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)


    args = parser.parse_args()

    if (
        args.subcommand != "exec"
        and args.force_pull
        and os.path.exists(get_frappe_docker_path())
    ):
        cprint("\nForce pull frappe_docker again\n", level=2)
        shutil.rmtree(get_frappe_docker_path(), ignore_errors=True)

    if args.subcommand == "build":
        build_image(
            push=args.push,
            frappe_path=args.frappe_path,
            frappe_branch=args.frappe_branch,
            apps_json_path=args.apps_json,
            tags=args.tags,
            containerfile_path=args.containerfile,
            python_version=args.python_version,
            node_version=args.node_version,
	    no_cache=args.no_cache,
        )
        if args.deploy:
            setup_prod(
                project=args.project,
                sites=args.sites,
                email=args.email,
                cronstring=args.backup_schedule,
                version=args.version,
                image=args.image,
                apps=args.apps,
                is_https=not args.no_ssl,
                http_port=args.http_port,
            )
        elif args.upgrade:
            update_prod(
                project=args.project,
                version=args.version,
                image=args.image,
                cronstring=args.backup_schedule,
                is_https=not args.no_ssl,
                http_port=args.http_port,
            )

    elif args.subcommand == "deploy":
        cprint("\nSetting Up Production Instance\n", level=2)
        logging.info("Running Production Setup")
        if args.email and "example.com" in args.email:
            cprint("Emails with example.com not acceptable", level=1)
            sys.exit(1)
        setup_prod(
            project=args.project,
            sites=args.sites,
            email=args.email,
            version=args.version,
            cronstring=args.backup_schedule,
            image=args.image,
            apps=args.apps,
            is_https=not args.no_ssl,
            http_port=args.http_port,
        )
    elif args.subcommand == "develop":
        cprint("\nSetting Up Development Instance\n", level=2)
        logging.info("Running Development Setup")
        setup_dev_instance(args.project)
    elif args.subcommand == "upgrade":
        cprint("\nUpgrading Production Instance\n", level=2)
        logging.info("Upgrading Development Setup")
        update_prod(
            project=args.project,
            version=args.version,
            image=args.image,
            is_https=not args.no_ssl,
            cronstring=args.backup_schedule,
            http_port=args.http_port,
        )
    elif args.subcommand == "exec":
        cprint(f"\nExec into {args.project} backend\n", level=2)
        logging.info(f"Exec into {args.project} backend")
        exec_command(
            project=args.project,
            command=["bash"],
            interactive_terminal=True,
        )
```

---

## 📋 Prerequisites

- ✅ Running multi-tenant Frappe HRMS v16 setup
- ✅ Custom Docker image: `yaswanth1679/frappe-hrms-erpnext:version-16`
- ✅ Latest commits pushed to your forked repositories
- ✅ `apps.json` file pointing to your forks
- ✅ Docker Hub login configured

---

## 🛡️ Pre-Upgrade Safety Step: Mark Current Image as Stable (Rollback Ready)

> **Purpose**: Always keep a known-good image before building or deploying a new one
> This allows **instant rollback** if the new image has a critical bug.

---

### ✅ Step A: Tag the Currently Running Image as `stable`

Before building a **new image**, tag the **currently running image** as stable.

```bash
# Mark current version as stable
docker tag \
  yaswanth1679/frappe-hrms-erpnext:version-16 \
  yaswanth1679/frappe-hrms-erpnext:16.0.0-stable
```

---

### ✅ Step B: Push Stable Image to Docker Hub

```bash
# Push stable image to Docker Hub
docker push yaswanth1679/frappe-hrms-erpnext:16.0.0-stable
```

✔ This guarantees:

* A **known working image** is always available
* Rollback does **not** depend on rebuilding
* Production recovery is fast and safe

---

## 🎯 Upgrade Overview

The upgrade process involves:
1. **Rebuild** Docker image with latest code from your forks
2. **Verify** the new image contains your changes
3. **Deploy** the updated image
4. **Migrate** all sites to apply schema/code changes
5. **Fix** Traefik routing if needed
6. **Verify** sites are working

---

## 📝 Step-by-Step Upgrade Process

### Step 1: Rebuild Docker Image with Latest Code

This pulls fresh code from your GitHub forks and builds a new image.

```bash
python3 easy-install.py build \
  --apps-json apps.json \
  --containerfile images/custom/Containerfile \
  --tag yaswanth1679/frappe-hrms-erpnext:version-16 \
  --no-cache \
  --push
```

**What happens:**
- Clones latest commits from your forked repos specified in `apps.json`
- Builds new Docker image with updated code
- Pushes image to Docker Hub

**Expected output:**
```
#15 exporting to image
#15 writing image sha256:786801383d95...
#15 DONE 13.0s
The push refers to repository [docker.io/yaswanth1679/frappe-hrms-erpnext]
version-16: digest: sha256:be0bb120c616... size: 2207
```

---

### Step 2: Stop Running Containers (Preserve Data)

```bash
docker compose -f frappe-hrms-erpnext-compose.yml down
```

**⚠️ CRITICAL:** 
- **NO `-v` flag** - This preserves your volumes (database, sites, Redis data)
- Only containers are stopped, data remains intact

**Expected output:**
```
[+] down 13/13
 ✔ Container frappe-hrms-erpnext-proxy-1        Removed
 ✔ Container frappe-hrms-erpnext-frontend-1     Removed
 ...
```

---

### Step 3: Pull Updated Image

```bash
docker pull yaswanth1679/frappe-hrms-erpnext:version-16
```

**Expected output:**
```
version-16: Pulling from yaswanth1679/frappe-hrms-erpnext
Digest: sha256:be0bb120c61608115b916e67777788e4b7ace099e58303d934ef38612af81d4c
Status: Image is up to date for yaswanth1679/frappe-hrms-erpnext:version-16
```

---

### Step 4: Verify Image Contains Latest Code

#### 4a. Check Image Build Timestamp

```bash
docker image inspect yaswanth1679/frappe-hrms-erpnext:version-16 --format='{{.Created}}'
```

**Expected output:**
```
2026-02-03T05:33:15.382053268+01:00
```

The timestamp should be **recent** (within the last few minutes).

---

#### 4b. Verify Specific Code Changes (Optional but Recommended)

Check if your specific code modifications are present in the image:

```bash
docker run --rm yaswanth1679/frappe-hrms-erpnext:version-16 bash -c "
grep -A 10 'def throw_overlap_error(self, d)' /home/frappe/frappe-bench/apps/hrms/hrms/hr/doctype/leave_application/leave_application.py
"
```

**Expected output (example):**
```python
def throw_overlap_error(self, d):
    msg = _("Employee {0} has already applied for {1} between {2} and {3}").format(
        self.employee, d["leave_type"], formatdate(d["from_date"]), formatdate(d["to_date"])
    )
    frappe.throw(msg, OverlapError)
```

Replace the function name with something you actually modified to confirm your changes are present.

---

##  Update Image Tag in Compose File

Before starting containers (or when rolling back), **ensure the compose file points to the stable image**.

### ✅ Update image tag in compose file

```bash
sed -i \
  's|yaswanth1679/frappe-hrms-erpnext:OLD_TAG|yaswanth1679/frappe-hrms-erpnext:NEW_TAG|g' \
  frappe-hrms-erpnext-compose.yml
```

---

### ✅ Verify Change

```bash
grep yaswanth1679/frappe-hrms-erpnext frappe-hrms-erpnext-compose.yml
```

**Expected output:**

```
yaswanth1679/frappe-hrms-erpnext:NEW_TAG
```

---

### Step 5: Start Containers with Updated Image

```bash
docker compose -f frappe-hrms-erpnext-compose.yml up -d
```

**Expected output:**
```
[+] up 13/13
 ✔ Network frappe-hrms-erpnext_default          Created
 ✔ Container frappe-hrms-erpnext-db-1           Healthy
 ✔ Container frappe-hrms-erpnext-configurator-1 Exited
 ...
```

---

### Step 6: Wait for Containers to Initialize

```bash
sleep 30
```

This gives containers time to fully start.

---

### Step 7: Verify Container Status

```bash
docker compose -f frappe-hrms-erpnext-compose.yml ps
```

**All containers should show `Up` status:**
```
NAME                                STATUS
frappe-hrms-erpnext-backend-1       Up 40 seconds
frappe-hrms-erpnext-frontend-1      Up 39 seconds
frappe-hrms-erpnext-db-1            Up 51 seconds (healthy)
...
```

---

### Step 8: Migrate Sites (CRITICAL - Applies Code Changes)

#### 8a. Migrate First Site

```bash
docker exec -it frappe-hrms-erpnext-backend-1 bench --site uat-pwv2.hashiraworks.com migrate
```

**Expected output:**
```
Migrating uat-pwv2.hashiraworks.com
Updating DocTypes for frappe        : [========================================] 100%
Updating DocTypes for erpnext       : [========================================] 100%
Updating DocTypes for hrms          : [========================================] 100%
Executing frappe.patches...
...
Queued rebuilding of search index for uat-pwv2.hashiraworks.com
```

---

#### 8b. Migrate Second Site

```bash
docker exec -it frappe-hrms-erpnext-backend-1 bench --site uat-gvsv2.hashiraworks.com migrate
```

**Expected output:**
```
Migrating uat-gvsv2.hashiraworks.com
Updating DocTypes for frappe        : [========================================] 100%
...
Queued rebuilding of search index for uat-gvsv2.hashiraworks.com
```

**⚠️ Why migrate is critical:**
- Applies database schema changes
- Runs patches from new code
- Updates DocTypes and metadata
- **Without migration, code changes won't take effect**

---

### Step 9: Clear Cache for Both Sites

#### 9a. Clear Cache - First Site

```bash
docker exec -it frappe-hrms-erpnext-backend-1 bench --site uat-pwv2.hashiraworks.com clear-cache
```

#### 9b. Clear Cache - Second Site

```bash
docker exec -it frappe-hrms-erpnext-backend-1 bench --site uat-gvsv2.hashiraworks.com clear-cache
```

**Purpose:**
- Clears Python bytecode cache
- Clears Redis cache
- Ensures new code is loaded fresh

---

### Step 10: Restart Critical Services

```bash
docker compose -f frappe-hrms-erpnext-compose.yml restart backend queue-long queue-short scheduler websocket
```

**Expected output:**
```
[+] restart 5/5
 ✔ Container frappe-hrms-erpnext-queue-short-1 Restarted
 ✔ Container frappe-hrms-erpnext-websocket-1   Restarted
 ✔ Container frappe-hrms-erpnext-queue-long-1  Restarted
 ✔ Container frappe-hrms-erpnext-backend-1     Restarted
 ✔ Container frappe-hrms-erpnext-scheduler-1   Restarted
```

**Why restart:**
- Reloads Python code in worker processes
- Ensures all services use new code
- Clears any in-memory state

---

### Step 11: Verify Deployment Health

#### 11a. Check First Site

```bash
docker exec -it frappe-hrms-erpnext-backend-1 bench --site uat-pwv2.hashiraworks.com doctor
```

**Expected output:**
```
-----Checking scheduler status-----
Workers online: 2
-----uat-pwv2.hashiraworks.com Jobs-----
```

#### 11b. Check Second Site

```bash
docker exec -it frappe-hrms-erpnext-backend-1 bench --site uat-gvsv2.hashiraworks.com doctor
```

**Expected output:**
```
-----Checking scheduler status-----
Workers online: 2
-----uat-gvsv2.hashiraworks.com Jobs-----
```

---

### Step 12: Verify Code is Deployed (Final Check)

```bash
docker exec -it frappe-hrms-erpnext-backend-1 bash -c "
grep -A 5 'def throw_overlap_error(self, d)' /home/frappe/frappe-bench/apps/hrms/hrms/hr/doctype/leave_application/leave_application.py
"
```

**Expected:** Your modified code should appear here.

---

## 🔧 Troubleshooting: Fix Traefik Routing (If Needed)

### Symptom: Internal Server Error on Sites

If you get **500 Internal Server Error** when accessing sites, check Traefik configuration.

---

### Issue: Corrupted Host Rule

The Traefik rule might be corrupted:

**Incorrect:**
```yaml
traefik.http.routers.frontend-http.rule: Hostuat-pwv2.hashiraworks.comuat-gvsv2.hashiraworks.com)
```

**Correct:**
```yaml
traefik.http.routers.frontend-http.rule: HostRegexp(`{host:.+}`)
```

---

### Fix Steps

#### 1. Stop Containers

```bash
docker compose -f frappe-hrms-erpnext-compose.yml down
```

---

#### 2. Edit Compose File

```bash
nano frappe-hrms-erpnext-compose.yml
```

Find the `frontend` service → `labels` section → Change to:

```yaml
  traefik.http.routers.frontend-http.rule: HostRegexp(`{host:.+}`)
```
---

#### 3. Verify Fix

```bash
grep "traefik.http.routers.frontend-http.rule" frappe-hrms-erpnext-compose.yml
```

**Expected output:**
```yaml
traefik.http.routers.frontend-http.rule: HostRegexp(`{host:.+}`)
```

---

#### 4. Restart Containers

```bash
docker compose -f frappe-hrms-erpnext-compose.yml up -d
```

---

#### 5. Enable DNS Multitenant (If Not Already Set)

```bash
docker exec -it frappe-hrms-erpnext-backend-1 bash
```

Inside container:

```bash
# Check current setting
cat sites/common_site_config.json | grep dns_multitenant

# Enable if not set
bench config dns_multitenant on

# Verify
cat sites/common_site_config.json | grep dns_multitenant

exit
```

**Expected in `common_site_config.json`:**
```json
{
  "dns_multitenant": true
}
```

---

#### 6. Test Sites

```bash
curl -I https://uat-pwv2.hashiraworks.com
curl -I https://uat-gvsv2.hashiraworks.com
```

**Expected response:**
```
HTTP/2 200
```

Or open in browser:
- `https://uat-pwv2.hashiraworks.com`
- `https://uat-gvsv2.hashiraworks.com`

---


## 🔧 Troubleshooting: Fix **502 Bad Gateway** (Traefik + Cloudflare)

### Symptom

After upgrade / rollback / image change, sites show:

* **Browser**: `502 Bad Gateway`
* **Cloudflare** error page
* Containers are **UP**
* `bench doctor` is **healthy**

---

### 🔍 How to Confirm It’s a Gateway Issue

Run this from your local machine or server:

#### ❌ When site is **BROKEN** (Bad Gateway)

```bash
curl -I https://uat-gvsv2.hashiraworks.com
```

**Output:**

```
HTTP/2 502
date: Tue, 03 Feb 2026 08:22:43 GMT
content-type: text/plain; charset=UTF-8
content-length: 15
cache-control: private, max-age=0, no-store, no-cache, must-revalidate, post-check=0, pre-check=0
expires: Thu, 01 Jan 1970 00:00:01 GMT
referrer-policy: same-origin
x-frame-options: SAMEORIGIN
server: cloudflare
cf-ray: 9c8085a4288e3b01-BOM
alt-svc: h3=":443"; ma=86400
```

This confirms:

* Cloudflare is reachable
* Backend is **not reachable via Traefik**

---

#### ✅ When site is **WORKING**

```bash
curl -I https://uat-gvsv2.hashiraworks.com
```

**Output:**

```
HTTP/2 200
date: Tue, 03 Feb 2026 08:41:35 GMT
content-type: text/html; charset=utf-8
cache-control: no-store,no-cache,must-revalidate,max-age=0
nel: {"report_to":"cf-nel","success_fraction":0.0,"max_age":604800}
link: </assets/frappe/dist/css/website.bundle.HDNOTQQX.css>; rel=preload; as=style,</assets/erpnext/dist/css/erpnext-web.bundle.ZILWTXE5.css>; rel=preload; as=style,</assets/frappe/dist/css/login.bundle.XQ2HK3OH.css>; rel=preload; as=style,</assets/frappe/dist/js/frappe-web.bundle.A4QFLFM5.js>; rel=preload; as=script,</website_script.js>; rel=preload; as=script,</assets/frappe/icons/lucide/icons.svg?v=1770093154.3296762>; rel=preload; as=fetch; crossorigin,</assets/frappe/icons/timeless/icons.svg?v=1770093154.3296762>; rel=preload; as=fetch; crossorigin,</assets/frappe/icons/espresso/icons.svg?v=1770093154.3296762>; rel=preload; as=fetch; crossorigin,</assets/erpnext/icons/pos-icons.svg?v=1770093154.3296762>; rel=preload; as=fetch; crossorigin
referrer-policy: same-origin, strict-origin-when-cross-origin
server: cloudflare
set-cookie: sid=Guest; Expires=Tue, 10 Feb 2026 10:41:34 GMT; Max-Age=612000; HttpOnly; Path=/; SameSite=Lax
set-cookie: system_user=no; Path=/; SameSite=Lax
set-cookie: full_name=Guest; Path=/; SameSite=Lax
set-cookie: user_id=Guest; Path=/; SameSite=Lax
set-cookie: user_lang=en; Path=/; SameSite=Lax
strict-transport-security: max-age=63072000; includeSubDomains; preload
vary: Accept-Encoding
x-content-type-options: nosniff
x-frame-options: SAMEORIGIN
x-from-cache: False
x-page-name: login
x-xss-protection: 1; mode=block
cf-cache-status: DYNAMIC
report-to: {"group":"cf-nel","max_age":604800,"endpoints":[{"url":"https://a.nel.cloudflare.com/report/v4?s=UdlP9vcuOsFwF81AePscsdJ08OCSUgkF1BAoqjA0kCgBbLr59QwimX5uxKQDlya9iFw%2BmGfLJesbbmwy0Aim8XB15mRClcEAhKP4%2Bt6eOlniyIuO%2B0LKZ%2FCv"}]}
cf-ray: 9c80a13ff91ab13b-BOM
alt-svc: h3=":443"; ma=86400
```

This confirms:

* Traefik routing is correct
* Frontend is reachable
* Site is healthy

---

## 🧠 Root Cause (Very Important)

When using **Traefik v2 / v3** with **Docker Compose** and **multi-tenant Frappe**:

* Traefik **does not automatically know** which Docker network to use
* Even if containers are on the same network
* Result: **Traefik sees the router but cannot reach the service**
* This causes **502 Bad Gateway**

---

## ✅ FIX: Explicitly Set Docker Network for Traefik

### Step 1: Edit compose file

```bash
nano frappe-hrms-erpnext-compose.yml
```

---

### Step 2: Update `frontend` service → `labels`

Ensure **ALL** of the following labels exist:

```yaml
labels:
  traefik.enable: "true"
  traefik.docker.network: frappe-hrms-erpnext_default
  traefik.http.routers.frontend-http.entrypoints: websecure
  traefik.http.routers.frontend-http.rule: HostRegexp(`{host:.+}`)
  traefik.http.routers.frontend-http.tls.certresolver: main-resolver
  traefik.http.services.frontend.loadbalancer.server.port: "8080"
```

🔑 **Critical line (do not skip):**

```yaml
traefik.docker.network: frappe-hrms-erpnext_default
```

---

### Step 3: Restart Containers

```bash
docker compose -f frappe-hrms-erpnext-compose.yml down
docker compose -f frappe-hrms-erpnext-compose.yml up -d
```

Optional but recommended:

```bash
sleep 30
docker compose -f frappe-hrms-erpnext-compose.yml restart proxy frontend
```

---

### Step 4: Verify Fix

```bash
curl -I https://uat-pwv2.hashiraworks.com
curl -I https://uat-gvsv2.hashiraworks.com
```

**Expected:**

```
HTTP/2 200
```

---

## 📝 Important Notes

* This issue is **NOT related to**

  * `bench migrate`
  * Code changes
  * Image rollback
* Backend, DB, Redis can all be healthy and still show **502**
* This is a **Traefik + Docker networking requirement**
* Always add `traefik.docker.network` for **production multi-tenant setups**

---


## 🎯 Complete Upgrade Script (All Steps Combined)

```bash
#!/bin/bash

# Step 1: Rebuild image with latest code
python3 easy-install.py build \
  --apps-json apps.json \
  --containerfile images/custom/Containerfile \
  --tag yaswanth1679/frappe-hrms-erpnext:version-16 \
  --push

# Step 2: Stop containers (preserve volumes)
docker compose -f frappe-hrms-erpnext-compose.yml down

# Step 3: Pull updated image
docker pull yaswanth1679/frappe-hrms-erpnext:version-16

# Step 4: Verify image timestamp
echo "=== Image Build Time ==="
docker image inspect yaswanth1679/frappe-hrms-erpnext:version-16 --format='{{.Created}}'

# Step 5: Start containers
docker compose -f frappe-hrms-erpnext-compose.yml up -d

# Step 6: Wait for initialization
sleep 30

# Step 7: Check container status
docker compose -f frappe-hrms-erpnext-compose.yml ps

# Step 8: Migrate sites
echo "=== Migrating Sites ==="
docker exec -it frappe-hrms-erpnext-backend-1 bench --site uat-pwv2.hashiraworks.com migrate
docker exec -it frappe-hrms-erpnext-backend-1 bench --site uat-gvsv2.hashiraworks.com migrate

# Step 9: Clear cache
echo "=== Clearing Cache ==="
docker exec -it frappe-hrms-erpnext-backend-1 bench --site uat-pwv2.hashiraworks.com clear-cache
docker exec -it frappe-hrms-erpnext-backend-1 bench --site uat-gvsv2.hashiraworks.com clear-cache

# Step 10: Restart services
docker compose -f frappe-hrms-erpnext-compose.yml restart backend queue-long queue-short scheduler websocket

# Step 11: Verify deployment
echo "=== Verifying Deployment ==="
docker exec -it frappe-hrms-erpnext-backend-1 bench --site uat-pwv2.hashiraworks.com doctor
docker exec -it frappe-hrms-erpnext-backend-1 bench --site uat-gvsv2.hashiraworks.com doctor

# Step 12: Test sites
echo "=== Testing Sites ==="
curl -I https://uat-pwv2.hashiraworks.com
curl -I https://uat-gvsv2.hashiraworks.com

echo "=== Upgrade Complete ==="
```

---

## 📊 Verification Checklist

After upgrade, verify:

- ✅ Image build timestamp is recent
- ✅ Your code changes are present in the image
- ✅ All containers are `Up` and healthy
- ✅ Both sites migrated successfully
- ✅ Scheduler shows "Workers online: 2"
- ✅ Sites accessible via HTTPS
- ✅ No internal server errors
- ✅ DNS multitenant enabled
- ✅ Traefik rule is `HostRegexp(\`{host:.+}\`)`

---

## ⚠️ Important Notes

### Data Safety

- ✅ **`docker compose down`** - Safe, preserves volumes
- ❌ **`docker compose down -v`** - DELETES ALL DATA (never use during upgrade)

### Migration is Mandatory

- **Every upgrade requires migration** for both sites
- Migration applies schema changes from new code
- Skipping migration = code won't work properly

### Multi-Tenant Configuration

- `HostRegexp(\`{host:.+}\`)` - Routes ALL domains to frontend
- `dns_multitenant: true` - Frappe handles site routing internally
- Each site has separate database
- Sites share same codebase but isolated data

### Cache Clearing

- Always clear cache after code changes
- Ensures Python bytecode is regenerated
- Prevents stale code from running

---
