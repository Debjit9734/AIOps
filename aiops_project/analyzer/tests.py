import os
import tempfile
from unittest.mock import patch

from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient

from analyzer.utils.analyzer_utils import analyze_files
from analyzer.utils.deployment_plans import (
    generate_deployment_plan_payload,
    validate_target,
)


class DeploymentPlanBuilderTests(TestCase):
    def test_validate_target_rejects_cloud_mismatch(self):
        _, error = validate_target(
            "aws",
            {
                "stack": "django",
                "deployment": "gcp_cloud_run",
            },
        )
        self.assertIsNotNone(error)

    def test_generate_payload_contains_visual_sections(self):
        payload, error = generate_deployment_plan_payload(
            cloud="aws",
            target={"stack": "django", "deployment": "aws_ec2"},
            insights={"framework": "Django", "dependencies": ["django", "gunicorn"]},
            features={"total_files": 10, "total_lines": 1000, "dependency_count": 2, "security_score": 0.7},
            ml_resources={"cpu": 1.5, "ram": 2.0, "storage": 8.0},
            llm_recommendation={"predicted_resources": None, "os_recommendation": "ubuntu:22.04"},
        )
        self.assertIsNone(error)
        self.assertIn("deployment_steps", payload)
        self.assertIn("prerequisites", payload)
        self.assertIn("console_clickpath", payload)
        self.assertIn("commands", payload)
        self.assertIn("verification_steps", payload)
        self.assertIn("rollback_steps", payload)
        self.assertIn("required_files", payload)
        self.assertIn(".env.example", payload["required_files"])
        self.assertIn("README_DEPLOYMENT.md", payload["required_files"])
        self.assertIn("nginx.conf", payload["required_files"])
        self.assertIn("deploy/systemd/app.service", payload["required_files"])

    def test_generate_payload_for_k8s_target(self):
        payload, error = generate_deployment_plan_payload(
            cloud="gcp",
            target={"stack": "fastapi", "deployment": "gcp_gke"},
            insights={"framework": "FastAPI", "dependencies": ["fastapi", "uvicorn"]},
            features={"total_files": 8, "total_lines": 500, "dependency_count": 2, "security_score": 0.9},
            ml_resources={"cpu": 1.0, "ram": 1.5, "storage": 6.0},
            llm_recommendation={},
        )
        self.assertIsNone(error)
        self.assertIn("k8s/deployment.yaml", payload["required_files"])
        self.assertIn("k8s/service.yaml", payload["required_files"])
        self.assertIn("k8s/ingress.yaml", payload["required_files"])


class AnalyzerApiCacheFlowTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        cache.clear()

    @patch("analyzer.views.analyze_security", return_value=3)
    @patch("analyzer.views.extract_features", return_value={"total_files": 4, "total_lines": 200, "dependency_count": 2})
    @patch("analyzer.views.analyze_files", return_value={"framework": "Django", "dependencies": ["django", "requests"]})
    @patch("analyzer.views.save_training_row")
    @patch("analyzer.views.download_repo_as_zip", return_value=("C:/tmp/repo", None))
    def test_analyze_repo_caches_analysis_and_returns_id(
        self,
        download_repo_mock,
        save_training_row_mock,
        analyze_files_mock,
        extract_features_mock,
        analyze_security_mock,
    ):
        response = self.client.post(
            "/api/analyze/",
            {"repo_url": "https://github.com/example/repo"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("analysis_id", response.data)
        self.assertEqual(response.data["insights"]["framework"], "Django")

        cached = cache.get(f"analysis:{response.data['analysis_id']}")
        self.assertIsNotNone(cached)
        self.assertEqual(cached["repo_url"], "https://github.com/example/repo")
        self.assertEqual(cached["repo_path"], "C:/tmp/repo")
        self.assertEqual(cached["features"]["security_score"], 3)

        download_repo_mock.assert_called_once()
        analyze_files_mock.assert_called_once()
        extract_features_mock.assert_called_once()
        analyze_security_mock.assert_called_once()
        save_training_row_mock.assert_called_once_with(
            {"total_files": 4, "total_lines": 200, "dependency_count": 2, "security_score": 3}
        )

    @patch("analyzer.views.generate_hf_recommendation", return_value={"predicted_resources": None, "os_recommendation": "ubuntu:22.04", "deployment_steps": ["step"], "configuration_files_needed": ["Dockerfile"]})
    @patch("analyzer.views.predict_resources", return_value={"cpu": 1.0, "ram": 2.0, "storage": 5.0})
    def test_recommend_endpoint_uses_cached_analysis(self, predict_resources_mock, llm_mock):
        cache.set(
            "analysis:test-id",
            {
                "repo_url": "https://github.com/example/repo",
                "repo_path": "C:/tmp/repo",
                "insights": {"framework": "Django", "dependencies": ["django"]},
                "features": {"total_files": 4, "total_lines": 200, "dependency_count": 1, "security_score": 2},
            },
            1800,
        )

        response = self.client.post(
            "/api/recommend-ml/",
            {"analysis_id": "test-id", "cloud": "aws"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["analysis_id"], "test-id")
        self.assertEqual(response.data["repo_url"], "https://github.com/example/repo")
        self.assertEqual(response.data["predicted_resources"]["cpu"], 1.0)
        predict_resources_mock.assert_called_once()
        llm_mock.assert_called_once()

    def test_cached_endpoints_return_404_for_unknown_analysis_id(self):
        recommend_response = self.client.post(
            "/api/recommend-ml/",
            {"analysis_id": "missing-id", "cloud": "aws"},
            format="json",
        )
        plan_response = self.client.post(
            "/api/deployment-plan/",
            {
                "analysis_id": "missing-id",
                "cloud": "aws",
                "target": {"stack": "django", "deployment": "aws_ec2"},
            },
            format="json",
        )

        self.assertEqual(recommend_response.status_code, 404)
        self.assertEqual(plan_response.status_code, 404)
        self.assertIn("Analysis not found", recommend_response.data["error"])
        self.assertIn("Analysis not found", plan_response.data["error"])


class AnalyzeFilesDetectionTests(TestCase):
    def test_detects_flutter_first_and_parses_dependency_blocks(self):
        with tempfile.TemporaryDirectory() as repo_dir:
            with open(os.path.join(repo_dir, "pubspec.yaml"), "w", encoding="utf-8") as f:
                f.write(
                    "name: sample_app\n"
                    "dependencies:\n"
                    "  flutter: ^3.0.0\n"
                    "  http: ^1.2.0\n"
                    "dev_dependencies:\n"
                    "  flutter_test: ^1.0.0\n"
                )

            result = analyze_files(repo_dir)

        self.assertEqual(result["framework"], "Flutter")
        self.assertEqual(
            result["dependencies"],
            ["flutter: ^3.0.0", "http: ^1.2.0", "flutter_test: ^1.0.0"],
        )

    def test_detects_node_framework_from_package_json(self):
        with tempfile.TemporaryDirectory() as repo_dir:
            with open(os.path.join(repo_dir, "package.json"), "w", encoding="utf-8") as f:
                f.write(
                    '{'
                    '"dependencies": {"react": "^18.0.0"}, '
                    '"devDependencies": {"vite": "^5.0.0"}'
                    '}'
                )

            result = analyze_files(repo_dir)

        self.assertEqual(result["framework"], "React")
        self.assertEqual(result["dependencies"], ["react", "vite"])

    def test_detects_java_and_extracts_artifact_ids(self):
        with tempfile.TemporaryDirectory() as repo_dir:
            with open(os.path.join(repo_dir, "pom.xml"), "w", encoding="utf-8") as f:
                f.write(
                    "<project>"
                    "<artifactId>demo-app</artifactId>"
                    "<dependencies>"
                    "<dependency><artifactId>spring-boot-starter-web</artifactId></dependency>"
                    "<dependency><artifactId>lombok</artifactId></dependency>"
                    "</dependencies>"
                    "</project>"
                )

            result = analyze_files(repo_dir)

        self.assertEqual(result["framework"], "Spring Boot")
        self.assertIn("spring-boot-starter-web", result["dependencies"])
        self.assertIn("lombok", result["dependencies"])

    def test_detects_go_requirements(self):
        with tempfile.TemporaryDirectory() as repo_dir:
            with open(os.path.join(repo_dir, "go.mod"), "w", encoding="utf-8") as f:
                f.write(
                    "module example.com/app\n\n"
                    "require github.com/gin-gonic/gin v1.9.0\n"
                    "require (\n"
                    "    golang.org/x/net v0.20.0\n"
                    ")\n"
                )

            result = analyze_files(repo_dir)

        self.assertEqual(result["framework"], "Go")
        self.assertEqual(
            result["dependencies"],
            [
                "require github.com/gin-gonic/gin v1.9.0",
                "golang.org/x/net v0.20.0",
            ],
        )

    def test_detects_nested_node_project(self):
        with tempfile.TemporaryDirectory() as repo_dir:
            nested_dir = os.path.join(repo_dir, "nested")
            os.makedirs(nested_dir, exist_ok=True)
            with open(os.path.join(nested_dir, "package.json"), "w", encoding="utf-8") as f:
                f.write('{"dependencies": {"next": "^14.0.0"}}')

            result = analyze_files(repo_dir)

        self.assertEqual(result["framework"], "Next.js")
        self.assertEqual(result["dependencies"], ["next"])

    def test_detects_django_from_manage_py_without_requirements(self):
        with tempfile.TemporaryDirectory() as repo_dir:
            project_dir = os.path.join(repo_dir, "todo")
            os.makedirs(project_dir, exist_ok=True)
            with open(os.path.join(repo_dir, "manage.py"), "w", encoding="utf-8") as f:
                f.write("import os\nos.environ.setdefault('DJANGO_SETTINGS_MODULE', 'todo.settings')\n")
            with open(os.path.join(project_dir, "settings.py"), "w", encoding="utf-8") as f:
                f.write("INSTALLED_APPS = ['django.contrib.admin']\n")

            result = analyze_files(repo_dir)

        self.assertEqual(result["framework"], "Django")
        self.assertEqual(result["dependencies"], [])

    def test_prefers_python_framework_over_nested_package_json(self):
        with tempfile.TemporaryDirectory() as repo_dir:
            frontend_dir = os.path.join(repo_dir, "frontend")
            os.makedirs(frontend_dir, exist_ok=True)
            with open(os.path.join(repo_dir, "manage.py"), "w", encoding="utf-8") as f:
                f.write("import os\nos.environ.setdefault('DJANGO_SETTINGS_MODULE', 'todo.settings')\n")
            with open(os.path.join(repo_dir, "requirements.txt"), "w", encoding="utf-8") as f:
                f.write("django==5.0.0\n")
            with open(os.path.join(frontend_dir, "package.json"), "w", encoding="utf-8") as f:
                f.write('{"dependencies": {"react": "^18.0.0"}}')

            result = analyze_files(repo_dir)

        self.assertEqual(result["framework"], "Django")
        self.assertIn("django==5.0.0", result["dependencies"])

    def test_detects_laravel_before_package_json(self):
        with tempfile.TemporaryDirectory() as repo_dir:
            frontend_dir = os.path.join(repo_dir, "resources")
            os.makedirs(frontend_dir, exist_ok=True)
            with open(os.path.join(repo_dir, "composer.json"), "w", encoding="utf-8") as f:
                f.write(
                    '{'
                    '"name": "laravel/laravel", '
                    '"require": {"php": "^8.2", "laravel/framework": "^11.0"}, '
                    '"require-dev": {"phpunit/phpunit": "^11.0"}'
                    '}'
                )
            with open(os.path.join(frontend_dir, "package.json"), "w", encoding="utf-8") as f:
                f.write('{"dependencies": {"vite": "^5.0.0"}}')

            result = analyze_files(repo_dir)

        self.assertEqual(result["framework"], "Laravel")
        self.assertIn("laravel/framework", result["dependencies"])
