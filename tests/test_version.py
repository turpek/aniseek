from __future__ import annotations

import aniseek


def test_package_version_defined():
    """Valida se a constante __version__ do pacote aniseek está definida corretamente."""
    version = aniseek.__version__

    assert isinstance(version, str)
    assert version == "0.1.0a1"
