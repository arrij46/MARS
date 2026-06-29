"""
PDF Generator Utility for User Stories

This module provides functions to convert user story JSON data into
well-formatted PDF documents using reportlab.
"""
from io import BytesIO
from typing import List, Dict, Any, Optional
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor


def generate_user_story_pdf(
    user_stories_data: Dict[str, Any],
    project_name: Optional[str] = None,
    output_stream: Optional[BytesIO] = None
) -> BytesIO:
    """
    Generate a PDF document from user stories JSON data.
    
    Args:
        user_stories_data: Dictionary containing user stories and metadata
            Expected format:
            {
                "user_stories": [
                    {
                        "user_story_id": "R1-US1",
                        "requirement_id": "R1",
                        "type": "FR",
                        "text": "As a user, I want..."
                    }
                ],
                "metadata": {...}
            }
        total_requirements: Total number of requirements
        project_name: Optional project name to include in header
        output_stream: Optional BytesIO stream to write to. If None, creates new stream.
    
    Returns:
        BytesIO: PDF file as bytes stream
    """
    # Create output stream if not provided
    if output_stream is None:
        output_stream = BytesIO()
    
    # Create PDF document
    doc = SimpleDocTemplate(
        output_stream,
        pagesize=letter,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=18
    )
    
    # Container for PDF elements
    story = []
    
    # Define styles
    styles = getSampleStyleSheet()
    
    # Custom title style
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=HexColor('#1a237e'),
        spaceAfter=30,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    # Custom heading style for user story ID
    story_id_style = ParagraphStyle(
        'StoryIdStyle',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=HexColor('#283593'),
        spaceAfter=12,
        spaceBefore=20,
        fontName='Helvetica-Bold'
    )
    
    # Custom style for labels (Actor, Story)
    label_style = ParagraphStyle(
        'LabelStyle',
        parent=styles['Normal'],
        fontSize=11,
        textColor=HexColor('#424242'),
        fontName='Helvetica-Bold',
        spaceAfter=6
    )
    
    # Custom style for story text
    story_text_style = ParagraphStyle(
        'StoryTextStyle',
        parent=styles['Normal'],
        fontSize=12,
        textColor=HexColor('#212121'),
        alignment=TA_JUSTIFY,
        spaceAfter=15,
        leftIndent=20
    )
    
    # Custom style for metadata
    metadata_style = ParagraphStyle(
        'MetadataStyle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=HexColor('#757575'),
        alignment=TA_CENTER,
        spaceAfter=20
    )
    
    # Add title
    title_text = project_name if project_name else "User Stories"
    story.append(Paragraph(title_text, title_style))
    story.append(Spacer(1, 0.2 * inch))
    
    # Add metadata if available
    metadata = user_stories_data.get("metadata", {})
    if metadata:
        total_stories = metadata.get("total_user_stories", 0)
        total_requirements = metadata.get("total_requirements", 0)
        metadata_text = f"Total User Stories: {total_stories} | Total Requirements: {total_requirements}"
        story.append(Paragraph(metadata_text, metadata_style))
        story.append(Spacer(1, 0.3 * inch))
    
    # Process each user story
    user_stories = user_stories_data.get("user_stories", [])
    
    if not user_stories:
        # No user stories available
        story.append(Paragraph(
            "No user stories generated yet.",
            styles['Normal']
        ))
    else:
        for idx, story_data in enumerate(user_stories):
            # Extract story information
            story_id = story_data.get("user_story_id", f"US-{idx + 1}")
            requirement_id = story_data.get("requirement_id", "N/A")
            story_type = story_data.get("type", "N/A")
            story_text = story_data.get("text", "")
            
            # Add page break for stories after the first one (except first)
            if idx > 0:
                story.append(PageBreak())
            
            # Add User Story ID as heading
            story.append(Paragraph(f"User Story ID: {story_id}", story_id_style))
            
            # Add requirement ID and type
            req_info = f"<b>Requirement ID:</b> {requirement_id} | <b>Type:</b> {story_type}"
            story.append(Paragraph(req_info, label_style))
            story.append(Spacer(1, 0.1 * inch))
            
            # Parse story text to extract Actor and Story
            # Format: "As a <role>, I want <action>, so that <benefit>"
            if story_text:
                # Split by common delimiters
                parts = story_text.split(", I want")
                if len(parts) >= 2:
                    actor_part = parts[0].replace("As a", "").strip()
                    rest = ", I want" + parts[1]
                    
                    # Extract benefit if "so that" exists
                    if "so that" in rest:
                        action_benefit = rest.split("so that")
                        action = action_benefit[0].replace(", I want", "").strip()
                        benefit = action_benefit[1].strip()
                    else:
                        action = rest.replace(", I want", "").strip()
                        benefit = ""
                    
                    # Add Actor
                    story.append(Paragraph("<b>Actor:</b>", label_style))
                    story.append(Paragraph(actor_part, story_text_style))
                    story.append(Spacer(1, 0.1 * inch))
                    
                    # Add Story (Action)
                    story.append(Paragraph("<b>Story:</b>", label_style))
                    story.append(Paragraph(action, story_text_style))
                    
                    # Add Benefit if available
                    if benefit:
                        story.append(Spacer(1, 0.1 * inch))
                        story.append(Paragraph("<b>Benefit:</b>", label_style))
                        story.append(Paragraph(benefit, story_text_style))
                
                # display full text
                story.append(Paragraph("<b>Final User Story:</b>", label_style))
                story.append(Paragraph(story_text, story_text_style))
            else:
                story.append(Paragraph("<b>Story:</b> (No text provided)", label_style))
    
    # Build PDF
    doc.build(story)
    
    # Reset stream position to beginning
    output_stream.seek(0)
    
    return output_stream


def generate_single_story_pdf(
    story_id: str,
    story_data: Dict[str, Any],
    project_name: Optional[str] = None
) -> BytesIO:
    """
    Generate PDF for a single user story.
    
    Args:
        story_id: User story identifier
        story_data: Dictionary containing single story data
        project_name: Optional project name
    
    Returns:
        BytesIO: PDF file as bytes stream
    """
    # Wrap single story in the expected format
    user_stories_data = {
        "user_stories": [story_data],
        "metadata": {}
    }
    
    return generate_user_story_pdf(user_stories_data, project_name)


def generate_batch_stories_pdf(
    stories_list: List[Dict[str, Any]],
    project_name: Optional[str] = None
) -> BytesIO:
    """
    Generate PDF for multiple user stories in batch.
    
    Args:
        stories_list: List of user story dictionaries
        project_name: Optional project name
    
    Returns:
        BytesIO: PDF file as bytes stream
    """
    user_stories_data = {
        "user_stories": stories_list,
        "metadata": {
            "total_user_stories": len(stories_list),
            "total_requirements": len(set(story.get("requirement_id", "N/A") for story in stories_list))
        }
    }
    
    return generate_user_story_pdf(user_stories_data, project_name)

