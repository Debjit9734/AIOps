SUPPORTED_CLOUDS = {"aws", "gcp", "azure"}
SUPPORTED_STACKS = {"django", "flask", "fastapi", "node"}
SUPPORTED_DEPLOYMENTS = {
    "aws_ec2",
    "aws_ecs_fargate",
    "aws_apprunner",
    "gcp_cloud_run",
    "gcp_gke",
    "azure_app_service",
    "azure_aks",
}

DEPLOYMENT_META = {
    "aws_ec2": {
        "cloud": "aws",
        "name": "AWS EC2 (Nginx + systemd)",
        "clickpath": [
            ["AWS Console", "EC2", "Instances", "Launch Instance"],
            ["AWS Console", "Route 53", "Hosted zones", "Create record"],
            ["AWS Console", "CloudWatch", "Logs", "Create log group"],
        ],
    },
    "aws_ecs_fargate": {
        "cloud": "aws",
        "name": "AWS ECS Fargate + ALB",
        "clickpath": [
            ["AWS Console", "ECR", "Create repository"],
            ["AWS Console", "ECS", "Clusters", "Create Cluster"],
            ["AWS Console", "EC2", "Load Balancers", "Create ALB"],
            ["AWS Console", "CloudWatch", "Container Insights"],
        ],
    },
    "aws_apprunner": {
        "cloud": "aws",
        "name": "AWS App Runner (Container)",
        "clickpath": [
            ["AWS Console", "ECR", "Create repository"],
            ["AWS Console", "App Runner", "Create service"],
            ["AWS Console", "Route 53", "Create CNAME record"],
            ["AWS Console", "CloudWatch", "Alarms", "Create alarm"],
        ],
    },
    "gcp_cloud_run": {
        "cloud": "gcp",
        "name": "GCP Cloud Run",
        "clickpath": [
            ["Google Cloud Console", "Cloud Run", "Create Service"],
            ["Google Cloud Console", "Artifact Registry", "Repositories", "Create"],
            ["Google Cloud Console", "Cloud DNS", "Create zone / records"],
            ["Google Cloud Console", "Cloud Monitoring", "Alerting", "Create policy"],
        ],
    },
    "gcp_gke": {
        "cloud": "gcp",
        "name": "GKE + Ingress",
        "clickpath": [
            ["Google Cloud Console", "Kubernetes Engine", "Clusters", "Create"],
            ["Google Cloud Console", "Kubernetes Engine", "Workloads", "Deploy"],
            ["Google Cloud Console", "Cloud DNS", "Create records"],
            ["Google Cloud Console", "Cloud Monitoring", "Dashboards"],
        ],
    },
    "azure_app_service": {
        "cloud": "azure",
        "name": "Azure App Service (Container)",
        "clickpath": [
            ["Azure Portal", "Container Registry", "Create"],
            ["Azure Portal", "App Services", "Create Web App"],
            ["Azure Portal", "DNS zones", "Add record set"],
            ["Azure Portal", "Monitor", "Alerts", "Create"],
        ],
    },
    "azure_aks": {
        "cloud": "azure",
        "name": "Azure AKS + Ingress",
        "clickpath": [
            ["Azure Portal", "Kubernetes services", "Create AKS cluster"],
            ["Azure Portal", "Container Registry", "Create / Attach ACR"],
            ["Azure Portal", "DNS zones", "Add A record"],
            ["Azure Portal", "Monitor", "Container insights"],
        ],
    },
}


def validate_target(cloud, target):
    normalized_cloud = (cloud or "").strip().lower()
    if normalized_cloud not in SUPPORTED_CLOUDS:
        return None, "cloud must be one of aws|gcp|azure"

    if not isinstance(target, dict):
        return None, "target object is required"

    stack = (target.get("stack") or "").strip().lower()
    deployment = (target.get("deployment") or "").strip().lower()

    if stack not in SUPPORTED_STACKS:
        return None, "target.stack must be one of django|flask|fastapi|node"
    if deployment not in SUPPORTED_DEPLOYMENTS:
        return (
            None,
            "target.deployment must be one of aws_ec2|aws_ecs_fargate|aws_apprunner|gcp_cloud_run|gcp_gke|azure_app_service|azure_aks",
        )

    expected_cloud = DEPLOYMENT_META[deployment]["cloud"]
    if expected_cloud != normalized_cloud:
        return None, f"target.deployment {deployment} does not belong to cloud {normalized_cloud}"

    return {"stack": stack, "deployment": deployment, "cloud": normalized_cloud}, None


def _runtime_start_command(stack):
    if stack == "django":
        return "gunicorn projectname.wsgi:application --bind 0.0.0.0:8000"
    if stack == "flask":
        return "gunicorn app:app --bind 0.0.0.0:8000"
    if stack == "fastapi":
        return "gunicorn main:app -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000"
    return "node server.js"


def _dockerfile_for_stack(stack):
    if stack == "node":
        return """\
FROM node:20-alpine
WORKDIR /app

COPY package*.json ./
RUN npm ci --only=production

COPY . .
EXPOSE 8000

# Replace server.js with your app entrypoint
CMD ["node", "server.js"]
"""

    entry = _runtime_start_command(stack)
    return f"""\
FROM python:3.11-slim
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["sh", "-c", "{entry}"]
"""


def _docker_compose_for_stack(stack):
    app_cmd = _runtime_start_command(stack)
    if stack == "node":
        app_cmd = "node server.js"

    return f"""\
version: "3.9"
services:
  app:
    build: .
    command: {app_cmd}
    env_file:
      - .env
    ports:
      - "8000:8000"
    restart: unless-stopped
"""


def _nginx_conf():
    return """\
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
"""


def _systemd_service(stack):
    cmd = _runtime_start_command(stack)
    return f"""\
[Unit]
Description=App service
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/srv/app
EnvironmentFile=/srv/app/.env
ExecStart=/bin/bash -lc '{cmd}'
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
"""


def _env_example(stack):
    common = [
        "APP_ENV=production",
        "APP_PORT=8000",
        "APP_DOMAIN=api.example.com",
        "LOG_LEVEL=info",
        "DATABASE_URL=<set-me>",
        "REDIS_URL=<set-me>",
    ]
    if stack in {"django", "flask", "fastapi"}:
        common.insert(0, "PYTHONUNBUFFERED=1")
    if stack == "django":
        common.extend(
            [
                "DJANGO_SETTINGS_MODULE=projectname.settings",
                "DJANGO_SECRET_KEY=<set-me>",
                "ALLOWED_HOSTS=api.example.com",
            ]
        )
    if stack == "node":
        common.extend(["NODE_ENV=production", "PORT=8000"])
    return "\n".join(common) + "\n"


def _k8s_manifests(stack):
    if stack == "node":
        port = 8000
    else:
        port = 8000

    deployment = f"""\
apiVersion: apps/v1
kind: Deployment
metadata:
  name: app
spec:
  replicas: 2
  selector:
    matchLabels:
      app: app
  template:
    metadata:
      labels:
        app: app
    spec:
      containers:
      - name: app
        image: <registry>/<image>:<tag>
        ports:
        - containerPort: {port}
        envFrom:
        - secretRef:
            name: app-secrets
"""
    service = """\
apiVersion: v1
kind: Service
metadata:
  name: app-service
spec:
  selector:
    app: app
  ports:
  - port: 80
    targetPort: 8000
  type: ClusterIP
"""
    ingress = """\
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: app-ingress
  annotations:
    kubernetes.io/ingress.class: nginx
spec:
  rules:
  - host: api.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: app-service
            port:
              number: 80
  tls:
  - hosts:
    - api.example.com
    secretName: app-tls
"""
    return deployment, service, ingress


def _readme_template(stack, cloud, deployment, deployment_steps):
    service_name = DEPLOYMENT_META[deployment]["name"]
    steps = "\n".join([f"{idx + 1}. {step}" for idx, step in enumerate(deployment_steps)])
    return f"""\
# README_DEPLOYMENT

## Target
- Cloud: {cloud.upper()}
- Stack: {stack}
- Deployment: {service_name}

## Prerequisites
- Cloud account with billing enabled
- Container registry access
- DNS zone control for your domain
- TLS certificate method (managed cert recommended)

## Secure Configuration
- Never commit secrets.
- Use .env.example as a template only.
- Store production values in cloud secret manager.

## Deployment Steps
{steps}

## Post-Deploy
- Verify `/health` endpoint.
- Verify HTTPS and redirect from HTTP.
- Confirm logs and metrics are flowing.
"""


def _commands_for_target(stack, cloud, deployment):
    base = [
        "git clone <repo-url>",
        "cd <repo-directory>",
        "cp .env.example .env",
        "docker build -t <image>:<tag> .",
    ]

    if deployment == "aws_ec2":
        base.extend(
            [
                "scp -i <key.pem> -r . ubuntu@<ec2-ip>:/srv/app",
                "ssh ubuntu@<ec2-ip> 'sudo systemctl daemon-reload && sudo systemctl restart app'",
                "ssh ubuntu@<ec2-ip> 'sudo certbot --nginx -d api.example.com'",
            ]
        )
    elif deployment == "aws_ecs_fargate":
        base.extend(
            [
                "aws ecr get-login-password --region <region> | docker login --username AWS --password-stdin <acct>.dkr.ecr.<region>.amazonaws.com",
                "docker tag <image>:<tag> <acct>.dkr.ecr.<region>.amazonaws.com/<repo>:<tag>",
                "docker push <acct>.dkr.ecr.<region>.amazonaws.com/<repo>:<tag>",
                "aws ecs update-service --cluster <cluster> --service <service> --force-new-deployment",
            ]
        )
    elif deployment == "aws_apprunner":
        base.extend(
            [
                "aws apprunner create-service --service-name <name> --source-configuration file://aws/apprunner.json",
            ]
        )
    elif deployment == "gcp_cloud_run":
        base.extend(
            [
                "gcloud auth login",
                "gcloud config set project <project-id>",
                "gcloud builds submit --tag gcr.io/<project-id>/<image>:<tag>",
                "gcloud run deploy <service> --image gcr.io/<project-id>/<image>:<tag> --region <region> --allow-unauthenticated",
            ]
        )
    elif deployment == "gcp_gke":
        base.extend(
            [
                "gcloud container clusters get-credentials <cluster> --region <region>",
                "kubectl apply -f k8s/",
                "kubectl rollout status deployment/app",
            ]
        )
    elif deployment == "azure_app_service":
        base.extend(
            [
                "az login",
                "az acr build --registry <acr-name> --image <image>:<tag> .",
                "az webapp config container set --name <app-name> --resource-group <rg> --docker-custom-image-name <acr>.azurecr.io/<image>:<tag>",
            ]
        )
    elif deployment == "azure_aks":
        base.extend(
            [
                "az login",
                "az aks get-credentials --resource-group <rg> --name <aks-name>",
                "kubectl apply -f k8s/",
                "kubectl rollout status deployment/app",
            ]
        )

    if cloud == "aws":
        base.append("aws cloudwatch put-metric-alarm --alarm-name app-5xx --metric-name HTTPCode_Target_5XX_Count --namespace AWS/ApplicationELB")
    elif cloud == "gcp":
        base.append("gcloud monitoring channels list")
    else:
        base.append("az monitor metrics alert create --name app-cpu-alert --resource-group <rg> --scopes <resource-id>")

    return base


def _deployment_steps(cloud, stack, deployment):
    service_name = DEPLOYMENT_META[deployment]["name"]
    return [
        f"Create and secure your {cloud.upper()} account/project/subscription with MFA and least-privilege IAM.",
        "Create container registry and enable required cloud services.",
        "Create DNS zone/record placeholders for app domain (example: api.example.com).",
        "Prepare environment configuration using .env.example and put real secrets in secret manager.",
        f"Build and test the {stack} application image locally.",
        f"Deploy the image to {service_name}.",
        "Attach custom domain and configure DNS records.",
        "Enable HTTPS with managed TLS certificate and enforce HTTP->HTTPS redirect.",
        "Configure application logs, infrastructure metrics, and alerting policies.",
        "Run health checks, smoke tests, and rollback drill.",
    ]


def _verification_steps():
    return [
        "Open https://api.example.com/health and confirm HTTP 200.",
        "Run curl -i https://api.example.com/health and verify response body and headers.",
        "Trigger one test request and confirm log entry appears in monitoring console.",
        "Check dashboard for CPU/RAM and error-rate metrics after deployment.",
    ]


def _rollback_steps(deployment):
    common = [
        "Identify previous known-good image tag.",
        "Redeploy previous image and verify /health endpoint.",
        "Restore previous DNS/service routing if needed.",
        "Capture incident timeline and create a postmortem action list.",
    ]
    if deployment in {"gcp_gke", "azure_aks"}:
        common.insert(1, "Use kubectl rollout undo deployment/app.")
    elif deployment == "aws_ecs_fargate":
        common.insert(1, "Update ECS service to previous task definition revision.")
    elif deployment == "aws_apprunner":
        common.insert(1, "Rollback App Runner service to previous image revision.")
    elif deployment == "aws_ec2":
        common.insert(1, "Restart systemd unit with previous release symlink on EC2.")
    return common


def _prerequisites(cloud, stack, deployment):
    items = [
        f"{cloud.upper()} account/project/subscription with billing enabled",
        "Git and Docker installed locally",
        "Cloud CLI configured and authenticated",
        "Access to DNS provider for custom domain",
        "Monitoring/alerting destination (email, Slack, PagerDuty, etc.)",
        f"Runtime prepared for {stack}",
    ]
    if deployment == "aws_ec2":
        items.append("EC2 SSH key pair and security group with least-privilege ports")
    if deployment in {"gcp_gke", "azure_aks"}:
        items.append("Kubernetes kubectl access to target cluster")
    return items


def _required_files(stack, cloud, deployment, deployment_steps):
    files = {
        ".env.example": _env_example(stack),
        "Dockerfile": _dockerfile_for_stack(stack),
        "docker-compose.yml": _docker_compose_for_stack(stack),
        "README_DEPLOYMENT.md": _readme_template(stack, cloud, deployment, deployment_steps),
        "scripts/deploy.sh": "#!/usr/bin/env bash\nset -euo pipefail\n\necho \"Run deployment commands for selected target here\"\n",
        "scripts/rollback.sh": "#!/usr/bin/env bash\nset -euo pipefail\n\necho \"Rollback to previous stable release\"\n",
    }

    if deployment == "aws_ec2":
        files["nginx.conf"] = _nginx_conf()
        files["deploy/systemd/app.service"] = _systemd_service(stack)
        files["scripts/ec2_bootstrap.sh"] = "#!/usr/bin/env bash\nset -euo pipefail\nsudo apt update && sudo apt install -y nginx\n"
    elif deployment == "aws_ecs_fargate":
        files["aws/ecs-task-definition.json"] = """\
{
  "family": "app-task",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "containerDefinitions": [
    {
      "name": "app",
      "image": "<account>.dkr.ecr.<region>.amazonaws.com/<repo>:<tag>",
      "portMappings": [{"containerPort": 8000, "protocol": "tcp"}],
      "essential": true
    }
  ]
}
"""
        files["aws/alb-notes.md"] = "# ALB Notes\n- Use target group health check path: /health\n- Attach ACM cert for HTTPS\n"
    elif deployment == "aws_apprunner":
        files["aws/apprunner.json"] = """\
{
  "ImageRepository": {
    "ImageIdentifier": "<account>.dkr.ecr.<region>.amazonaws.com/<repo>:<tag>",
    "ImageRepositoryType": "ECR"
  },
  "AutoDeploymentsEnabled": true
}
"""
    elif deployment == "gcp_cloud_run":
        files["gcp/cloudrun-service.yaml"] = """\
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  name: app
spec:
  template:
    spec:
      containers:
      - image: gcr.io/<project-id>/<image>:<tag>
        ports:
        - containerPort: 8000
"""
    elif deployment in {"gcp_gke", "azure_aks"}:
        dep, svc, ing = _k8s_manifests(stack)
        files["k8s/deployment.yaml"] = dep
        files["k8s/service.yaml"] = svc
        files["k8s/ingress.yaml"] = ing
    elif deployment == "azure_app_service":
        files["azure/webapp-deploy.sh"] = "#!/usr/bin/env bash\nset -euo pipefail\naz webapp up --name <app-name> --resource-group <rg>\n"
        files["azure/appsettings.sample.json"] = '{\n  "WEBSITES_PORT": "8000",\n  "APP_ENV": "production"\n}\n'

    return files


def generate_deployment_plan_payload(
    cloud,
    target,
    insights,
    features,
    ml_resources,
    llm_recommendation,
):
    normalized, error = validate_target(cloud, target)
    if error:
        return None, error

    stack = normalized["stack"]
    deployment = normalized["deployment"]
    cloud = normalized["cloud"]
    deployment_steps = _deployment_steps(cloud, stack, deployment)
    required_files = _required_files(stack, cloud, deployment, deployment_steps)

    llm_resources = None
    if isinstance(llm_recommendation, dict):
        llm_resources = llm_recommendation.get("predicted_resources")

    final_resources = llm_resources or ml_resources

    payload = {
        "target": normalized,
        "insights": insights,
        "features": features,
        "architecture": {
            "name": DEPLOYMENT_META[deployment]["name"],
            "cloud": cloud,
            "stack": stack,
            "deployment_key": deployment,
        },
        "prerequisites": _prerequisites(cloud, stack, deployment),
        "console_clickpath": DEPLOYMENT_META[deployment]["clickpath"],
        "commands": _commands_for_target(stack, cloud, deployment),
        "deployment_steps": deployment_steps,
        "verification_steps": _verification_steps(),
        "rollback_steps": _rollback_steps(deployment),
        "required_files": required_files,
        "recommended_resources": {
            "ml_prediction": ml_resources,
            "llm_prediction": llm_resources,
            "final": final_resources,
            "os_recommendation": (llm_recommendation or {}).get("os_recommendation"),
        },
        "guide_source": "api+fallback",
    }
    return payload, None
