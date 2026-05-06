#!/usr/bin/env python3
import argparse
import json
from pathlib import Path


def load_text(path):
    return Path(path).read_text(encoding='utf-8').strip()


def load_json(path):
    return json.loads(load_text(path))


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


def render_list(items, key_title='name', key_desc='description'):
    featured = [x for x in items if x.get('featured', False)]
    rows = featured if featured else items
    if not rows:
        return '- None yet'
    rendered = []
    for item in rows:
        title = item.get(key_title) or item.get('title') or 'Untitled'
        desc = item.get(key_desc) or item.get('summary') or ''
        url = item.get('url', '').strip()
        line = f"- **{title}**"
        if desc:
            line += f": {desc}"
        if url:
            line += f" ([link]({url}))"
        rendered.append(line)
    return '\n'.join(rendered)


def render_links(links):
    if not isinstance(links, dict) or not links:
        return '- Add your public links here'
    return '\n'.join([f"- **{k}**: {v}" for k, v in links.items() if v])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--profile', required=True)
    parser.add_argument('--projects', required=True)
    parser.add_argument('--skills', required=True)
    parser.add_argument('--writing', required=True)
    parser.add_argument('--now', required=True)
    parser.add_argument('--template', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()

    profile = load_yaml_like(args.profile)
    projects = load_json(args.projects)
    skills = load_json(args.skills)
    writing = load_json(args.writing)
    now = load_text(args.now)
    template = load_text(args.template)

    replacements = {
        'name': profile.get('name', 'Your Name'),
        'headline': profile.get('headline', 'Add a clear headline'),
        'summary': profile.get('summary', 'Add a short summary.'),
        'summary_zh_section': '',
        'now': now,
        'projects': render_list(projects, 'name', 'description'),
        'skills': render_list(skills, 'name', 'description'),
        'writing': render_list(writing, 'title', 'summary'),
        'links': render_links(profile.get('links', {})),
        'contact_note': profile.get('contact_note', ''),
    }

    summary_zh = profile.get('summary_zh', '').strip()
    if summary_zh:
        replacements['summary_zh_section'] = f'## 中文简介\n\n{summary_zh}'

    content = template
    for key, value in replacements.items():
        content = content.replace('{{' + key + '}}', value)

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(content + '\n', encoding='utf-8')
    print(f'Wrote {output}')


if __name__ == '__main__':
    main()
