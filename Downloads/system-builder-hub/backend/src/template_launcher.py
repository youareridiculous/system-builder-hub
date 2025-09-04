import os
import re
from flask import Blueprint, render_template, request, send_from_directory, jsonify
import json
from pathlib import Path

template_launcher = Blueprint('template_launcher', __name__)

# Get the correct path to the templates directory (project root)
TEMPLATE_DIR = Path(__file__).resolve().parent.parent.parent / "templates"
FAVORITES_FILE = TEMPLATE_DIR / 'favorites.json'

# Predefined tags with their detection patterns
PREDEFINED_TAGS = {
    "frontend": ["frontend", "react", "vue", "angular", "javascript", "jsx", "css", "html"],
    "backend": ["backend", "api", "flask", "django", "express", "server", "database"],
    "AI": ["ai", "machine learning", "ml", "neural", "prompt", "gpt", "openai"],
    "utils": ["utils", "utility", "helper", "common", "shared"],
    "infra": ["infra", "docker", "kubernetes", "deploy", "ci/cd", "aws", "cloud"]
}

def load_favorites():
    """Load favorites from JSON file"""
    if FAVORITES_FILE.exists():
        try:
            with open(FAVORITES_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    return {}

def save_favorites(favorites):
    """Save favorites to JSON file"""
    try:
        with open(FAVORITES_FILE, 'w', encoding='utf-8') as f:
            json.dump(favorites, f, indent=2, ensure_ascii=False)
    except IOError as e:
        print(f"Error saving favorites: {e}")

def detect_tags(filename, content):
    """Detect tags based on filename and content"""
    detected_tags = []
    filename_lower = filename.lower()
    content_lower = content.lower()
    
    for tag, patterns in PREDEFINED_TAGS.items():
        for pattern in patterns:
            if pattern in filename_lower or pattern in content_lower:
                detected_tags.append(tag)
                break
    
    # Remove duplicates while preserving order
    return list(dict.fromkeys(detected_tags))

def get_file_preview(content, max_lines=20):
    """Get a preview of the file content"""
    lines = content.splitlines()
    preview_lines = lines[:max_lines]
    
    if len(lines) > max_lines:
        preview_lines.append(f"\n... ({len(lines) - max_lines} more lines)")
    
    return '\n'.join(preview_lines)

@template_launcher.route("/template-launcher")
def template_launcher_view():
    favorites = load_favorites()
    selected_tag = request.args.get("tag")
    show_favorites_only = request.args.get("favorites") == "true"

    templates = []
    
    if not TEMPLATE_DIR.exists():
        return render_template("template_launcher.html", 
                             templates=[], 
                             tags=list(PREDEFINED_TAGS.keys()), 
                             selected_tag=selected_tag)

    for filename in os.listdir(TEMPLATE_DIR):
        if not filename.endswith(('.md', '.txt', '.py', '.js', '.jsx', '.ts', '.tsx', '.yml', '.yaml')):
            continue
            
        path = TEMPLATE_DIR / filename
        
        if not path.is_file():
            continue
            
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            preview = get_file_preview(content)
            tags = detect_tags(filename, content)
            is_favorite = favorites.get(filename, False)
            
            # Skip if showing favorites only and this template is not favorited
            if show_favorites_only and not is_favorite:
                continue
                
            # Skip if tag filter is applied and template doesn't have that tag
            if selected_tag and selected_tag not in tags:
                continue
                
            template_info = {
                "filename": filename,
                "preview": preview,
                "tags": tags,
                "favorite": is_favorite,
                "size": len(content),
                "lines": len(content.splitlines())
            }
            
            templates.append(template_info)
            
        except Exception as e:
            print(f"Error reading {filename}: {e}")
            continue

    # Sort templates: favorites first, then alphabetically
    templates.sort(key=lambda x: (not x['favorite'], x['filename'].lower()))
    
    return render_template("template_launcher.html", 
                         templates=templates, 
                         tags=list(PREDEFINED_TAGS.keys()), 
                         selected_tag=selected_tag,
                         show_favorites_only=show_favorites_only)

@template_launcher.route("/toggle-favorite/<filename>", methods=["POST"])
def toggle_favorite(filename):
    favorites = load_favorites()
    favorites[filename] = not favorites.get(filename, False)
    save_favorites(favorites)
    return '', 204

@template_launcher.route('/download-template/<filename>')
def download_template(filename):
    return send_from_directory(TEMPLATE_DIR, filename, as_attachment=True)
