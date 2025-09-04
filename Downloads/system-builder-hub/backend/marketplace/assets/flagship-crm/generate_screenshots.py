"""
Generate placeholder screenshots for Flagship CRM
"""
import os
from PIL import Image, ImageDraw, ImageFont
import textwrap

def create_placeholder_screenshot(title, description, filename, width=1200, height=800):
    """Create a placeholder screenshot"""
    # Create image
    img = Image.new('RGB', (width, height), color='#f8fafc')
    draw = ImageDraw.Draw(img)
    
    # Add border
    draw.rectangle([0, 0, width-1, height-1], outline='#e2e8f0', width=2)
    
    # Add title
    try:
        font = ImageFont.truetype("Arial", 36)
    except:
        font = ImageFont.load_default()
    
    # Wrap title text
    title_lines = textwrap.wrap(title, width=30)
    y_position = 50
    
    for line in title_lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        text_width = bbox[2] - bbox[0]
        x_position = (width - text_width) // 2
        draw.text((x_position, y_position), line, fill='#1e293b', font=font)
        y_position += 50
    
    # Add description
    try:
        desc_font = ImageFont.truetype("Arial", 18)
    except:
        desc_font = ImageFont.load_default()
    
    desc_lines = textwrap.wrap(description, width=50)
    y_position += 30
    
    for line in desc_lines:
        bbox = draw.textbbox((0, 0), line, font=desc_font)
        text_width = bbox[2] - bbox[0]
        x_position = (width - text_width) // 2
        draw.text((x_position, y_position), line, fill='#64748b', font=desc_font)
        y_position += 30
    
    # Add placeholder content
    y_position += 50
    
    # Simulate UI elements
    # Header
    draw.rectangle([50, y_position, width-50, y_position+60], fill='#3b82f6', outline='#2563eb')
    draw.text((70, y_position+20), "SBH CRM Dashboard", fill='white', font=desc_font)
    
    y_position += 80
    
    # Content area
    draw.rectangle([50, y_position, width-50, height-100], fill='white', outline='#e2e8f0')
    
    # Add some mock content
    content_y = y_position + 30
    
    # Metrics cards
    metrics = [
        ("Total Contacts", "1,234"),
        ("Active Deals", "56"),
        ("Tasks Due", "23"),
        ("Revenue", "$45,678")
    ]
    
    card_width = (width - 150) // 4
    for i, (label, value) in enumerate(metrics):
        x = 70 + i * (card_width + 10)
        draw.rectangle([x, content_y, x+card_width, content_y+80], fill='#f1f5f9', outline='#e2e8f0')
        draw.text((x+10, content_y+10), label, fill='#64748b', font=desc_font)
        draw.text((x+10, content_y+35), value, fill='#1e293b', font=font)
    
    content_y += 120
    
    # Chart placeholder
    draw.rectangle([70, content_y, width-70, content_y+200], fill='#f8fafc', outline='#e2e8f0')
    draw.text((90, content_y+20), "📊 Analytics Chart", fill='#64748b', font=desc_font)
    
    # Save image
    img.save(filename)
    print(f"Generated {filename}")

def main():
    """Generate all placeholder screenshots"""
    screenshots = [
        {
            "title": "CRM Dashboard",
            "description": "Main dashboard with key metrics, charts, and insights",
            "filename": "dashboard.png"
        },
        {
            "title": "Contacts Manager",
            "description": "Comprehensive contact management with search, filtering, and bulk actions",
            "filename": "contacts.png"
        },
        {
            "title": "Deal Pipeline",
            "description": "Kanban-style deal pipeline with drag-and-drop functionality",
            "filename": "pipeline.png"
        },
        {
            "title": "AI Copilot Hub",
            "description": "AI-powered assistant for sales, operations, and customer success",
            "filename": "copilot.png"
        },
        {
            "title": "Analytics Dashboard",
            "description": "Conversational analytics with natural language queries and insights",
            "filename": "analytics.png"
        },
        {
            "title": "Automations Builder",
            "description": "No-code automation builder for workflows and triggers",
            "filename": "automations.png"
        },
        {
            "title": "Projects Kanban",
            "description": "Project management with task tracking and team collaboration",
            "filename": "projects.png"
        },
        {
            "title": "Admin Panel",
            "description": "System administration, user management, and settings",
            "filename": "admin.png"
        }
    ]
    
    # Create directory if it doesn't exist
    os.makedirs("marketplace/assets/flagship-crm", exist_ok=True)
    
    # Generate screenshots
    for screenshot in screenshots:
        create_placeholder_screenshot(
            screenshot["title"],
            screenshot["description"],
            f"marketplace/assets/flagship-crm/{screenshot['filename']}"
        )

if __name__ == "__main__":
    main()
