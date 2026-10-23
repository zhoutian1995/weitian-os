"""Install the anonymous event patch as a versioned static release with guarded rollback."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess

REMOTE = r'''
import datetime, fcntl, hashlib, json, os, shutil, subprocess, sys
from pathlib import Path
def release_metadata(base, patch_source_git_sha, tag, original_release, script_sha, deployed_at):
    result = dict(base)
    result.update(release=tag, gitSha=base.get("gitSha"), patch_source_git_sha=patch_source_git_sha,
                  base_release=str(original_release), tree_state="base-plus-uncommitted-geo-events-patch", deployed_at=deployed_at,
                  patches={**base.get("patches", {}), "geo-events.js": script_sha})
    return result

p = json.load(sys.stdin)
current = Path("/srv/weitian-os/current")
with open("/var/lock/weitian-os-deploy.lock", "a") as lease:
    fcntl.flock(lease, fcntl.LOCK_EX | fcntl.LOCK_NB)
    original_release = current.resolve()
    if str(original_release) != p["expected_release"]:
        raise RuntimeError("Active release changed; refusing to deploy over another owner")
    site = Path("/etc/nginx/sites-enabled/willeai-landing")
    text = site.read_text()
    if "root /srv/weitian-os/current;" not in text:
        raise RuntimeError("Unexpected website root")
    tag = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-geo-events-" + p["script_sha256"][:12]
    backup = Path("/var/backups/weitian-geo-events") / tag
    backup.mkdir(parents=True, exist_ok=False)
    release = Path("/srv/weitian-os/releases") / tag
    snippet = Path("/etc/nginx/snippets/geo-events-server.conf")
    http = Path("/etc/nginx/conf.d/geo-events.conf")
    old = {str(file): file.read_bytes() if file.exists() else None for file in (site, snippet, http)}
    for file, content in old.items():
        if content is not None:
            (backup / Path(file).name).write_bytes(content)
    (backup / "original-release.txt").write_text(str(original_release))
    new = {}
    try:
        shutil.copytree(original_release, release)
        (release / "assets").mkdir(exist_ok=True)
        (release / "assets/geo-events.js").write_text(p["script"])
        original_metadata = original_release / "release.json"
        base = json.loads(original_metadata.read_text()) if original_metadata.is_file() else {}
        metadata = release_metadata(base, p["patch_source_git_sha"], tag, original_release, p["script_sha256"],
                                    datetime.datetime.now(datetime.timezone.utc).isoformat())
        (release / "release.json").write_text(json.dumps(metadata, indent=2))
        (release / "healthz.txt").write_text(tag + "\n")
        for directory, _, files in os.walk(release):
            os.chmod(directory, 0o755)
            for name in files: os.chmod(Path(directory) / name, 0o644)
        include = "    include /etc/nginx/snippets/geo-events-server.conf;\n"
        if include not in text:
            if text.count("    index index.html;\n") != 1: raise RuntimeError("Ambiguous Nginx include point")
            text = text.replace("    index index.html;\n", "    index index.html;\n" + include)
        server = p["server"].replace('/assets/geo-events.js"', '/assets/geo-events.js?v=' + p["script_sha256"][:12] + '"')
        new = {str(site): text.encode(), str(snippet): server.encode(), str(http): p["http"].encode()}
        for file, content in new.items(): Path(file).write_bytes(content)
        subprocess.run(["nginx", "-t"], check=True, capture_output=True)
        if current.resolve() != original_release: raise RuntimeError("Another deployment changed current during preparation")
        pending = current.with_name(".current-" + tag)
        pending.symlink_to(release)
        pending.replace(current)
        subprocess.run(["nginx", "-s", "reload"], check=True, capture_output=True)
        print(json.dumps({"status": "DEPLOYED", "release": str(release), "previous": str(original_release), "backup": str(backup), "script_sha256": p["script_sha256"]}))
    except Exception:
        if current.resolve() == release:
            pending = current.with_name(".rollback-" + tag)
            pending.symlink_to(original_release)
            pending.replace(current)
        conflicts = []
        for file, content in old.items():
            destination = Path(file)
            if destination.exists() and destination.read_bytes() != new.get(file):
                conflicts.append(file)
                continue
            if content is None: destination.unlink(missing_ok=True)
            else: destination.write_bytes(content)
        if not conflicts:
            subprocess.run(["nginx", "-t"], check=True, capture_output=True)
            subprocess.run(["nginx", "-s", "reload"], check=True, capture_output=True)
        raise
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected-release", required=True)
    parser.add_argument("--receipt", required=True)
    args = parser.parse_args()
    path = Path(args.receipt)
    if (not os.path.ismount("/Volumes/1TB-SSD") or not Path("/Volumes/1TB-SSD/.wille-work-storage").is_file()
            or not path.resolve().is_relative_to(Path("/Volumes/1TB-SSD/WilleSpace-Work").resolve())):
        raise ValueError("Deployment and receipt require the real external SSD")
    with path.open("x", encoding="utf-8") as stream:
        json.dump({"status": "RUNNING", "expected_release": args.expected_release}, stream)
    root = Path(__file__).parents[1]
    script = (root / "assets/geo-events.js").read_text()
    git = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    payload = {"expected_release": args.expected_release, "patch_source_git_sha": git, "script": script,
               "script_sha256": hashlib.sha256(script.encode()).hexdigest(),
               "http": (root / "deploy/geo-events-http.conf").read_text(), "server": (root / "deploy/geo-events-server.conf").read_text()}
    result = subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=12", "dmit-vps", "python3", "-c", shlex.quote(REMOTE)],
                            input=json.dumps(payload), capture_output=True, text=True, timeout=120)
    receipt = {"returncode": result.returncode, "stdout": result.stdout, "stderr": result.stderr,
               "script_sha256": payload["script_sha256"], "expected_release": args.expected_release}
    path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8")
    print(result.stdout or result.stderr)
    raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()
