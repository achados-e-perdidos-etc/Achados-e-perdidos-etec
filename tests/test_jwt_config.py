"""Evita publicar novamente com segredo JWT ausente ou fraco."""
import os
import subprocess
import sys
import unittest
from pathlib import Path


class JWTConfigTests(unittest.TestCase):
    def test_servidor_rejeita_segredo_ausente_ou_curto(self):
        for secret in ['', 'curto']:
            env = dict(os.environ, JWT_SECRET=secret, DATABASE_URL='')
            result = subprocess.run(
                [sys.executable, '-c', 'import config'], env=env,
                cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('Configure JWT_SECRET', result.stderr)
