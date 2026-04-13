import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class DeployConfigTests(unittest.TestCase):
    def test_backend_uses_bridge_network_and_port_mapping(self):
        compose_text = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
        self.assertIn("backend:", compose_text)
        self.assertIn('      - "8000:8000"', compose_text)
        self.assertNotIn("network_mode: host", compose_text)

    def test_frontend_proxies_api_to_backend_service(self):
        nginx_text = (ROOT / "frontend" / "nginx.conf").read_text(encoding="utf-8")
        self.assertIn("proxy_pass http://backend:8000/api/;", nginx_text)

    def test_frontend_does_not_need_host_gateway_mapping(self):
        compose_text = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
        self.assertNotIn("host.docker.internal:host-gateway", compose_text)


if __name__ == "__main__":
    unittest.main()
