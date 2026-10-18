#!/usr/bin/env python3
import hashlib
import json
import os
import sys
import time
import urllib.request
import urllib.error

def get_token() -> str:
    path = os.path.expanduser("~/.gemini/mcp-oauth-tokens.json")
    if not os.path.exists(path):
        raise RuntimeError(f"Missing {path}")
    with open(path) as f:
        data = json.load(f)
    for item in data:
        if item.get("serverName") == "vercel":
            # Check if token needs refresh
            expires_at = item["token"].get("expiresAt", 0)
            now_ms = int(time.time() * 1000)
            if now_ms >= expires_at - 60000 and "refreshToken" in item["token"]:
                import urllib.parse
                post_data = urllib.parse.urlencode({
                    "grant_type": "refresh_token",
                    "client_id": item["clientId"],
                    "refresh_token": item["token"]["refreshToken"],
                }).encode()
                req = urllib.request.Request(
                    item["tokenUrl"],
                    data=post_data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    method="POST",
                )
                with urllib.request.urlopen(req) as resp:
                    refreshed = json.loads(resp.read().decode())
                    item["token"]["accessToken"] = refreshed["access_token"]
                    if "refresh_token" in refreshed:
                        item["token"]["refreshToken"] = refreshed["refresh_token"]
                    item["token"]["expiresAt"] = now_ms + int(refreshed.get("expires_in", 3600)) * 1000
                with open(path, "w") as fp:
                    json.dump(data, fp, indent=2)
            return item["token"]["accessToken"]
    raise RuntimeError("No Vercel token found in mcp-oauth-tokens.json")

def upload_file(token: str, file_path: str, data: bytes, digest: str) -> None:
    req = urllib.request.Request(
        "https://api.vercel.com/v2/files",
        data=data,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/octet-stream",
            "Content-Length": str(len(data)),
            "x-vercel-digest": digest,
        },
        method="POST"
    )
    try:
        with urllib.request.urlopen(req) as resp:
            pass
    except urllib.error.HTTPError as e:
        err_body = e.read().decode(errors="replace")
        raise RuntimeError(f"Failed to upload {file_path}: {e.code} {e.reason}: {err_body}")

def deploy():
    token = get_token()
    dist_dir = os.path.abspath("frontend/dist")
    if not os.path.isdir(dist_dir):
        raise RuntimeError(f"{dist_dir} does not exist. Run npm run build first.")

    deployment_files = []
    print(f"Scanning {dist_dir}...")
    for root, _, files in os.walk(dist_dir):
        for f in files:
            full_path = os.path.join(root, f)
            rel_path = os.path.relpath(full_path, dist_dir)
            with open(full_path, "rb") as fp:
                content = fp.read()
            size = len(content)
            digest = hashlib.sha1(content).hexdigest()
            print(f"Uploading {rel_path} ({size} bytes, sha1: {digest[:8]}...)...")
            upload_file(token, rel_path, content, digest)
            deployment_files.append({
                "file": rel_path,
                "sha": digest,
                "size": size
            })

    # Include vercel.json for rewrites and clean routing
    vercel_json_path = os.path.abspath("frontend/vercel.json")
    if os.path.exists(vercel_json_path):
        with open(vercel_json_path, "rb") as fp:
            v_content = fp.read()
        v_size = len(v_content)
        v_digest = hashlib.sha1(v_content).hexdigest()
        print(f"Uploading vercel.json ({v_size} bytes, sha1: {v_digest[:8]}...)...")
        upload_file(token, "vercel.json", v_content, v_digest)
        deployment_files.append({
            "file": "vercel.json",
            "sha": v_digest,
            "size": v_size
        })

    print(f"Uploaded {len(deployment_files)} files. Creating deployment...")
    payload = {
        "name": "enterprise-knowledge-ai",
        "project": "enterprise-knowledge-ai",
        "target": "production",
        "projectSettings": {
            "framework": None
        },
        "files": deployment_files
    }

    req = urllib.request.Request(
        "https://api.vercel.com/v13/deployments",
        data=json.dumps(payload).encode(),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(req) as resp:
            deployment = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        err_body = e.read().decode(errors="replace")
        raise RuntimeError(f"Failed to create deployment: {e.code} {e.reason}: {err_body}")

    deploy_id = deployment.get("id")
    url = deployment.get("url")
    print(f"Deployment created: id={deploy_id}, url=https://{url}")

    # Poll status
    for _ in range(60):
        req_status = urllib.request.Request(
            f"https://api.vercel.com/v13/deployments/{deploy_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        with urllib.request.urlopen(req_status) as resp:
            data = json.loads(resp.read().decode())
        state = data.get("readyState")
        print(f"Deployment state: {state}")
        if state == "READY":
            aliases = data.get("alias", [])
            print("Deployment is READY!")
            print(f"Production URL: https://{url}")
            for a in aliases:
                print(f"Alias URL: https://{a}")
            return data
        elif state in ("ERROR", "CANCELED"):
            raise RuntimeError(f"Deployment failed with state: {state}: {data.get('errorMessage')}")
        time.sleep(2)

    raise TimeoutError("Deployment polling timed out")

if __name__ == "__main__":
    deploy()
