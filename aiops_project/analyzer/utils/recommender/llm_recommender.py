import os
import json
import re

import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

model = genai.GenerativeModel("gemini-2.5-flash")


CLOUD_PROFILES = {
    "aws": {
        "label": "AWS",
        "service": "EC2",
        "server_name": "EC2 instance",
        "console_path": "AWS Console > EC2 > Instances > Launch instances",
        "small_size": "t3.micro",
        "medium_size": "t3.medium",
        "large_size": "t3.large",
        "ssh_user": "ubuntu",
        "address_name": "Public IPv4 address",
        "firewall_name": "Security Group",
        "ssh_command": "ssh -i .\\your-key.pem ubuntu@<ec2-public-ip>",
    },
    "gcp": {
        "label": "GCP",
        "service": "Compute Engine",
        "server_name": "Compute Engine VM",
        "console_path": "Google Cloud Console > Compute Engine > VM instances > Create instance",
        "small_size": "e2-micro",
        "medium_size": "e2-standard-2",
        "large_size": "e2-standard-4",
        "ssh_user": "$USER",
        "address_name": "External IP",
        "firewall_name": "Firewall rules",
        "ssh_command": "gcloud compute ssh <vm-name> --zone <zone-name>",
    },
    "azure": {
        "label": "Azure",
        "service": "Virtual Machines",
        "server_name": "Azure virtual machine",
        "console_path": "Azure Portal > Virtual machines > Create > Azure virtual machine",
        "small_size": "Standard B1s",
        "medium_size": "Standard B2s",
        "large_size": "Standard D2s v5",
        "ssh_user": "azureuser",
        "address_name": "Public IP address",
        "firewall_name": "Network Security Group",
        "ssh_command": "ssh -i .\\your-key.pem azureuser@<azure-public-ip>",
    },
}

RUNTIME_PROFILES = {
    "django": {
        "label": "Django",
        "port": "8000",
        "install": [
            "python3 -m venv .venv",
            "source .venv/bin/activate",
            "pip install -r requirements.txt",
        ],
        "env": [
            "DEBUG=False",
            "ALLOWED_HOSTS=<server-public-ip-or-domain>",
            "SECRET_KEY=<strong-secret-key>",
            "DATABASE_URL=<database-connection-string>",
        ],
        "start": [
            "python manage.py migrate",
            "python manage.py collectstatic --noinput",
            "gunicorn <project_name>.wsgi:application --bind 0.0.0.0:8000",
        ],
        "process": "systemd or Gunicorn behind Nginx",
    },
    "flask": {
        "label": "Flask",
        "port": "5000",
        "install": [
            "python3 -m venv .venv",
            "source .venv/bin/activate",
            "pip install -r requirements.txt",
        ],
        "env": [
            "FLASK_ENV=production",
            "SECRET_KEY=<strong-secret-key>",
            "DATABASE_URL=<database-connection-string>",
        ],
        "start": ["gunicorn app:app --bind 0.0.0.0:5000"],
        "process": "systemd or Gunicorn behind Nginx",
    },
    "fastapi": {
        "label": "FastAPI",
        "port": "8000",
        "install": [
            "python3 -m venv .venv",
            "source .venv/bin/activate",
            "pip install -r requirements.txt",
        ],
        "env": [
            "DATABASE_URL=<database-connection-string>",
            "SECRET_KEY=<strong-secret-key>",
            "ALLOWED_ORIGINS=<frontend-domain>",
        ],
        "start": ["uvicorn main:app --host 0.0.0.0 --port 8000"],
        "process": "systemd or Uvicorn behind Nginx",
    },
    "node/express": {
        "label": "Express.js",
        "port": "3000",
        "install": ["npm install", "npm install -g pm2"],
        "env": [
            "NODE_ENV=production",
            "PORT=3000",
            "DATABASE_URL=<database-connection-string-if-used>",
            "SESSION_SECRET=<strong-secret-if-used>",
        ],
        "start": ["pm2 start npm --name online-exam-portal -- start", "pm2 save", "pm2 startup"],
        "process": "PM2 behind Nginx",
    },
}


def _rule_based_resource_estimate(features):
    """
    Deterministic sizing baseline, independent of the LLM. Mirrors the
    labeling logic used for training data generation (see
    data_generator.generate_labels), so LLM output can be sanity-checked
    against a known-reasonable estimate instead of trusted blindly.
    """
    total_lines = features.get("total_lines") or 0
    dependency_count = features.get("dependency_count") or 0
    security_score = features.get("security_score") or 0

    if total_lines < 3000 and dependency_count < 15:
        cpu, ram, storage = 1, 1, 10
    elif total_lines < 20000:
        cpu, ram, storage = 2, 4, 20
    else:
        cpu, ram, storage = 4, 8, 50

    if security_score and security_score > 6:
        cpu += 0.5
        ram += 1

    return {"cpu": cpu, "ram": ram, "storage": storage}


def _sanity_check_resources(predicted, features, max_multiplier=3):
    """
    Clamp LLM-predicted resources against the rule-based baseline so a
    hallucinated or copy-pasted-example value can't slip through
    unquestioned. Values are allowed to differ from the baseline by up to
    `max_multiplier`x in either direction, which still gives the LLM room
    to account for things the rule-based estimate can't see (e.g. it read
    the code and noticed heavy background jobs) without letting it return
    wildly disproportionate numbers for a small project.
    """
    if not isinstance(predicted, dict):
        return None

    baseline = _rule_based_resource_estimate(features)
    clamped = {}

    for key in ("cpu", "ram", "storage"):
        predicted_value = predicted.get(key)
        baseline_value = baseline[key]

        if not isinstance(predicted_value, (int, float)):
            clamped[key] = baseline_value
            continue

        upper_bound = baseline_value * max_multiplier
        lower_bound = baseline_value / max_multiplier
        clamped[key] = round(min(max(predicted_value, lower_bound), upper_bound), 2)

    return clamped


def _normalize_stack(framework):
    framework_name = (framework or "").lower()
    if "django" in framework_name:
        return "django"
    if "flask" in framework_name:
        return "flask"
    if "fastapi" in framework_name:
        return "fastapi"
    if "express" in framework_name or "node" in framework_name:
        return "node/express"
    return "node/express" if "react" in framework_name else "unknown"


def _recommended_size(resources, cloud):
    profile = CLOUD_PROFILES.get((cloud or "").lower(), CLOUD_PROFILES["aws"])
    cpu = (resources or {}).get("cpu") or 1
    ram = (resources or {}).get("ram") or 1

    if cpu <= 1 and ram <= 1:
        return profile["small_size"]
    if cpu <= 2 and ram <= 4:
        return profile["medium_size"]
    return profile["large_size"]


def _is_shallow_runbook(runbook):
    if not isinstance(runbook, list) or len(runbook) < 6:
        return True

    detail_count = 0
    short_detail_count = 0
    generic_title_count = 0

    for index, step in enumerate(runbook):
        if not isinstance(step, dict):
            return True
        title = str(step.get("title", ""))
        details = step.get("details") or []
        detail_count += len(details)
        short_detail_count += sum(1 for detail in details if len(str(detail).split()) < 10)
        if title.lower().startswith("recommendation step") or title.strip() == str(index + 1):
            generic_title_count += 1

    return detail_count < len(runbook) * 2 or short_detail_count > detail_count / 2 or generic_title_count > 0


def _format_commands(commands):
    return [command for command in commands if command]


def _is_virtual_machine_architecture(selected_architecture):
    architecture = (selected_architecture or "").lower()
    return not architecture or any(
        name in architecture
        for name in ("ec2", "compute engine", "virtual machine", "vm")
    )


def _build_managed_architecture_runbook(
    framework,
    cloud,
    resources,
    deployment_steps,
    selected_architecture,
    repo_url=None,
):
    cloud_key = (cloud or "aws").lower()
    cloud_profile = CLOUD_PROFILES.get(cloud_key, CLOUD_PROFILES["aws"])
    stack_key = _normalize_stack(framework)
    runtime = RUNTIME_PROFILES.get(stack_key) or {
        "label": framework or "Detected stack",
        "port": "<app-port>",
        "env": ["Add the variables listed in .env.example or README."],
    }
    architecture = selected_architecture or cloud_profile["service"]
    repository = repo_url or "<your-github-repo-url>"
    cpu = (resources or {}).get("cpu", "recommended")
    ram = (resources or {}).get("ram", "recommended")
    storage = (resources or {}).get("storage", "recommended")
    architecture_lower = architecture.lower()

    if "fargate" in architecture_lower:
        platform_notes = [
            "Use Amazon ECS with Fargate so AWS runs containers without you managing an EC2 server.",
            "Create an ECR repository, push the Docker image, then run it with an ECS task definition and service.",
            f"Expose container port {runtime['port']} through an Application Load Balancer for browser traffic.",
        ]
        commands = [
            "aws ecr create-repository --repository-name aiops-app",
            "docker build -t aiops-app .",
            "aws ecr get-login-password --region <region> | docker login --username AWS --password-stdin <account-id>.dkr.ecr.<region>.amazonaws.com",
            "docker tag aiops-app:latest <account-id>.dkr.ecr.<region>.amazonaws.com/aiops-app:latest",
            "docker push <account-id>.dkr.ecr.<region>.amazonaws.com/aiops-app:latest",
        ]
    elif "app runner" in architecture_lower:
        platform_notes = [
            "Use AWS App Runner for a managed web-service deployment with less infrastructure setup than ECS.",
            "Connect the GitHub repository or use an image from ECR, then configure build/start commands.",
            f"Set the service port to {runtime['port']} and add production environment variables in the App Runner console.",
        ]
        commands = ["docker build -t aiops-app .", "docker run -p 8080:{port} aiops-app".format(port=runtime["port"])]
    elif "cloud run" in architecture_lower:
        platform_notes = [
            "Use Google Cloud Run for a serverless container deployment.",
            "Build and push the container image with Cloud Build, then deploy it as a Cloud Run service.",
            f"Set the container port to {runtime['port']} and add production environment variables in Cloud Run.",
        ]
        commands = [
            "gcloud builds submit --tag gcr.io/<project-id>/aiops-app",
            "gcloud run deploy aiops-app --image gcr.io/<project-id>/aiops-app --platform managed --allow-unauthenticated",
        ]
    elif "app service" in architecture_lower:
        platform_notes = [
            "Use Azure App Service for managed web app hosting.",
            "Create an App Service plan, connect the repository or deploy a Docker image, and configure app settings.",
            f"Set the startup command so the app listens on port {runtime['port']}.",
        ]
        commands = [
            "az webapp up --name <app-name> --resource-group <resource-group> --runtime <runtime>",
            "az webapp config appsettings set --name <app-name> --resource-group <resource-group> --settings KEY=VALUE",
        ]
    elif "gke" in architecture_lower or "aks" in architecture_lower:
        platform_notes = [
            f"Use {architecture} when you want Kubernetes-native deployment and scaling.",
            "Build a container image, push it to the cloud registry, then create Deployment and Service manifests.",
            "Expose the app through a LoadBalancer service or ingress controller.",
        ]
        commands = [
            "docker build -t aiops-app .",
            "kubectl create deployment aiops-app --image=<registry>/aiops-app:latest",
            f"kubectl expose deployment aiops-app --type=LoadBalancer --port=80 --target-port={runtime['port']}",
        ]
    else:
        platform_notes = [
            f"Use {architecture} as the selected deployment architecture for this recommendation.",
            "Package the app, configure environment variables, and deploy through the managed service console.",
            f"Make sure the service routes traffic to app port {runtime['port']}.",
        ]
        commands = ["docker build -t aiops-app ."]

    return [
        {
            "title": f"Use {architecture} as the selected architecture",
            "details": [
                f"The user selected {architecture}, so this runbook is not using the default primary VM path.",
                f"Detected stack: {runtime['label']}. Target cloud: {cloud_profile['label']}.",
                f"Resource estimate: {cpu} vCPU, {ram} GB RAM, {storage} GB storage.",
            ],
            "commands": [],
        },
        {
            "title": "Prepare the repository for managed deployment",
            "details": [
                "Push the latest code to GitHub before creating the cloud service.",
                "Make sure Dockerfile, dependency files, and startup commands are present and tested locally.",
                "Do not commit .env files, passwords, database URLs, Gemini keys, or cloud secrets.",
            ],
            "commands": ["git status", "git add .", "git commit -m \"Prepare managed deployment\"", "git push origin main"],
        },
        {
            "title": f"Configure {architecture}",
            "details": platform_notes,
            "commands": [],
        },
        {
            "title": "Build and publish the deployable artifact",
            "details": [
                "Managed platforms usually deploy either from source control or from a container image.",
                "If the service asks for a port, use the detected runtime port from this project.",
                "If the service asks for health checks, start with the root path or a simple health endpoint if the project has one.",
            ],
            "commands": commands,
        },
        {
            "title": "Add production environment variables",
            "details": [
                "Create environment variables inside the cloud service settings, not in committed source code.",
                "Start with these common variables: " + ", ".join(runtime.get("env", [])),
                "Save the settings, then trigger a redeploy so the app starts with the new values.",
            ],
            "commands": [],
        },
        {
            "title": "Deploy and verify the public URL",
            "details": [
                "Open the service URL generated by the cloud provider after deployment finishes.",
                "Test the most important user flows, not only the home page.",
                "Check deployment logs immediately if the service returns 502, 503, or a startup timeout.",
            ],
            "commands": [],
        },
        {
            "title": "Review the original API recommendation steps",
            "details": [
                "Use these generated steps as supporting guidance for the selected architecture.",
                "Ignore any step that asks you to create a raw VM when the selected architecture is managed.",
                "Original API recommendation steps: " + " | ".join(deployment_steps or []),
            ],
            "commands": [],
        },
    ]


def _build_beginner_runbook(framework, cloud, resources, deployment_steps, repo_url=None, selected_architecture=None):
    if not _is_virtual_machine_architecture(selected_architecture):
        return _build_managed_architecture_runbook(
            framework=framework,
            cloud=cloud,
            resources=resources,
            deployment_steps=deployment_steps,
            selected_architecture=selected_architecture,
            repo_url=repo_url,
        )

    cloud_key = (cloud or "aws").lower()
    cloud_profile = CLOUD_PROFILES.get(cloud_key, CLOUD_PROFILES["aws"])
    stack_key = _normalize_stack(framework)
    runtime = RUNTIME_PROFILES.get(stack_key)
    size = _recommended_size(resources, cloud_key)
    repository = repo_url or "<your-github-repo-url>"
    cpu = (resources or {}).get("cpu", "recommended")
    ram = (resources or {}).get("ram", "recommended")
    storage = (resources or {}).get("storage", "recommended")

    if runtime is None:
        runtime = {
            "label": framework or "Detected stack",
            "port": "<app-port>",
            "install": ["Follow the dependency install command in the project README."],
            "env": ["Add the variables listed in .env.example or README."],
            "start": ["Follow the production start command in the project README."],
            "process": "a process manager suitable for this stack",
        }

    install_commands = [
        "sudo apt update",
        "sudo apt upgrade -y",
        "sudo apt install -y git curl nginx",
    ]
    if stack_key == "node/express":
        install_commands.extend(
            [
                "curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -",
                "sudo apt install -y nodejs",
                "node -v",
                "npm -v",
            ]
        )
    elif stack_key in {"django", "flask", "fastapi"}:
        install_commands.extend(["sudo apt install -y python3 python3-venv python3-pip"])

    return [
        {
            "title": "Understand the generated recommendation",
            "details": [
                f"The selected architecture is {selected_architecture or cloud_profile['service']} on {cloud_profile['label']} for a {runtime['label']} project.",
                f"Recommended starter server: {size}. Resource estimate: {cpu} vCPU, {ram} GB RAM, {storage} GB storage.",
                f"Recommended operating system: Ubuntu 22.04 LTS. Application test port: {runtime['port']}.",
                "Use the remaining steps in order. Each step explains what to click, what value to choose, and what command to run.",
            ],
            "commands": [],
        },
        {
            "title": "Push the project to GitHub",
            "details": [
                "Open the project on your computer and make sure the latest code is committed.",
                "Create a GitHub repository if one does not already exist, then push the code.",
                "Do not push real .env files, passwords, database URLs, API keys, or cloud keys.",
            ],
            "commands": ["git status", "git add .", "git commit -m \"Prepare deployment\"", "git push origin main"],
        },
        {
            "title": f"Create the {cloud_profile['server_name']}",
            "details": [
                f"Open {cloud_profile['console_path']}.",
                f"Choose Ubuntu 22.04 LTS as the image because the commands in this runbook use Ubuntu package names.",
                f"Choose {size} because it matches the API resource estimate for this repository.",
                "Create or select an SSH key pair. Download the private key and keep it safe because it is needed to connect.",
            ],
            "commands": [],
        },
        {
            "title": f"Open the required {cloud_profile['firewall_name']} ports",
            "details": [
                "Open SSH port 22 only from your own IP address so only your computer can connect.",
                "Open HTTP port 80 from the internet so normal browser traffic can reach Nginx.",
                "Open HTTPS port 443 from the internet so you can add SSL later.",
                f"Temporarily open app port {runtime['port']} only from your own IP for testing. Close it after Nginx is working.",
            ],
            "commands": [],
        },
        {
            "title": "Connect to the server",
            "details": [
                f"Wait until the server status is running, then copy the {cloud_profile['address_name']}.",
                "Open PowerShell on your computer in the folder where your private key is stored.",
                "Run the SSH command. The first connection may ask you to trust the server fingerprint; type yes.",
            ],
            "commands": [cloud_profile["ssh_command"]],
        },
        {
            "title": "Install server tools and runtime",
            "details": [
                "Run these commands on the cloud server, not on your local computer.",
                f"They install Linux updates, Git, Nginx, and the runtime needed for {runtime['label']}.",
                "If a command asks for confirmation, type y and press Enter.",
            ],
            "commands": install_commands,
        },
        {
            "title": "Clone the repository on the server",
            "details": [
                "Clone the same GitHub repository that Analyze used.",
                "After cloning, move into the project folder before installing dependencies.",
                "If the repository is private, use a GitHub token or SSH deploy key instead of a normal password.",
            ],
            "commands": [f"git clone {repository}", "cd <repo-folder>", "ls"],
        },
        {
            "title": "Create production environment variables",
            "details": [
                "Create a .env file on the server for values that should not be stored in GitHub.",
                "Use the variable names from this project README, .env.example, or source code.",
                "For this stack, start with these common values: " + ", ".join(runtime["env"]),
            ],
            "commands": ["nano .env"],
        },
        {
            "title": "Install application dependencies",
            "details": [
                f"Run the dependency commands for {runtime['label']} from inside the cloned project folder.",
                "Fix any missing package errors before continuing. The app should install cleanly before you try to run it.",
            ],
            "commands": runtime["install"],
        },
        {
            "title": f"Start the application with {runtime['process']}",
            "details": [
                "Start the app in a way that keeps running after the SSH window closes.",
                f"The app should listen on 0.0.0.0:{runtime['port']} so the cloud server can receive traffic.",
                f"Test it in your browser with http://<{cloud_profile['address_name'].lower().replace(' ', '-')}>:{runtime['port']}.",
            ],
            "commands": runtime["start"],
        },
        {
            "title": "Configure Nginx reverse proxy",
            "details": [
                f"Nginx receives browser traffic on port 80 and forwards it to the app on port {runtime['port']}.",
                "This lets users visit the server without typing the app port.",
                "After Nginx works, remove the temporary app-port firewall rule and keep only 22, 80, and 443 open.",
            ],
            "commands": [
                "sudo nano /etc/nginx/sites-available/app",
                "sudo ln -s /etc/nginx/sites-available/app /etc/nginx/sites-enabled/app",
                "sudo nginx -t",
                "sudo systemctl restart nginx",
            ],
        },
        {
            "title": "Verify, monitor, and deploy future changes",
            "details": [
                "Open the public server URL and test login, exam creation, submission, and any database-backed screens.",
                "Check application logs after every deploy so startup errors are visible immediately.",
                "For future updates, push to GitHub, SSH into the server, pull changes, reinstall dependencies if needed, and restart the process manager.",
                "Original API recommendation steps merged into this runbook: " + " | ".join(deployment_steps or []),
            ],
            "commands": _format_commands(
                [
                    "pm2 logs online-exam-portal" if stack_key == "node/express" else "",
                    "git pull origin main",
                    "npm install" if stack_key == "node/express" else "",
                    "pm2 restart online-exam-portal" if stack_key == "node/express" else "",
                ]
            ),
        },
    ]


def _ensure_beginner_runbook(data, framework, cloud, resources, repo_url=None, selected_architecture=None):
    deployment_steps = data.get("deployment_steps") or []
    if not isinstance(deployment_steps, list):
        deployment_steps = [str(deployment_steps)]

    runbook = data.get("deployment_runbook")
    if _is_shallow_runbook(runbook):
        data["deployment_runbook"] = _build_beginner_runbook(
            framework=framework,
            cloud=cloud,
            resources=resources,
            deployment_steps=deployment_steps,
            repo_url=repo_url,
            selected_architecture=selected_architecture,
        )
    return data


def _default_recommendation(framework, cloud, selected_architecture=None):
    framework_name = (framework or "unknown").lower()
    cloud_name = (cloud or "cloud").upper()
    architecture = selected_architecture or cloud_name

    steps = [
        "Clone repository.",
        "Install dependencies.",
        "Build Docker image.",
        f"Deploy on {architecture}.",
    ]

    files = [
        "Dockerfile",
        "docker-compose.yml",
        ".env",
    ]

    if framework_name == "django":
        steps.insert(2, "Run migrations and collectstatic.")
        files.append("nginx.conf")

    runbook = [
        {
            "title": "Review the generated recommendation",
            "details": [
                f"Target cloud: {cloud_name}.",
                f"Selected architecture: {architecture}.",
                f"Detected framework: {framework or 'Unknown'}.",
                "Use this fallback runbook because the AI recommendation service did not return a detailed plan.",
            ],
            "commands": [],
        },
        {
            "title": "Prepare the repository",
            "details": [
                "Push the latest project code to GitHub before opening the cloud server.",
                "Do not commit real .env files, passwords, tokens, or cloud keys.",
            ],
            "commands": ["git add .", "git commit -m \"Prepare deployment\"", "git push origin main"],
        },
        {
            "title": "Provision a starter Linux server",
            "details": [
                f"Create a small Ubuntu 22.04 LTS virtual machine on {cloud_name}.",
                "Open SSH port 22 only for your IP, and open HTTP 80 plus HTTPS 443 for users.",
                "Temporarily open the app port only from your IP while testing.",
            ],
            "commands": [],
        },
        {
            "title": "Install dependencies and run the app",
            "details": [
                "SSH into the server, install Git and runtime dependencies, clone the repository, and start the app.",
                "Use the app's README for project-specific install and start commands.",
            ],
            "commands": ["sudo apt update", "sudo apt install -y git", "git clone <repository-url>", "cd <repo-folder>"],
        },
    ]

    return {
        "predicted_resources": None,
        "os_recommendation": "Ubuntu 22.04 LTS",
        "deployment_steps": steps,
        "deployment_runbook": runbook,
        "configuration_files_needed": files,
        "architecture": architecture,
    }


def _extract_json(text):
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group())
    except Exception:
        return None


def generate_gemini_recommendation(insights, features, cloud, repo_url=None, selected_architecture=None):
    framework = insights.get("framework", "Unknown")
    architecture = selected_architecture or "best fit for the selected cloud"

    # NOTE: the previous prompt put literal example numbers (cpu: 2, ram: 4,
    # storage: 30) directly in the expected-output schema. LLMs frequently
    # echo concrete example values back verbatim instead of reasoning about
    # the actual input, especially when the example "looks like a real
    # answer" rather than an obvious placeholder. The schema below uses
    # clearly-marked placeholder text instead, and explicitly restates the
    # real project metrics right above it so there's no ambiguity about
    # what to size for.
    prompt = f"""
You are an experienced DevOps Architect.

Analyze the following repository information and size infrastructure
resources specifically for THIS project. Do not use generic or example
values -- base cpu/ram/storage on the actual metrics given below.

Framework:
{framework}

Dependencies:
{insights.get("dependencies", [])}

Project metrics (use these to size resources):
{json.dumps(features, indent=2)}

Target cloud:
{cloud}

Selected deployment architecture:
{architecture}

Important architecture instruction:
The recommendation, deployment_steps, deployment_runbook, configuration
files, and commands must target "{architecture}". If this is a managed
service such as ECS Fargate, App Runner, Cloud Run, Azure App Service,
GKE Autopilot, or AKS, do not give a raw VM/SSH/Nginx-first runbook unless
that service genuinely requires it.

Return ONLY valid JSON, matching this exact shape. The bracketed text is
a description of what to put there, NOT a value to copy -- replace each
one with a real number you calculated from the project metrics above.

{{
    "predicted_resources": {{
        "cpu": "[number of vCPUs appropriate for total_lines={features.get('total_lines')} and dependency_count={features.get('dependency_count')}, e.g. 0.5 to 8]",
        "ram": "[RAM in GB appropriate for this project's size, e.g. 0.5 to 16]",
        "storage": "[storage in GB appropriate for this project's size, e.g. 5 to 100]"
    }},
    "os_recommendation": "Ubuntu 22.04 LTS",
    "deployment_steps": [
        "...",
        "...",
        "..."
    ],
    "deployment_runbook": [
        {{
            "title": "clear beginner step title, not 'Recommendation step 1'",
            "details": [
                "detail 1: specific beginner explanation connected to this project's stack, cloud, recommended resources, operating system, ports, and deployment_steps",
                "detail 2: exact console choices where useful, such as VM family/size, Ubuntu image, firewall/security-group ports, SSH username, and what value to copy",
                "detail 3: what the beginner should verify before moving to the next step"
            ],
            "commands": [
                "only include commands that the user should paste in a terminal for this step"
            ]
        }}
    ],
    "configuration_files_needed": [
        "...",
        "...",
        "..."
    ],
    "architecture": "{architecture}"
}}

Do not explain anything.
Do not use markdown.
Only output JSON. All numeric fields must be actual numbers, not strings
or bracketed placeholders.
The deployment_runbook must be detailed enough for a complete beginner
and must merge the actual deployment_steps into one coherent ordered guide.
Return at least 10 deployment_runbook items.
Each deployment_runbook item must contain a human title, at least 3 details,
and commands when terminal work is needed.
Do not create a separate generic guide that conflicts with deployment_steps.
"""

    try:
        response = model.generate_content(prompt)
        data = _extract_json(response.text)

        if data is None:
            return _default_recommendation(framework, cloud, selected_architecture)

        # Sanity-check whatever the LLM returned against a deterministic
        # baseline before trusting it, regardless of whether it looks
        # plausible on its face.
        predicted = data.get("predicted_resources")
        data["predicted_resources"] = _sanity_check_resources(predicted, features)
        resources = data["predicted_resources"] or _rule_based_resource_estimate(features)
        data["architecture"] = data.get("architecture") or architecture
        data = _ensure_beginner_runbook(
            data,
            framework,
            cloud,
            resources,
            repo_url,
            selected_architecture=selected_architecture,
        )

        return data

    except Exception as e:
        print(e)
        data = _default_recommendation(framework, cloud, selected_architecture)
        resources = data["predicted_resources"] or _rule_based_resource_estimate(features)
        return _ensure_beginner_runbook(
            data,
            framework,
            cloud,
            resources,
            repo_url,
            selected_architecture=selected_architecture,
        )
