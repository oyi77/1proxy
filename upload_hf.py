#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Upload 1proxy-backend to HF Space"""

import os
import sys
import time
from huggingface_hub import HfApi

# Fix Windows encoding issue
if sys.platform == "win32":
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# USE THE TOKEN FROM ENVIRONMENT
TOKEN = os.getenv("HF_TOKEN")
REPO = "paijo77/1proxy"

if not TOKEN:
    print("❌ ERROR: HF_TOKEN environment variable not set!")
    sys.exit(1)

api = HfApi(token=TOKEN)

print("🚀 Starting HF Space deployment...\n")

# Wait a moment for the new repo to propagate in HF's system
print("⏳ Waiting for repository propagation (15s)...")
time.sleep(15)

# Upload HF Space configuration files FIRST
print("📋 Uploading HF Space configuration...")
for f in ["README.md", "Dockerfile"]:
    local_path = os.path.join("hf-spaces", f)
    if os.path.exists(local_path):
        try:
            api.upload_file(
                path_or_fileobj=open(local_path, "rb"),
                path_in_repo=f,
                repo_id=REPO,
                repo_type="space",
                commit_message=f"update {f}",
            )
            print(f"✅ Uploaded: {f}")
        except Exception as e:
            print(f"❌ Failed to upload {f}: {e}")

# Upload requirements.txt to root
print("\n📦 Uploading dependencies...")
try:
    api.upload_file(
        path_or_fileobj=open("hf-spaces/requirements.txt", "rb"),
        path_in_repo="requirements.txt",
        repo_id=REPO,
        repo_type="space",
        commit_message="update requirements.txt",
    )
    print("✅ Uploaded: requirements.txt")
except Exception as e:
    print(f"❌ Failed to upload requirements.txt: {e}")

# Walk and upload all .py files
print("\n📁 Uploading application code...")
uploaded_count = 0
for root, dirs, files in os.walk("1proxy-backend"):
    # Skip __pycache__ and .git
    dirs[:] = [d for d in dirs if d not in ["__pycache__", ".git", ".venv", "venv"]]

    for f in files:
        if f.endswith(".py"):
            local = os.path.join(root, f)
            # Convert Windows path to forward slashes and adjust remote path
            remote = local.replace("\\", "/").replace("1proxy-backend/", "")

            try:
                api.upload_file(
                    path_or_fileobj=open(local, "rb"),
                    path_in_repo=remote,
                    repo_id=REPO,
                    repo_type="space",
                    commit_message=f"update {remote}",
                )
                uploaded_count += 1
                print(f"✅ Uploaded: {remote}")
            except Exception as e:
                print(f"❌ Failed to upload {remote}: {e}")

print(f"\n✨ Successfully uploaded {uploaded_count} Python files!")

# Upload BUILD_TRIGGER.txt last to trigger rebuild
print("\n🔨 Triggering rebuild...")
timestamp = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
trigger_content = f"Build triggered at {timestamp}\n"

try:
    api.upload_file(
        path_or_fileobj=trigger_content.encode(),
        path_in_repo="BUILD_TRIGGER.txt",
        repo_id=REPO,
        repo_type="space",
        commit_message=f"trigger rebuild - {timestamp}",
    )
    print("✅ Build triggered!")
except Exception as e:
    print(f"❌ Failed to trigger build: {e}")

print("\n" + "=" * 60)
print("✅ DEPLOYMENT COMPLETE!")
print("=" * 60)
print(f"\n🔗 Visit: https://huggingface.co/spaces/{REPO}")
print(f"🌐 App URL: https://paijo77-1proxy.hf.space")
print("\n⏳ Build will start shortly. Check the logs on HuggingFace.")
