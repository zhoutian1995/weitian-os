"""Install the anonymous event patch as a versioned static release with guarded rollback."""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess

PROFILES = {
    "personal": {"host": "dmit-vps", "root": "/srv/weitian-os", "lock": "/var/lock/weitian-os-deploy.lock",
                 "site": "/etc/nginx/sites-enabled/willeai-landing", "snippet": "/etc/nginx/snippets/geo-events-server.conf",
                 "http": "/etc/nginx/conf.d/geo-events.conf", "backup": "/var/backups/weitian-geo-events", "nginx": ["nginx"]},
    "company": {"host": "my-server", "root": "/srv/weiling-company", "lock": "/srv/weiling-company/.static-deploy.lock",
                "site": "/www/server/panel/vhost/nginx/willeai.cn.conf", "snippet": "/srv/weiling-company/nginx/geo-events-server.conf",
                "http": "/www/server/panel/vhost/nginx/geo-events-http.conf", "backup": "/srv/weiling-company/deploy-backups",
                "nginx": ["/usr/bin/nginx", "-c", "/www/server/nginx/conf/nginx.conf"]},
}

REMOTE = r'''
import base64, datetime, fcntl, hashlib, json, os, shutil, stat, subprocess, sys, tempfile
from pathlib import Path

def config_bytes(path):
    return path.read_bytes() if path.exists() else None

def atomic_config(path, content, expected):
    destination = path.resolve(strict=False)
    if config_bytes(destination) != expected:
        raise RuntimeError("Nginx configuration changed before replacement: " + str(path))
    destination.parent.mkdir(parents=True, exist_ok=True)
    previous = destination.stat() if destination.exists() else None
    fd, name = tempfile.mkstemp(prefix=".geo-events-", dir=str(destination.parent))
    temporary = Path(name)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.chmod(stat.S_IMODE(previous.st_mode) if previous else 0o644)
        if previous and os.geteuid() == 0:
            os.chown(str(temporary), previous.st_uid, previous.st_gid)
        if path.resolve(strict=False) != destination or config_bytes(destination) != expected:
            raise RuntimeError("Nginx configuration changed during preparation: " + str(path))
        os.replace(str(temporary), str(destination))
    finally:
        if temporary.exists():
            temporary.unlink()

def restore_config(path, old, intended):
    current = config_bytes(path)
    if current == old:
        return True
    if current != intended:
        return False
    if old is None:
        path.resolve(strict=False).unlink()
    else:
        atomic_config(path, old, intended)
    return True

def validate_static_base(base, files, expected):
    if set(files) != set(expected):
        raise ValueError("Static input baseline does not cover the exact patch")
    for name in files:
        source = base / name
        source.resolve(strict=False).relative_to(base.resolve())
        if source.is_symlink():
            raise ValueError("Static input is unexpectedly linked: " + name)
        actual = hashlib.sha256(source.read_bytes()).hexdigest() if source.is_file() else None
        if actual != expected[name]:
            raise RuntimeError("Static input changed since explicit preparation: " + name)


def release_metadata(base, patch_source_git_sha, tag, original_release, script_sha, deployed_at):
    result = dict(base)
    result.update(release=tag, gitSha=base.get("gitSha"), patch_source_git_sha=patch_source_git_sha,
                  base_release=str(original_release), tree_state="base-plus-uncommitted-geo-events-patch", deployed_at=deployed_at,
                  patches={**base.get("patches", {}), "geo-events.js": script_sha})
    return result

p = json.load(sys.stdin)
profile = p["profile"]
root = Path(profile["root"])
current = root / "current"
nginx = profile["nginx"]
with open(profile["lock"], "a") as lease:
    fcntl.flock(lease, fcntl.LOCK_EX | fcntl.LOCK_NB)
    original_release = current.resolve()
    if str(original_release) != p["expected_release"]:
        raise RuntimeError("Active release changed; refusing to deploy over another owner")
    validate_static_base(original_release, p.get("static_files", {}), p.get("static_base_sha256", {}))
    site = Path(profile["site"])
    text = site.read_text()
    if "root " + str(current) + ";" not in text:
        raise RuntimeError("Unexpected website root")
    if shutil.disk_usage(str(root)).free < 100 * 1024 * 1024:
        raise RuntimeError("Insufficient deployment storage")
    tag = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-geo-events-" + p["script_sha256"][:12]
    backup = Path(profile["backup"]) / tag
    backup.mkdir(parents=True, exist_ok=False)
    release = root / "releases" / tag
    snippet = Path(profile["snippet"])
    http = Path(profile["http"])
    Path("/var/log/nginx").mkdir(parents=True, exist_ok=True)
    logical_files = (site, snippet, http)
    bindings = {str(file): str(file.resolve(strict=False)) for file in logical_files}
    old = {str(file): config_bytes(file) for file in logical_files}
    for file, content in old.items():
        if content is not None:
            (backup / Path(file).name).write_bytes(content)
    (backup / "original-release.txt").write_text(str(original_release))
    new = {}
    try:
        shutil.copytree(original_release, release)
        (release / "assets").mkdir(exist_ok=True)
        (release / "assets/geo-events.js").write_text(p["script"])
        allowed_static = {"learn/index.html", "learn/实践.css", "learn/实践.js", "sitemap.xml", "llms.txt", "assets/weitian/wecom-contact-764be1abb583.jpg"}
        for name, entry in p.get("static_files", {}).items():
            if p["site"] != "personal" or name not in allowed_static:
                raise ValueError("Unexpected original-learning asset: " + name)
            content = base64.b64decode(entry["base64"], validate=True)
            if hashlib.sha256(content).hexdigest() != entry["sha256"]:
                raise ValueError("Original-learning asset hash mismatch")
            destination = release / name
            if destination.is_symlink():
                raise ValueError("Unsafe original-learning destination")
            try:
                destination.resolve().relative_to(release.resolve())
            except ValueError:
                raise ValueError("Original-learning destination escapes release")
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(content)
        original_metadata = original_release / "release.json"
        base = json.loads(original_metadata.read_text()) if original_metadata.is_file() else {}
        metadata = release_metadata(base, p["patch_source_git_sha"], tag, original_release, p["script_sha256"],
                                    datetime.datetime.now(datetime.timezone.utc).isoformat())
        metadata["source_dirty"] = True
        metadata["original_static_files"] = {name: entry["sha256"] for name, entry in p.get("static_files", {}).items()}
        (release / "release.json").write_text(json.dumps(metadata, indent=2))
        (release / "healthz.txt").write_text(tag + "\n")
        for directory, _, files in os.walk(release):
            os.chmod(directory, 0o755)
            for name in files: os.chmod(Path(directory) / name, 0o644)
        include = "    include " + str(snippet) + ";\n"
        if include not in text:
            if text.count("    index index.html;\n") != 1: raise RuntimeError("Ambiguous Nginx include point")
            text = text.replace("    index index.html;\n", "    index index.html;\n" + include)
        server = p["server"].replace('/assets/geo-events.js"', '/assets/geo-events.js?v=' + p["script_sha256"][:12] + '"')
        new = {str(site): text.encode(), str(snippet): server.encode(), str(http): p["http"].encode()}
        for file, content in new.items():
            destination = Path(file)
            if str(destination.resolve(strict=False)) != bindings[file]:
                raise RuntimeError("Nginx configuration link changed: " + file)
            atomic_config(destination, content, old[file])
        subprocess.run(nginx + ["-t"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if current.resolve() != original_release: raise RuntimeError("Another deployment changed current during preparation")
        pending = current.with_name(".current-" + tag)
        pending.symlink_to(release)
        pending.replace(current)
        subprocess.run(nginx + ["-s", "reload"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(json.dumps({"status": "DEPLOYED", "site": p["site"], "release": str(release), "previous": str(original_release), "backup": str(backup), "script_sha256": p["script_sha256"]}))
    except Exception:
        if current.resolve() == release:
            pending = current.with_name(".rollback-" + tag)
            pending.symlink_to(original_release)
            pending.replace(current)
        conflicts = []
        if current.resolve() != original_release:
            conflicts.append(str(current))
        for file, content in old.items():
            destination = Path(file)
            if (conflicts and str(current) in conflicts) or str(destination.resolve(strict=False)) != bindings[file]:
                conflicts.append(file)
                continue
            if not restore_config(destination, content, new.get(file)):
                conflicts.append(file)
        if not conflicts:
            subprocess.run(nginx + ["-t"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(nginx + ["-s", "reload"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        raise
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected-release", required=True)
    parser.add_argument("--site", choices=sorted(PROFILES), default="personal")
    parser.add_argument("--include-learning", action="store_true")
    parser.add_argument("--expected-static-manifest", type=Path)
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
    payload = {"site": args.site, "profile": PROFILES[args.site], "expected_release": args.expected_release, "patch_source_git_sha": git, "script": script,
               "script_sha256": hashlib.sha256(script.encode()).hexdigest(),
               "http": (root / "deploy/geo-events-http.conf").read_text(), "server": (root / "deploy/geo-events-server.conf").read_text()}
    if args.include_learning:
        if args.site != "personal":
            raise ValueError("Original learning pages belong to the personal site")
        if not args.expected_static_manifest or not args.expected_static_manifest.resolve().is_relative_to(Path("/Volumes/1TB-SSD/WilleSpace-Work").resolve()):
            raise ValueError("Original learning patch requires an explicit SSD baseline manifest")
        payload["static_base_sha256"] = json.loads(args.expected_static_manifest.read_text())
        names = ("learn/index.html", "learn/实践.css", "learn/实践.js", "sitemap.xml", "llms.txt", "assets/weitian/wecom-contact-764be1abb583.jpg")
        payload["static_files"] = {name: {"base64": base64.b64encode((root / name).read_bytes()).decode("ascii"),
                                                "sha256": hashlib.sha256((root / name).read_bytes()).hexdigest()} for name in names}
    result = subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=12", PROFILES[args.site]["host"], "python3", "-c", shlex.quote(REMOTE)],
                            input=json.dumps(payload), capture_output=True, text=True, timeout=120)
    receipt = {"returncode": result.returncode, "stdout": result.stdout, "stderr": result.stderr,
               "script_sha256": payload["script_sha256"], "expected_release": args.expected_release}
    path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8")
    print(result.stdout or result.stderr)
    raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()
