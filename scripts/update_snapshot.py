#!/usr/bin/env python3
import argparse
import json
import os
import subprocess
import urllib.request
from pathlib import Path


def normalize_text(text):
    if not text:
        return ''
    return (
        text.replace('\u2013', '-')
        .replace('\u2014', '-')
        .replace('\u2018', "'")
        .replace('\u2019', "'")
        .replace('\u201c', '"')
        .replace('\u201d', '"')
    )


def fetch_repos(username):
    try:
        result = subprocess.run(
            ['gh', 'api', f'users/{username}/repos', '--paginate', '--slurp'],
            check=True,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
        )
        payload = json.loads(result.stdout)
        if isinstance(payload, list):
            flattened = []
            for item in payload:
                if isinstance(item, list):
                    flattened.extend(item)
                else:
                    flattened.append(item)
            return flattened
    except Exception:
        pass

    headers = {
        'Accept': 'application/vnd.github+json',
        'User-Agent': f'{username}-profile-snapshot',
    }
    token = os.environ.get('GITHUB_TOKEN') or os.environ.get('GH_TOKEN')
    if token:
        headers['Authorization'] = f'Bearer {token}'

    repos = []
    page = 1
    while True:
        url = (
            f'https://api.github.com/users/{username}/repos'
            f'?per_page=100&page={page}&type=owner&sort=updated'
        )
        request = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(request) as response:
            payload = json.loads(response.read().decode('utf-8'))
        if not payload:
            break
        repos.extend(payload)
        page += 1
    return repos


def pick_top_repo(repos, username):
    candidates = [repo for repo in repos if repo.get('name') != username]
    pool = candidates if candidates else repos
    if not pool:
        return {}

    def rank(repo):
        return (
            repo.get('stargazers_count', 0),
            repo.get('updated_at', ''),
            repo.get('created_at', ''),
        )

    repo = sorted(pool, key=rank, reverse=True)[0]
    return {
        'name': repo.get('name', ''),
        'description': normalize_text(repo.get('description') or ''),
        'html_url': repo.get('html_url', ''),
        'stargazers_count': repo.get('stargazers_count', 0),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--username', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()

    repos = fetch_repos(args.username)
    owned_public = [repo for repo in repos if not repo.get('fork') and not repo.get('private')]
    snapshot = {
        'username': args.username,
        'owned_repo_count': len(owned_public),
        'total_stars': sum(repo.get('stargazers_count', 0) for repo in owned_public),
        'top_repo': pick_top_repo(owned_public, args.username),
    }

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(f'Wrote {output}')


if __name__ == '__main__':
    main()
