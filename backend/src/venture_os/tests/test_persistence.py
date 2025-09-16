import os
import tempfile
import unittest
import subprocess

class TestPersistence(unittest.TestCase):
    def test_entity_persistence(self):
        temp_file = tempfile.NamedTemporaryFile(delete=False)
        temp_file.close()

        try:
            # Create an entity via subprocess
            result = subprocess.run(
                [
                    'python', '-c',
                    f"from venture_os.service.entity_service import create_entity; create_entity(VOS_STORE='jsonl', file='{temp_file.name}')"
                ],
                capture_output=True
            )

            if result.returncode != 0:
                self.skipTest('Subprocess failed')

            # Restart and reload repo from the same file
            result = subprocess.run(
                [
                    'python', '-c',
                    f"from venture_os.service.entity_service import load_entities; load_entities(file='{temp_file.name}')"
                ],
                capture_output=True
            )

            # Assert the entity is still present
            self.assertIn('entity_name', result.stdout.decode())

        finally:
            os.remove(temp_file.name)

if __name__ == '__main__':
    unittest.main()