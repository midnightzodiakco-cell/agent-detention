import json
import tempfile
import unittest
from pathlib import Path
import importlib.util

HERE = Path(__file__).resolve().parent.parent / "scripts"
spec = importlib.util.spec_from_file_location("detention_protocol", HERE / "detention_protocol.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class DetentionProtocolTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "state.json"

    def tearDown(self):
        self.tmp.cleanup()

    def fail(self, capacity="accuracy", requirement="preserve", eligible=True):
        return mod.record_failure(self.path, "agent", capacity, requirement, "unchanged", "changed", eligible=eligible)

    def test_three_identical_failures_open_detention(self):
        self.assertFalse(self.fail()["detention_triggered"])
        self.assertFalse(self.fail()["detention_triggered"])
        result = self.fail()
        self.assertTrue(result["detention_triggered"])
        self.assertEqual(result["active_detention"], "DET-0001")

    def test_unrelated_capacity_does_not_combine(self):
        self.fail("a"); self.fail("a")
        result = self.fail("b")
        self.assertFalse(result["detention_triggered"])
        self.assertEqual(result["consecutive"], 1)

    def test_ineligible_failure_does_not_increment(self):
        self.fail(eligible=False)
        result = self.fail()
        self.assertEqual(result["consecutive"], 1)

    def test_release_requires_practice_quota(self):
        for _ in range(3): self.fail()
        with self.assertRaises(ValueError): mod.release(self.path, "agent", "DET-0001")
        with self.assertRaises(ValueError): mod.practice(self.path, "agent", "DET-0001", "PASS")
        mod.investigate(self.path, "agent", "DET-0001", "assignment", "failed response", "accurate response", "exact", "how", "why", "causes", "prevention", "overwrote")
        for _ in range(99): mod.practice(self.path, "agent", "DET-0001", "PASS")
        self.assertNotEqual(mod.status(self.path, "agent")["detentions"][0].get("competency"), "PASS")
        mod.practice(self.path, "agent", "DET-0001", "PASS")
        self.assertEqual(mod.release(self.path, "agent", "DET-0001")["state"], "NORMAL")

    def test_atomic_state_is_valid_json(self):
        self.fail(); data = json.loads(self.path.read_text())
        self.assertEqual(data["schema_version"], 1)
        self.assertEqual(len(data["events"]), 1)

if __name__ == "__main__":
    unittest.main()
