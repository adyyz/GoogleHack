"""Runtime startup checks without a container engine, cloud client or provider."""
from types import SimpleNamespace

import pytest

from backend.container import server_options


def test_container_listens_on_cloud_port_and_preserves_local_loopback():
    assert server_options(SimpleNamespace(mode="cloud"), "9090") == {"app": "backend.api:app", "host": "0.0.0.0", "port": 9090}
    assert server_options(SimpleNamespace(mode="local"), "8080")["host"] == "127.0.0.1"
    for port in ["", "0", "65536", "-1", "8080.0", " 8080", "٨٠٨٠"]:
        with pytest.raises(ValueError, match="PORT"): server_options(SimpleNamespace(mode="cloud"), port)
