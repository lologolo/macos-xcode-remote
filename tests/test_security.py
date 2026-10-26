"""Security regressions without requiring a macOS host.

Run: python -m unittest discover -s tests -v
Real crypto tests require age and age-keygen on PATH.
"""
import contextlib
import importlib.util
import io
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


class RustDeskTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.state = Path(self.temp.name)
        self.creds = {"macos_user": "remoteadmin", "macos_password": "MAC-SENTINEL",
                      "rustdesk_password": "RUSTDESK-SENTINEL"}
        (self.state / "credentials.json").write_text(json.dumps(self.creds))
        self.mod = module("configure-rustdesk")
        env = patch.dict(os.environ, {"STATE_DIR": str(self.state)})
        env.start()
        self.addCleanup(env.stop)

    def test_password_error_with_zero_exit_status_is_rejected(self):
        with patch.object(self.mod, "command", return_value="Installation and administrative privileges required!"), \
             patch.object(self.mod.time, "sleep"), self.assertRaises(RuntimeError):
            self.mod.main()
        self.assertNotIn("rustdesk_id", json.loads((self.state / "credentials.json").read_text()))

    def test_option_readback_mismatch_prevents_publication(self):
        def command(*args):
            return "Done!" if args[0] == "--password" else ""
        with patch.object(self.mod, "command", side_effect=command), \
             patch.object(self.mod.time, "sleep"), self.assertRaises(RuntimeError):
            self.mod.main()

    def test_settings_and_id_verified(self):
        settings = {}
        def command(*args):
            if args[0] == "--password":
                return "Done!"
            if args[0] == "--get-id":
                return "123 456 789"
            if len(args) == 3:
                settings[args[1]] = args[2]
                return ""
            return settings[args[1]]
        output = io.StringIO()
        with patch.object(self.mod, "command", side_effect=command), contextlib.redirect_stdout(output):
            self.mod.main()
        data = json.loads((self.state / "credentials.json").read_text())
        self.assertEqual(data["rustdesk_id"], "123456789")
        self.assertEqual(settings["approve-mode"], "password")
        self.assertEqual(settings["verification-method"], "use-permanent-password")
        for key in ("direct-server", "enable-lan-discovery", "enable-tunnel", "enable-terminal"):
            self.assertEqual(settings[key], "N")
        self.assertNotIn("RUSTDESK-SENTINEL", output.getvalue())
        self.assertNotIn("MAC-SENTINEL", output.getvalue())

    def test_invalid_id_is_rejected(self):
        settings = {}
        def command(*args):
            if args[0] == "--password": return "Done!"
            if args[0] == "--get-id": return "error: unavailable"
            if len(args) == 3:
                settings[args[1]] = args[2]
                return ""
            return settings[args[1]]
        with patch.object(self.mod, "command", side_effect=command), \
             patch.object(self.mod.time, "sleep"), self.assertRaises(RuntimeError):
            self.mod.main()


class ChromePreparationTests(unittest.TestCase):
    def test_existing_gui_job_is_not_bootstrapped_again(self):
        mod = module("prepare-crd")
        with patch.object(mod, "launchctl", return_value=0) as command:
            mod.ensure_job("gui/501", "org.chromium.chromoting", Path("/installed.plist"))
        self.assertEqual([call.args[0] for call in command.call_args_list], ["enable", "print"])
        self.assertFalse(any(call.kwargs.get("privileged") for call in command.call_args_list))

    def test_missing_agent_is_registered_in_gui_domain(self):
        mod = module("prepare-crd")
        with patch.object(mod, "launchctl", side_effect=[0, 1, 0, 0]) as command:
            mod.ensure_job("gui/501", "org.chromium.chromoting", Path("/installed.plist"))
        self.assertEqual(command.call_args_list[2].args, ("bootstrap", "gui/501", str(Path("/installed.plist"))))

    def test_failed_registration_is_reported(self):
        mod = module("prepare-crd")
        with patch.object(mod, "launchctl", side_effect=[0, 1, 1, 1]), self.assertRaises(RuntimeError):
            mod.ensure_job("gui/501", "org.chromium.chromoting", Path("/installed.plist"))

    def test_unexpected_native_host_paths_are_rejected(self):
        mod = module("prepare-crd")
        with tempfile.TemporaryDirectory() as temp:
            manifest = Path(temp) / "manifest.json"
            for name in ("/tmp/untrusted", "relative-host", "/Library/PrivilegedHelperTools/../untrusted"):
                manifest.write_text(json.dumps({"name": "com.google.chrome.remote_desktop", "path": name}))
                with self.assertRaises(RuntimeError):
                    mod.native_host_path(manifest)

    def test_google_manifest_native_path_is_used_without_guessing_a_filename(self):
        mod = module("prepare-crd")
        with tempfile.TemporaryDirectory() as temp:
            manifest = Path(temp) / "manifest.json"
            host = "/Library/PrivilegedHelperTools/ChromeRemoteDesktopHost.app/Contents/MacOS/Native Host.app/Contents/MacOS/native_messaging_host"
            manifest.write_text(json.dumps({"name": "com.google.chrome.remote_desktop", "path": host}))
            self.assertEqual(mod.native_host_path(manifest).as_posix(), host)

    def test_permission_wizard_runs_without_sudo_and_keeps_output_private(self):
        mod = module("prepare-crd")
        with tempfile.TemporaryDirectory() as temp, patch.object(mod.subprocess, "Popen") as process:
            process.return_value.pid = 123
            host = Path("/installed-native-host")
            mod.open_wizard(host, Path(temp))
            self.assertEqual(process.call_args.args[0], [str(host), "--check-permission"])
            self.assertEqual(Path(process.call_args.kwargs["stdout"].name).name, "crd-permission-wizard.log")
            self.assertEqual((Path(temp) / "crd-permission-wizard.pid").read_text(), "123")


class AdminTests(unittest.TestCase):
    def test_creation_failure_is_not_ignored(self):
        mod = module("create-admin")
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, {"STATE_DIR": temp}), \
             patch.object(mod.subprocess, "run", return_value=subprocess.CompletedProcess([], 1)), \
             patch.object(mod, "run", side_effect=RuntimeError("failure")), \
             contextlib.redirect_stdout(io.StringIO()), self.assertRaises(RuntimeError):
            mod.main()
        # A failed creation cannot reach credential publication.

    def test_existing_user_is_not_reset(self):
        mod = module("create-admin")
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, {"STATE_DIR": temp}), \
             patch.object(mod.subprocess, "run", return_value=subprocess.CompletedProcess([], 0)), \
             patch.object(mod, "run") as command, self.assertRaises(RuntimeError):
            mod.main()
        command.assert_not_called()


class CaptureStartupTests(unittest.TestCase):
    def test_capture_inherits_workflow_instead_of_launchd(self):
        setup = (ROOT / "scripts/setup-rustdesk.sh").read_text()
        start = (ROOT / "scripts/start-rustdesk.sh").read_text()
        self.assertIn('"$CLI" --server >"$STATE_DIR/rustdesk-server.log" 2>&1 &', start)
        self.assertIn('"$CONSOLE_UID" == "$(id -u)"', start)
        self.assertIn('kill -0 "$SERVER_PID"', start)
        self.assertNotIn("launchctl bootstrap", setup + start)
        self.assertNotIn("open -a", setup + start)
        self.assertNotIn("sudo", '\n'.join(line for line in start.splitlines() if not line.startswith('#')))

    def test_capture_errors_detected_without_disclosing_log_content(self):
        mod = module("rustdesk-health")
        with tempfile.TemporaryDirectory() as temp:
            log = Path(temp) / "server.log"
            log.write_text("PRIVATE-ID-AND-ADDRESS: Failed to create capturer\n")
            self.assertIs(mod.capture_error_present([log]), True)
            log.write_text("PRIVATE-ID-AND-ADDRESS: normal operation\n")
            self.assertIs(mod.capture_error_present([log]), False)
            self.assertIs(mod.capture_error_present([Path(temp) / "missing.log"]), False)

    def test_health_warning_never_reprints_private_logs(self):
        mod = module("rustdesk-health")
        with tempfile.TemporaryDirectory() as temp:
            state = Path(temp)
            (state / "rustdesk-server.pid").write_text("123")
            (state / "rustdesk-server.log").write_text("PRIVATE-SENTINEL Failed to create capturer")
            output = io.StringIO()
            with patch.dict(os.environ, {"STATE_DIR": str(state)}), \
                 patch.object(mod.os, "kill"), patch.object(mod, "display_count", return_value=0), \
                 patch.object(mod.Path, "home", return_value=state), contextlib.redirect_stdout(output):
                mod.main()
            self.assertIn("no active display", output.getvalue())
            self.assertIn("screen-capture failure", output.getvalue())
            self.assertNotIn("PRIVATE-SENTINEL", output.getvalue())


@unittest.skipUnless(shutil.which("age") and shutil.which("age-keygen"), "Install age for real crypto tests")
class EncryptionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.state = Path(self.temp.name)
        (self.state / "public").mkdir()
        self.key = self.state / "identity.txt"
        subprocess.run(["age-keygen", "-o", str(self.key)], capture_output=True, check=True)
        self.recipient = subprocess.run(["age-keygen", "-y", str(self.key)], capture_output=True,
                                        text=True, check=True).stdout.strip()
        self.source = self.state / "credentials.json"
        self.source.write_text(json.dumps({"macos_user": "remoteadmin", "macos_password": "MAC-SENTINEL",
                                          "rustdesk_id": "123456789", "rustdesk_password": "RD-SENTINEL"}))
        self.env = os.environ | {"STATE_DIR": str(self.state), "AGE_RECIPIENT": self.recipient,
                                 "GITHUB_RUN_ID": "123", "GITHUB_RUN_ATTEMPT": "1"}

    def execute(self):
        return subprocess.run([os.sys.executable, str(ROOT / "scripts" / "encrypt-connection.py")],
                              env=self.env, capture_output=True, text=True)

    def test_roundtrip_and_wrong_key_rejection(self):
        result = self.execute()
        self.assertEqual(result.returncode, 0, result.stderr)
        target = self.state / "public" / "connection-info.txt.age"
        ciphertext = target.read_bytes()
        for value in (b"MAC-SENTINEL", b"RD-SENTINEL", b"123456789"):
            self.assertNotIn(value, ciphertext)
        self.assertFalse(self.source.exists())
        self.assertEqual(len(list((self.state / "public").iterdir())), 1)
        plain = subprocess.run(["age", "-d", "-i", str(self.key), str(target)], capture_output=True, check=True).stdout
        self.assertIn(b"MAC-SENTINEL", plain)
        self.assertIn(b"RD-SENTINEL", plain)
        wrong = self.state / "wrong-key.txt"
        subprocess.run(["age-keygen", "-o", str(wrong)], capture_output=True, check=True)
        result = subprocess.run(["age", "-d", "-i", str(wrong), str(target)], capture_output=True)
        self.assertNotEqual(result.returncode, 0)

    def test_invalid_recipient_fails_closed_and_removes_plaintext(self):
        self.env["AGE_RECIPIENT"] = "invalid"
        result = self.execute()
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.source.exists())
        self.assertFalse(list((self.state / "public").iterdir()))
        self.assertNotIn("MAC-SENTINEL", result.stdout + result.stderr)
        self.assertNotIn("RD-SENTINEL", result.stdout + result.stderr)


class WorkflowTests(unittest.TestCase):
    def test_only_ciphertext_is_uploaded(self):
        text = (ROOT / ".github/workflows/rustdesk-session.yml").read_text()
        self.assertIn("/public/connection-info.txt.age", text)
        self.assertEqual(text.count("uses: actions/upload-artifact@"), 1)
        self.assertNotIn("secrets.", text)
        self.assertNotIn("actions/cache", text)
        self.assertIn("persist-credentials: false", text)
        self.assertIn("contents: read", text)
        self.assertIn("github.triggering_actor == github.repository_owner", text)
        self.assertIn("github.actor == github.repository_owner", text)
        self.assertIn("github.event.repository.default_branch", text)
        self.assertNotIn("pull_request", text)
        self.assertNotIn("schedule:", text)
        self.assertIn("if: always()", text)

    def test_no_legacy_credential_publishing_workflows_remain(self):
        workflows = list((ROOT / ".github/workflows").glob("*.yml"))
        self.assertEqual([p.name for p in workflows], ["rustdesk-session.yml"])


if __name__ == "__main__":
    unittest.main()
