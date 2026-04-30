#!/usr/bin/env python3
import argparse
import json
from pathlib import Path


def load_text(path):
    return Path(path).read_text(encoding='utf-8').strip()


def load_json(path):
    return json.loads(load_text(path))


def load_yaml_like(path):
    data = {}
    current_key = None
    block_mode = False
    block_lines = []
    for raw in Path(path).read_text(encoding='utf-8').splitlines():
        line = raw.rstrip('\n')
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        if block_mode:
            if line.startswith('  ') or line == '':
                block_lines.append(line[2:] if line.startswith('  ') else '')
                continue
            data[current_key] = '\n'.join(block_lines).strip()
            block_mode = False
            block_lines = []
            current_key = None
        if line.endswith(': |-') or line.endswith(': >-') or line.endswith(': |') or line.endswith(': >'):
            current_key = line.split(':', 1)[0]
            block_mode = True
        elif ': ' in line:
            key, value = line.split(': ', 1)
            if value.startswith('[') and value.endswith(']'):
                try:
                    data[key] = json.loads(value.replace("'", '"'))
                except Exception:
                    data[key] = value
            else:
                data[key] = value
        elif line.endswith(':'):
            current_key = line[:-1]
            data[current_key] = []
        elif line.lstrip().startswith('- ') and isinstance(data.get(current_key), list):
            data[current_key].append(line.lstrip()[2:])
    if block_mode and current_key is not None:
        data[current_key] = '\n'.join(block_lines).strip()
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
        'now': now,
        'projects': render_list(projects, 'name', 'description'),
        'skills': render_list(skills, 'name', 'description'),
        'writing': render_list(writing, 'title', 'summary'),
        'links': render_links(profile.get('links', {})),
        'contact_note': profile.get('contact_note', ''),
    }

    content = template
    for key, value in replacements.items():
        content = content.replace('{{' + key + '}}', value)

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(content + '\n', encoding='utf-8')
    print(f'Wrote {output}')


if __name__ == '__main__':
    main()
