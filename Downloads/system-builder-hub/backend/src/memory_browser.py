from flask import Blueprint, render_template, request, redirect, url_for
from pathlib import Path
import re

memory_browser = Blueprint('memory_browser', __name__, template_folder='templates')

MEMORY_SESSIONS_DIR = Path(__file__).resolve().parent.parent.parent / 'memory/SESSIONS'

def parse_memory_file(memory_path):
    sections = {
        "Reusable Logic": [],
        "Bugs": [],
        "Prompts": [],
        "Guidelines": [],
        "Wins": []
    }

    if not memory_path.exists():
        return sections

    content = memory_path.read_text(encoding='utf-8')

    patterns = {
        "Reusable Logic": r"## 🔁 Reusable Logic\n(.+?)(?=\n##|$)",
        "Bugs": r"## 🐛 Bugs & Pitfalls\n(.+?)(?=\n##|$)",
        "Prompts": r"## 💡 Prompts & Ideas\n(.+?)(?=\n##|$)",
        "Guidelines": r"## 📚 Guidelines & Lessons\n(.+?)(?=\n##|$)",
        "Wins": r"## 🔥 Wins & Breakthroughs\n(.+?)(?=\n##|$)"
    }

    for key, pattern in patterns.items():
        match = re.search(pattern, content, re.DOTALL)
        if match:
            lines = [line.strip('- ').strip() for line in match.group(1).strip().splitlines() if line.strip()]
            sections[key] = lines

    return sections

@memory_browser.route('/test')
def test_route():
    return "Memory browser blueprint is working!"

@memory_browser.route('/memory-browser')
def memory_browser_view():
    sessions = []

    for session_dir in sorted(MEMORY_SESSIONS_DIR.glob('*'), reverse=True):
        memory_file = session_dir / 'memory.md'
        if memory_file.exists():
            sections = parse_memory_file(memory_file)
            sessions.append({
                'name': session_dir.name,
                'sections': sections
            })

    return render_template('memory_browser.html', sessions=sessions)