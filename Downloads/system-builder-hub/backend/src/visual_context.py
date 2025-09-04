"""
🎨 System Build Hub OS - Visual Context Awareness

This module provides image and document-based context awareness for the system builder,
enabling visual inputs, design references, and document analysis in prompts.
"""

import os
import uuid
import base64
import json
import fitz  # PyMuPDF for PDF processing
from PIL import Image, ImageDraw, ImageFont
import cv2
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum
import io
import requests
from urllib.parse import urlparse

from agent_framework import AgentOrchestrator, MemorySystem
from system_lifecycle import SystemLifecycleManager

class VisualInputType(Enum):
    SCREENSHOT = "screenshot"
    UI_MOCKUP = "ui_mockup"
    DESIGN_REFERENCE = "design_reference"
    DOCUMENT = "document"
    FIGMA_FILE = "figma_file"
    SKETCH_FILE = "sketch_file"
    PDF_SPEC = "pdf_spec"

class AnalysisType(Enum):
    LAYOUT_ANALYSIS = "layout_analysis"
    COLOR_SCHEME = "color_scheme"
    TYPOGRAPHY = "typography"
    COMPONENT_DETECTION = "component_detection"
    ACCESSIBILITY = "accessibility"
    RESPONSIVE_DESIGN = "responsive_design"
    VISUAL_DIFF = "visual_diff"

@dataclass
class VisualContext:
    """Visual context information"""
    context_id: str
    input_type: VisualInputType
    file_path: str
    original_filename: str
    file_size: int
    mime_type: str
    dimensions: Optional[Tuple[int, int]] = None
    extracted_text: Optional[str] = None
    color_palette: Optional[List[str]] = None
    layout_analysis: Optional[Dict[str, Any]] = None
    component_detection: Optional[List[Dict[str, Any]]] = None
    accessibility_score: Optional[float] = None
    created_at: datetime = None

@dataclass
class VisualPrompt:
    """Visual prompt with context"""
    prompt_id: str
    user_prompt: str
    visual_contexts: List[VisualContext]
    analysis_results: Dict[str, Any]
    generated_instructions: List[str]
    created_at: datetime = None

@dataclass
class VisualDiff:
    """Visual difference analysis"""
    diff_id: str
    before_image: str
    after_image: str
    diff_areas: List[Dict[str, Any]]
    change_summary: str
    severity: str  # low, medium, high
    created_at: datetime = None


@dataclass
class ImageAnalysis:
    """Image analysis result"""
    analysis_id: str
    image_path: str
    analysis_type: AnalysisType
    results: Dict[str, Any]
    confidence: float
    processing_time: float
    created_at: datetime
    metadata: Dict[str, Any]


@dataclass
class VideoAnalysis:
    """Video analysis result"""
    analysis_id: str
    video_path: str
    analysis_type: AnalysisType
    results: Dict[str, Any]
    confidence: float
    processing_time: float
    frame_count: int
    duration: float
    created_at: datetime
    metadata: Dict[str, Any]

class VisualContextProcessor:
    """
    Processes visual inputs and provides context-aware analysis
    """
    
    def __init__(self, base_dir: Path, agent_orchestrator: AgentOrchestrator,
                 memory_system: MemorySystem, system_lifecycle: SystemLifecycleManager):
        self.base_dir = base_dir
        self.agent_orchestrator = agent_orchestrator
        self.memory_system = memory_system
        self.system_lifecycle = system_lifecycle
        
        # Visual processing directories
        self.visual_dir = base_dir / "visual_context"
        self.uploads_dir = self.visual_dir / "uploads"
        self.processed_dir = self.visual_dir / "processed"
        self.diffs_dir = self.visual_dir / "diffs"
        self.cache_dir = self.visual_dir / "cache"
        
        # Create directories
        for directory in [self.visual_dir, self.uploads_dir, self.processed_dir, 
                         self.diffs_dir, self.cache_dir]:
            directory.mkdir(parents=True, exist_ok=True)
        
        # Supported file types
        self.supported_image_types = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'}
        self.supported_document_types = {'.pdf', '.docx', '.txt', '.md'}
        self.supported_design_types = {'.fig', '.sketch', '.xd'}
        
        # Load models and configurations
        self.load_analysis_models()
        
        # Track processed contexts
        self.visual_contexts: Dict[str, VisualContext] = {}
        self.visual_prompts: Dict[str, VisualPrompt] = {}
        self.visual_diffs: Dict[str, VisualDiff] = {}
    
    def load_analysis_models(self):
        """Load analysis models and configurations"""
        # This would load actual ML models in production
        # For now, we'll use basic computer vision techniques
        self.layout_detector = None  # Would be a trained model
        self.component_detector = None  # Would be a trained model
        self.color_analyzer = None  # Would be a trained model
        
        # Basic analysis configurations
        self.analysis_config = {
            'min_confidence': 0.7,
            'max_colors': 10,
            'layout_grid_size': 12,
            'component_min_size': 50
        }
    
    def process_visual_input(self, file_data: bytes, filename: str, 
                           input_type: VisualInputType = None) -> str:
        """Process visual input and return context ID"""
        context_id = str(uuid.uuid4())
        
        # Determine input type if not provided
        if input_type is None:
            input_type = self._detect_input_type(filename)
        
        # Save file
        file_path = self._save_uploaded_file(file_data, filename, context_id)
        
        # Create visual context
        visual_context = VisualContext(
            context_id=context_id,
            input_type=input_type,
            file_path=str(file_path),
            original_filename=filename,
            file_size=len(file_data),
            mime_type=self._get_mime_type(filename),
            created_at=datetime.now()
        )
        
        # Process based on input type
        if input_type in [VisualInputType.SCREENSHOT, VisualInputType.UI_MOCKUP, 
                         VisualInputType.DESIGN_REFERENCE]:
            self._process_image_context(visual_context)
        elif input_type == VisualInputType.DOCUMENT:
            self._process_document_context(visual_context)
        elif input_type == VisualInputType.PDF_SPEC:
            self._process_pdf_context(visual_context)
        elif input_type in [VisualInputType.FIGMA_FILE, VisualInputType.SKETCH_FILE]:
            self._process_design_file_context(visual_context)
        
        # Store context
        self.visual_contexts[context_id] = visual_context
        
        # Save to disk
        self._save_visual_context(visual_context)
        
        return context_id
    
    def _detect_input_type(self, filename: str) -> VisualInputType:
        """Detect input type based on filename and extension"""
        ext = Path(filename).suffix.lower()
        
        if ext in self.supported_image_types:
            if 'screenshot' in filename.lower():
                return VisualInputType.SCREENSHOT
            elif 'mockup' in filename.lower() or 'design' in filename.lower():
                return VisualInputType.UI_MOCKUP
            else:
                return VisualInputType.DESIGN_REFERENCE
        elif ext == '.pdf':
            return VisualInputType.PDF_SPEC
        elif ext in ['.fig', '.sketch']:
            return VisualInputType.FIGMA_FILE if ext == '.fig' else VisualInputType.SKETCH_FILE
        else:
            return VisualInputType.DOCUMENT
    
    def _save_uploaded_file(self, file_data: bytes, filename: str, context_id: str) -> Path:
        """Save uploaded file to disk"""
        # Create safe filename
        safe_filename = f"{context_id}_{Path(filename).name}"
        file_path = self.uploads_dir / safe_filename
        
        with open(file_path, 'wb') as f:
            f.write(file_data)
        
        return file_path
    
    def _get_mime_type(self, filename: str) -> str:
        """Get MIME type from filename"""
        ext = Path(filename).suffix.lower()
        
        mime_types = {
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif',
            '.bmp': 'image/bmp',
            '.webp': 'image/webp',
            '.pdf': 'application/pdf',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.txt': 'text/plain',
            '.md': 'text/markdown',
            '.fig': 'application/figma',
            '.sketch': 'application/sketch'
        }
        
        return mime_types.get(ext, 'application/octet-stream')
    
    def _process_image_context(self, context: VisualContext):
        """Process image-based visual context"""
        try:
            # Load image
            image = Image.open(context.file_path)
            context.dimensions = image.size
            
            # Extract text (OCR)
            context.extracted_text = self._extract_text_from_image(image)
            
            # Analyze color palette
            context.color_palette = self._analyze_color_palette(image)
            
            # Analyze layout
            context.layout_analysis = self._analyze_layout(image)
            
            # Detect components
            context.component_detection = self._detect_components(image)
            
            # Calculate accessibility score
            context.accessibility_score = self._calculate_accessibility_score(image)
            
        except Exception as e:
            self.memory_system.log_event("visual_processing_error", {
                "context_id": context.context_id,
                "error": str(e),
                "file_path": context.file_path
            })
    
    def _process_document_context(self, context: VisualContext):
        """Process document-based visual context"""
        try:
            # Extract text from document
            context.extracted_text = self._extract_text_from_document(context.file_path)
            
            # Analyze document structure
            context.layout_analysis = self._analyze_document_structure(context.file_path)
            
        except Exception as e:
            self.memory_system.log_event("document_processing_error", {
                "context_id": context.context_id,
                "error": str(e),
                "file_path": context.file_path
            })
    
    def _process_pdf_context(self, context: VisualContext):
        """Process PDF specification context"""
        try:
            # Extract text and images from PDF
            pdf_data = self._extract_pdf_content(context.file_path)
            context.extracted_text = pdf_data.get('text', '')
            
            # Analyze PDF structure
            context.layout_analysis = {
                'pages': pdf_data.get('pages', 0),
                'sections': pdf_data.get('sections', []),
                'images': pdf_data.get('images', []),
                'tables': pdf_data.get('tables', [])
            }
            
        except Exception as e:
            self.memory_system.log_event("pdf_processing_error", {
                "context_id": context.context_id,
                "error": str(e),
                "file_path": context.file_path
            })
    
    def _process_design_file_context(self, context: VisualContext):
        """Process design file context (Figma, Sketch)"""
        try:
            # For now, we'll extract basic information
            # In production, this would use Figma/Sketch APIs
            context.extracted_text = f"Design file: {context.original_filename}"
            context.layout_analysis = {
                'type': context.input_type.value,
                'components': [],
                'styles': [],
                'assets': []
            }
            
        except Exception as e:
            self.memory_system.log_event("design_file_processing_error", {
                "context_id": context.context_id,
                "error": str(e),
                "file_path": context.file_path
            })
    
    def _extract_text_from_image(self, image: Image.Image) -> str:
        """Extract text from image using OCR"""
        try:
            # Convert to OpenCV format
            cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            
            # Use Tesseract OCR (would need to be installed)
            # For now, return placeholder
            return "Text extraction would be implemented with OCR"
            
        except Exception as e:
            return f"Text extraction failed: {str(e)}"
    
    def _analyze_color_palette(self, image: Image.Image) -> List[str]:
        """Analyze color palette from image"""
        try:
            # Convert to RGB if needed
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Resize for faster processing
            small_image = image.resize((150, 150))
            
            # Get colors
            colors = small_image.getcolors(maxcolors=10000)
            if not colors:
                return []
            
            # Sort by frequency and get top colors
            colors.sort(key=lambda x: x[0], reverse=True)
            
            # Convert to hex
            palette = []
            for count, (r, g, b) in colors[:self.analysis_config['max_colors']]:
                hex_color = f"#{r:02x}{g:02x}{b:02x}"
                palette.append(hex_color)
            
            return palette
            
        except Exception as e:
            return []
    
    def _analyze_layout(self, image: Image.Image) -> Dict[str, Any]:
        """Analyze layout structure of image"""
        try:
            width, height = image.size
            
            # Convert to grayscale for edge detection
            gray = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2GRAY)
            
            # Detect edges
            edges = cv2.Canny(gray, 50, 150)
            
            # Find contours
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # Analyze layout regions
            regions = []
            for contour in contours:
                x, y, w, h = cv2.boundingRect(contour)
                if w > self.analysis_config['component_min_size'] and h > self.analysis_config['component_min_size']:
                    regions.append({
                        'x': x,
                        'y': y,
                        'width': w,
                        'height': h,
                        'area': w * h,
                        'center': (x + w//2, y + h//2)
                    })
            
            # Sort regions by area
            regions.sort(key=lambda x: x['area'], reverse=True)
            
            return {
                'width': width,
                'height': height,
                'aspect_ratio': width / height,
                'regions': regions[:10],  # Top 10 regions
                'grid_analysis': self._analyze_grid_layout(regions, width, height)
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    def _analyze_grid_layout(self, regions: List[Dict], width: int, height: int) -> Dict[str, Any]:
        """Analyze grid-based layout"""
        try:
            # Simple grid analysis
            grid_size = self.analysis_config['layout_grid_size']
            cell_width = width // grid_size
            cell_height = height // grid_size
            
            # Count regions in each grid cell
            grid = [[0 for _ in range(grid_size)] for _ in range(grid_size)]
            
            for region in regions:
                center_x, center_y = region['center']
                grid_x = min(center_x // cell_width, grid_size - 1)
                grid_y = min(center_y // cell_height, grid_size - 1)
                grid[grid_y][grid_x] += 1
            
            return {
                'grid_size': grid_size,
                'cell_width': cell_width,
                'cell_height': cell_height,
                'grid_density': grid,
                'layout_type': self._classify_layout_type(grid)
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    def _classify_layout_type(self, grid: List[List[int]]) -> str:
        """Classify layout type based on grid analysis"""
        try:
            # Simple classification
            total_cells = len(grid) * len(grid[0])
            occupied_cells = sum(sum(row) for row in grid)
            density = occupied_cells / total_cells
            
            if density < 0.1:
                return "minimal"
            elif density < 0.3:
                return "clean"
            elif density < 0.6:
                return "balanced"
            else:
                return "dense"
                
        except Exception:
            return "unknown"
    
    def _detect_components(self, image: Image.Image) -> List[Dict[str, Any]]:
        """Detect UI components in image"""
        try:
            # This would use a trained component detection model
            # For now, return basic detection based on layout analysis
            
            layout = self._analyze_layout(image)
            regions = layout.get('regions', [])
            
            components = []
            for region in regions[:5]:  # Top 5 regions
                component_type = self._classify_component(region, image.size)
                components.append({
                    'type': component_type,
                    'bounds': {
                        'x': region['x'],
                        'y': region['y'],
                        'width': region['width'],
                        'height': region['height']
                    },
                    'confidence': 0.8,  # Placeholder
                    'properties': self._extract_component_properties(region, image)
                })
            
            return components
            
        except Exception as e:
            return []
    
    def _classify_component(self, region: Dict, image_size: Tuple[int, int]) -> str:
        """Classify component type based on region properties"""
        try:
            width, height = image_size
            region_width = region['width']
            region_height = region['height']
            
            # Simple classification based on size and position
            if region_width > width * 0.8:
                return "header" if region['y'] < height * 0.2 else "footer"
            elif region_height > height * 0.3:
                return "sidebar"
            elif region_width > width * 0.4 and region_height > height * 0.4:
                return "main_content"
            elif region_width < width * 0.2 and region_height < height * 0.1:
                return "button"
            else:
                return "content_block"
                
        except Exception:
            return "unknown"
    
    def _extract_component_properties(self, region: Dict, image: Image.Image) -> Dict[str, Any]:
        """Extract properties from component region"""
        try:
            # Crop region from image
            cropped = image.crop((region['x'], region['y'], 
                                region['x'] + region['width'], 
                                region['y'] + region['height']))
            
            # Analyze colors in region
            colors = self._analyze_color_palette(cropped)
            
            return {
                'colors': colors,
                'area': region['area'],
                'aspect_ratio': region['width'] / region['height']
            }
            
        except Exception:
            return {}
    
    def _calculate_accessibility_score(self, image: Image.Image) -> float:
        """Calculate accessibility score for image"""
        try:
            # Convert to grayscale
            gray = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2GRAY)
            
            # Calculate contrast
            mean_brightness = np.mean(gray)
            std_brightness = np.std(gray)
            contrast_score = min(std_brightness / 50.0, 1.0)
            
            # Calculate color diversity
            colors = self._analyze_color_palette(image)
            color_score = min(len(colors) / 5.0, 1.0)
            
            # Calculate layout score
            layout = self._analyze_layout(image)
            layout_type = layout.get('grid_analysis', {}).get('layout_type', 'unknown')
            layout_score = 0.8 if layout_type in ['clean', 'balanced'] else 0.5
            
            # Overall score
            overall_score = (contrast_score + color_score + layout_score) / 3.0
            
            return round(overall_score, 2)
            
        except Exception:
            return 0.5
    
    def _extract_text_from_document(self, file_path: str) -> str:
        """Extract text from document"""
        try:
            # This would use appropriate libraries for different document types
            # For now, return placeholder
            return f"Text extracted from document: {Path(file_path).name}"
            
        except Exception as e:
            return f"Text extraction failed: {str(e)}"
    
    def _analyze_document_structure(self, file_path: str) -> Dict[str, Any]:
        """Analyze document structure"""
        try:
            return {
                'type': 'document',
                'sections': [],
                'headings': [],
                'lists': [],
                'tables': []
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    def _extract_pdf_content(self, file_path: str) -> Dict[str, Any]:
        """Extract content from PDF"""
        try:
            doc = fitz.open(file_path)
            
            text = ""
            images = []
            tables = []
            
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                text += page.get_text()
                
                # Extract images
                image_list = page.get_images()
                for img_index, img in enumerate(image_list):
                    xref = img[0]
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image["image"]
                    images.append({
                        'page': page_num,
                        'index': img_index,
                        'size': len(image_bytes)
                    })
            
            doc.close()
            
            return {
                'text': text,
                'pages': len(doc),
                'images': images,
                'tables': tables,
                'sections': self._extract_pdf_sections(text)
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    def _extract_pdf_sections(self, text: str) -> List[Dict[str, Any]]:
        """Extract sections from PDF text"""
        try:
            # Simple section extraction based on headers
            lines = text.split('\n')
            sections = []
            current_section = None
            
            for line in lines:
                line = line.strip()
                if line and line.isupper() and len(line) < 100:
                    # Likely a header
                    if current_section:
                        sections.append(current_section)
                    
                    current_section = {
                        'title': line,
                        'content': '',
                        'level': 1
                    }
                elif current_section:
                    current_section['content'] += line + '\n'
            
            if current_section:
                sections.append(current_section)
            
            return sections
            
        except Exception:
            return []
    
    def create_visual_prompt(self, user_prompt: str, context_ids: List[str]) -> str:
        """Create a visual prompt with context"""
        prompt_id = str(uuid.uuid4())
        
        # Get visual contexts
        contexts = [self.visual_contexts.get(cid) for cid in context_ids if cid in self.visual_contexts]
        
        # Analyze contexts and generate instructions
        analysis_results = self._analyze_visual_contexts(contexts)
        generated_instructions = self._generate_instructions(user_prompt, contexts, analysis_results)
        
        # Create visual prompt
        visual_prompt = VisualPrompt(
            prompt_id=prompt_id,
            user_prompt=user_prompt,
            visual_contexts=contexts,
            analysis_results=analysis_results,
            generated_instructions=generated_instructions,
            created_at=datetime.now()
        )
        
        # Store prompt
        self.visual_prompts[prompt_id] = visual_prompt
        
        # Save to disk
        self._save_visual_prompt(visual_prompt)
        
        # Log to memory
        self.memory_system.log_event("visual_prompt_created", {
            "prompt_id": prompt_id,
            "context_count": len(contexts),
            "analysis_results": analysis_results
        })
        
        return prompt_id
    
    def _analyze_visual_contexts(self, contexts: List[VisualContext]) -> Dict[str, Any]:
        """Analyze multiple visual contexts together"""
        try:
            analysis = {
                'total_contexts': len(contexts),
                'context_types': {},
                'common_colors': [],
                'layout_patterns': [],
                'component_types': [],
                'accessibility_issues': [],
                'design_recommendations': []
            }
            
            # Analyze each context
            for context in contexts:
                # Count context types
                context_type = context.input_type.value
                analysis['context_types'][context_type] = analysis['context_types'].get(context_type, 0) + 1
                
                # Collect colors
                if context.color_palette:
                    analysis['common_colors'].extend(context.color_palette)
                
                # Collect layout patterns
                if context.layout_analysis:
                    layout_type = context.layout_analysis.get('grid_analysis', {}).get('layout_type', 'unknown')
                    analysis['layout_patterns'].append(layout_type)
                
                # Collect component types
                if context.component_detection:
                    for component in context.component_detection:
                        analysis['component_types'].append(component.get('type', 'unknown'))
                
                # Check accessibility
                if context.accessibility_score and context.accessibility_score < 0.7:
                    analysis['accessibility_issues'].append({
                        'context_id': context.context_id,
                        'score': context.accessibility_score,
                        'issues': self._identify_accessibility_issues(context)
                    })
            
            # Generate design recommendations
            analysis['design_recommendations'] = self._generate_design_recommendations(analysis)
            
            return analysis
            
        except Exception as e:
            return {'error': str(e)}
    
    def _identify_accessibility_issues(self, context: VisualContext) -> List[str]:
        """Identify accessibility issues in visual context"""
        issues = []
        
        if context.accessibility_score:
            if context.accessibility_score < 0.5:
                issues.append("Low contrast - consider improving color contrast")
            if context.accessibility_score < 0.7:
                issues.append("Limited color diversity - consider adding more color variation")
        
        if context.layout_analysis:
            layout_type = context.layout_analysis.get('grid_analysis', {}).get('layout_type', 'unknown')
            if layout_type == 'dense':
                issues.append("Dense layout - consider improving spacing and readability")
        
        return issues
    
    def _generate_design_recommendations(self, analysis: Dict[str, Any]) -> List[str]:
        """Generate design recommendations based on analysis"""
        recommendations = []
        
        # Color recommendations
        if len(analysis['common_colors']) > 0:
            unique_colors = list(set(analysis['common_colors']))
            if len(unique_colors) < 3:
                recommendations.append("Consider adding more color variation to improve visual hierarchy")
            elif len(unique_colors) > 8:
                recommendations.append("Consider reducing color palette for better consistency")
        
        # Layout recommendations
        layout_patterns = analysis['layout_patterns']
        if layout_patterns:
            most_common = max(set(layout_patterns), key=layout_patterns.count)
            if most_common == 'dense':
                recommendations.append("Consider using more whitespace for better readability")
            elif most_common == 'minimal':
                recommendations.append("Consider adding more content structure for better user guidance")
        
        # Component recommendations
        component_types = analysis['component_types']
        if component_types:
            if 'button' not in component_types:
                recommendations.append("Consider adding clear call-to-action buttons")
            if 'main_content' not in component_types:
                recommendations.append("Consider defining clear main content areas")
        
        return recommendations
    
    def _generate_instructions(self, user_prompt: str, contexts: List[VisualContext], 
                             analysis: Dict[str, Any]) -> List[str]:
        """Generate specific instructions based on visual context"""
        instructions = []
        
        # Add context-specific instructions
        for context in contexts:
            if context.input_type == VisualInputType.SCREENSHOT:
                instructions.append(f"Fix layout issues identified in screenshot: {context.original_filename}")
            
            elif context.input_type == VisualInputType.UI_MOCKUP:
                instructions.append(f"Implement design from mockup: {context.original_filename}")
            
            elif context.input_type == VisualInputType.DESIGN_REFERENCE:
                instructions.append(f"Apply design style from reference: {context.original_filename}")
            
            elif context.input_type == VisualInputType.PDF_SPEC:
                instructions.append(f"Implement specifications from PDF: {context.original_filename}")
        
        # Add analysis-based instructions
        if analysis.get('accessibility_issues'):
            instructions.append("Address accessibility issues: improve contrast and readability")
        
        if analysis.get('design_recommendations'):
            for rec in analysis['design_recommendations']:
                instructions.append(f"Design improvement: {rec}")
        
        # Add color palette instructions
        if analysis.get('common_colors'):
            colors = list(set(analysis['common_colors']))[:5]
            instructions.append(f"Use color palette: {', '.join(colors)}")
        
        return instructions
    
    def create_visual_diff(self, before_image_path: str, after_image_path: str) -> str:
        """Create visual difference analysis"""
        diff_id = str(uuid.uuid4())
        
        try:
            # Load images
            before_img = cv2.imread(before_image_path)
            after_img = cv2.imread(after_image_path)
            
            if before_img is None or after_img is None:
                raise ValueError("Could not load images")
            
            # Resize to same dimensions
            height, width = before_img.shape[:2]
            after_img = cv2.resize(after_img, (width, height))
            
            # Calculate difference
            diff = cv2.absdiff(before_img, after_img)
            gray_diff = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
            
            # Find significant differences
            _, thresh = cv2.threshold(gray_diff, 30, 255, cv2.THRESH_BINARY)
            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # Analyze differences
            diff_areas = []
            total_diff_area = 0
            
            for contour in contours:
                area = cv2.contourArea(contour)
                if area > 100:  # Minimum area threshold
                    x, y, w, h = cv2.boundingRect(contour)
                    diff_areas.append({
                        'x': x,
                        'y': y,
                        'width': w,
                        'height': h,
                        'area': area,
                        'type': self._classify_diff_type(area, w, h)
                    })
                    total_diff_area += area
            
            # Calculate severity
            total_area = width * height
            diff_percentage = total_diff_area / total_area
            severity = self._calculate_diff_severity(diff_percentage)
            
            # Generate summary
            change_summary = self._generate_diff_summary(diff_areas, severity)
            
            # Create visual diff
            visual_diff = VisualDiff(
                diff_id=diff_id,
                before_image=before_image_path,
                after_image=after_image_path,
                diff_areas=diff_areas,
                change_summary=change_summary,
                severity=severity,
                created_at=datetime.now()
            )
            
            # Store diff
            self.visual_diffs[diff_id] = visual_diff
            
            # Save to disk
            self._save_visual_diff(visual_diff)
            
            return diff_id
            
        except Exception as e:
            self.memory_system.log_event("visual_diff_error", {
                "diff_id": diff_id,
                "error": str(e)
            })
            return None
    
    def _classify_diff_type(self, area: float, width: int, height: int) -> str:
        """Classify type of difference"""
        if area < 500:
            return "minor_change"
        elif width > 100 and height > 100:
            return "major_change"
        elif width > 200 or height > 200:
            return "layout_change"
        else:
            return "content_change"
    
    def _calculate_diff_severity(self, diff_percentage: float) -> str:
        """Calculate severity of differences"""
        if diff_percentage < 0.05:
            return "low"
        elif diff_percentage < 0.15:
            return "medium"
        else:
            return "high"
    
    def _generate_diff_summary(self, diff_areas: List[Dict], severity: str) -> str:
        """Generate summary of differences"""
        if not diff_areas:
            return "No significant differences detected"
        
        change_types = [area['type'] for area in diff_areas]
        type_counts = {}
        for change_type in change_types:
            type_counts[change_type] = type_counts.get(change_type, 0) + 1
        
        summary_parts = [f"Detected {len(diff_areas)} change areas"]
        
        for change_type, count in type_counts.items():
            summary_parts.append(f"{count} {change_type.replace('_', ' ')}")
        
        summary_parts.append(f"Overall severity: {severity}")
        
        return ", ".join(summary_parts)
    
    def _save_visual_context(self, context: VisualContext):
        """Save visual context to disk"""
        context_path = self.processed_dir / f"{context.context_id}.json"
        with open(context_path, 'w') as f:
            json.dump(asdict(context), f, indent=2, default=str)
    
    def _save_visual_prompt(self, prompt: VisualPrompt):
        """Save visual prompt to disk"""
        prompt_path = self.processed_dir / f"prompt_{prompt.prompt_id}.json"
        with open(prompt_path, 'w') as f:
            json.dump(asdict(prompt), f, indent=2, default=str)
    
    def _save_visual_diff(self, diff: VisualDiff):
        """Save visual diff to disk"""
        diff_path = self.diffs_dir / f"diff_{diff.diff_id}.json"
        with open(diff_path, 'w') as f:
            json.dump(asdict(diff), f, indent=2, default=str)
    
    def get_visual_context(self, context_id: str) -> Optional[VisualContext]:
        """Get visual context by ID"""
        return self.visual_contexts.get(context_id)
    
    def get_visual_prompt(self, prompt_id: str) -> Optional[VisualPrompt]:
        """Get visual prompt by ID"""
        return self.visual_prompts.get(prompt_id)
    
    def get_visual_diff(self, diff_id: str) -> Optional[VisualDiff]:
        """Get visual diff by ID"""
        return self.visual_diffs.get(diff_id)
    
    def list_visual_contexts(self) -> List[Dict[str, Any]]:
        """List all visual contexts"""
        return [asdict(context) for context in self.visual_contexts.values()]
    
    def list_visual_prompts(self) -> List[Dict[str, Any]]:
        """List all visual prompts"""
        return [asdict(prompt) for prompt in self.visual_prompts.values()]
    
    def list_visual_diffs(self) -> List[Dict[str, Any]]:
        """List all visual diffs"""
        return [asdict(diff) for diff in self.visual_diffs.values()]
