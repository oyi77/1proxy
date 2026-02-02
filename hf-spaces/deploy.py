#!/usr/bin/env python3
"""
Deploy 1proxy to HuggingFace Spaces using the Hub API.

Usage:
    python deploy.py [--token HF_TOKEN] [--name SPACE_NAME]

Requirements:
    pip install huggingface_hub
"""

import os
import sys
import argparse
from pathlib import Path
from huggingface_hub import HfApi


def deploy_to_hf_spaces(token: str, space_name: str):
    """
    Deploy 1proxy to HuggingFace Spaces.

    Args:
        token: HuggingFace access token
        space_name: Name for the Space
    """
    api = HfApi(token=token)

    # Get user info to construct full repo path
    me = api.whoami()

    # Get the directory containing this script
    script_dir = Path(__file__).parent.absolute()
    repo_root = script_dir.parent

    print(f"🚀 Deploying 1proxy to HuggingFace Spaces...")
    print(f"   Space name: {space_name}")
    print(f"   Repository root: {repo_root}")
    print(f"   User: {me['name']}")

    # Space will be created in user's namespace
    space_id = f"{me['name']}/{space_name}"

    try:
        # Try to get space info
        api.space_info(space_id)
        space_exists = True
        print(f"   📦 Space '{space_id}' already exists, will update...")
    except Exception:
        space_exists = False
        print(f"   📦 Creating new Space '{space_id}'...")

    # Upload files to the Space
    print(f"\n📤 Uploading files to HuggingFace...")

    # Upload hf-spaces directory
    api.upload_folder(
        repo_id=space_id,
        folder_path=str(script_dir),
        repo_type="space",
        commit_message="Deploy 1proxy to HF Spaces",
    )

    print(f"\n✅ Deployment initiated!")
    print(f"\n📋 Next steps:")
    print(f"   1. Go to: https://huggingface.co/spaces/{space_id}")
    print(f"   2. Add secrets in Space settings:")
    print(f"      - SECRET_KEY (min 32 chars)")
    print(f"      - GITHUB_CLIENT_ID")
    print(f"      - GITHUB_CLIENT_SECRET")
    print(f"   3. Configure admin repo (optional):")
    print(f"      - GITHUB_REPO_OWNER")
    print(f"      - GITHUB_REPO_NAME")
    print(f"   4. The Space will build automatically")
    print(f"\n🔗 Your 1proxy instance will be available at:")
    print(f"   https://{me['name']}-{space_name}.hf.space")

    return space_id


def main():
    parser = argparse.ArgumentParser(description="Deploy 1proxy to HuggingFace Spaces")
    parser.add_argument(
        "--token",
        type=str,
        default=None,
        help="HuggingFace access token (or set HF_TOKEN env var)",
    )
    parser.add_argument(
        "--name",
        type=str,
        default="1proxy",
        help="Name for the Space (default: 1proxy)",
    )

    args = parser.parse_args()

    # Get token from args or environment
    token = args.token or os.environ.get("HF_TOKEN")

    if not token:
        print("❌ Error: HuggingFace token required!")
        print("   Set --token argument or HF_TOKEN environment variable")
        print("   Get your token from: https://huggingface.co/settings/tokens")
        sys.exit(1)

    space_name = deploy_to_hf_spaces(token=token, space_name=args.name)


if __name__ == "__main__":
    main()
