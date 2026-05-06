#!/usr/bin/env python3
import argparse
import json
from pathlib import Path


def load_text(path):
    return Path(path).read_text(encoding='utf-8').strip()


def load_json(path):
    source = Path(path)
    if not source.exists():
        return {}
    content = load_text(source)
    if not content:
        return {}
    return json.loads(content)


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


def render_tech_stack(tech_stack):
    if isinstance(tech_stack, list) and tech_stack:
        return ' · '.join(item.strip() for item in tech_stack if item and item.strip())
    if isinstance(tech_stack, str) and tech_stack.strip():
        return tech_stack.strip()
    return 'TBD'


def render_stats_cards(username):
    username = (username or '').strip()
    if not username:
        return ''

    stats = (
        f"![GitHub stats](https://github-readme-stats.vercel.app/api"
        f"?username={username}&show_icons=true&hide_border=true&rank_icon=github)"
    )
    langs = (
        f"![Top languages](https://github-readme-stats.vercel.app/api/top-langs/"
        f"?username={username}&layout=compact&hide_border=true)"
    )
    return f'{stats}\n\n{langs}'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--profile', required=True)
    parser.add_argument('--template', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()

    profile = load_yaml_like(args.profile)
    template = load_text(args.template)

    summary_zh = profile.get('summary_zh', '').strip()
    replacements = {
        'name': profile.get('name', 'Your Name'),
        'role': profile.get('role', '').strip(),
        'summary': profile.get('summary', 'Add a short summary.'),
        'summary_zh_section': f'## 中文简介\n\n{summary_zh}' if summary_zh else '',
        'tech_stack': render_tech_stack(profile.get('tech_stack', [])),
        'stats_cards': render_stats_cards(profile.get('username', '')),
    }

    content = template
    for key, value in replacements.items():
        content = content.replace('{{' + key + '}}', value)

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(content.strip() + '\n', encoding='utf-8')
    print(f'Wrote {output}')


if __name__ == '__main__':
    main()
