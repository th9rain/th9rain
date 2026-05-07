#!/usr/bin/env python3
import argparse
import json
import os
import re
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def load_text(path):
    return Path(path).read_text(encoding='utf-8').strip()


def load_yaml_like(path):
    lines = Path(path).read_text(encoding='utf-8').splitlines()
    data = {}
    index = 0

    while index < len(lines):
        raw = lines[index]
        if not raw.strip() or raw.lstrip().startswith('#'):
            index += 1
            continue
        if raw.startswith(' '):
            index += 1
            continue
        if ':' not in raw:
            index += 1
            continue

        key, rest = raw.split(':', 1)
        key = key.strip()
        rest = rest.strip()

        if rest in {'|-', '>-', '|', '>'}:
            block_lines = []
            index += 1
            while index < len(lines):
                line = lines[index]
                if not line.strip():
                    block_lines.append('')
                    index += 1
                    continue
                if not line.startswith('  '):
                    break
                block_lines.append(line[2:])
                index += 1
            data[key] = '\n'.join(block_lines).strip()
            continue

        if rest == '':
            mapping = {}
            items = []
            index += 1
            while index < len(lines):
                line = lines[index]
                if not line.strip():
                    index += 1
                    continue
                if not line.startswith('  '):
                    break
                stripped = line[2:]
                if stripped.startswith('- '):
                    items.append(stripped[2:])
                elif ': ' in stripped:
                    subkey, subvalue = stripped.split(': ', 1)
                    mapping[subkey.strip()] = subvalue.strip()
                index += 1
            if mapping and not items:
                data[key] = mapping
            elif items and not mapping:
                data[key] = items
            elif mapping:
                data[key] = mapping
            else:
                data[key] = {}
            continue

        data[key] = rest
        index += 1

    return data


def unquote_scalar(value):
    if not isinstance(value, str):
        return value
    text = value.strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in {"'", '"'}:
        return text[1:-1]
    return text


def render_tech_stack(tech_stack):
    if isinstance(tech_stack, list) and tech_stack:
        return ' · '.join(
            unquote_scalar(item) for item in tech_stack if isinstance(item, str) and unquote_scalar(item)
        )
    if isinstance(tech_stack, str) and tech_stack.strip():
        return unquote_scalar(tech_stack)
    return 'TBD'


def render_bullet_list(items):
    if isinstance(items, list):
        lines = [unquote_scalar(item) for item in items if isinstance(item, str) and unquote_scalar(item)]
        return '\n'.join(f'- {line}' for line in lines)
    if isinstance(items, str) and items.strip():
        return f'- {unquote_scalar(items)}'
    return ''


def render_inline_links(links):
    if isinstance(links, list):
        items = [unquote_scalar(item) for item in links if isinstance(item, str) and unquote_scalar(item)]
        return ' · '.join(items)
    if isinstance(links, str) and links.strip():
        return unquote_scalar(links)
    return ''


def render_section(title, body):
    body = (body or '').strip()
    if not body:
        return ''
    return f'## {title}\n\n{body}'


def parse_int(value, default):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def parse_link_header(header):
    links = {}
    for part in header.split(','):
        match = re.match(r'\s*<([^>]+)>;\s*rel="([^"]+)"', part)
        if match:
            url, rel = match.groups()
            links[rel] = url
    return links


def github_api_get(url):
    token = os.environ.get('GITHUB_TOKEN', '').strip()
    headers = {
        'Accept': 'application/vnd.github+json',
        'User-Agent': 'th9rain-profile-generator',
        'X-GitHub-Api-Version': '2022-11-28',
    }
    if token:
        headers['Authorization'] = f'Bearer {token}'

    request = Request(url, headers=headers)
    with urlopen(request, timeout=20) as response:
        payload = response.read().decode('utf-8')
        return json.loads(payload), response.headers


def fetch_recent_repositories(username, excluded_names=None, limit=3):
    username = (username or '').strip()
    if not username or limit <= 0:
        return []

    excluded = {username.lower()}
    for name in excluded_names or []:
        if isinstance(name, str) and name.strip():
            excluded.add(name.strip().lower())

    url = (
        f'https://api.github.com/users/{username}/repos'
        f'?per_page=100&type=owner&sort=updated&page=1'
    )
    repositories = []

    while url and len(repositories) < limit:
        try:
            payload, headers = github_api_get(url)
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError):
            return repositories

        if not isinstance(payload, list):
            return repositories

        for repo in payload:
            name = (repo.get('name') or '').strip()
            if not name or name.lower() in excluded:
                continue
            if repo.get('private') or repo.get('fork') or repo.get('archived'):
                continue

            repositories.append(
                {
                    'name': name,
                    'url': (repo.get('html_url') or '').strip(),
                    'description': ' '.join((repo.get('description') or '').split()),
                }
            )
            if len(repositories) >= limit:
                break

        if len(repositories) >= limit:
            break

        url = parse_link_header(headers.get('Link', '')).get('next')

    return repositories


def render_repositories(repositories):
    if not repositories:
        return ''

    lines = []
    for repo in repositories:
        name = repo.get('name', '').strip()
        url = repo.get('url', '').strip()
        description = repo.get('description', '').strip()
        if not name or not url:
            continue
        line = f'- [{name}]({url})'
        if description:
            line += f' - {description}'
        lines.append(line)
    return '\n'.join(lines)


def collapse_blank_lines(text):
    return re.sub(r'\n{3,}', '\n\n', text.strip()) + '\n'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--profile', required=True)
    parser.add_argument('--template', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()

    profile = load_yaml_like(args.profile)
    template = load_text(args.template)

    summary_zh = profile.get('summary_zh', '').strip()
    links_line = render_inline_links(profile.get('links', []))
    featured_projects = render_bullet_list(profile.get('featured_projects', []))
    current_focus = render_bullet_list(profile.get('current_focus', []))
    repo_limit = max(parse_int(profile.get('repo_limit', 3), 3), 0)
    repo_title = (profile.get('repo_section_title') or 'Recent Public Repositories').strip()
    recent_repositories = fetch_recent_repositories(
        username=profile.get('username', ''),
        excluded_names=profile.get('repo_exclude', []),
        limit=repo_limit,
    )
    recent_repositories_body = render_repositories(recent_repositories)
    replacements = {
        'name': profile.get('name', 'Your Name'),
        'role': profile.get('role', '').strip(),
        'links_line': links_line,
        'summary': profile.get('summary', 'Add a short summary.'),
        'summary_zh_section': render_section('中文简介', summary_zh),
        'featured_projects_section': render_section('Selected Projects', featured_projects),
        'recent_repositories_section': render_section(repo_title, recent_repositories_body),
        'current_focus_section': render_section('Current Focus', current_focus),
        'tech_stack': render_tech_stack(profile.get('tech_stack', [])),
    }

    content = template
    for key, value in replacements.items():
        content = content.replace('{{' + key + '}}', value)

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(collapse_blank_lines(content), encoding='utf-8')
    print(f'Wrote {output}')


if __name__ == '__main__':
    main()
