#!/usr/bin/env python3

def reorganize_tech_workflow_v2():
    """Reorganize TECHNICIAN_WORKFLOW.md - move all diagrams to bottom"""
    with open('TECHNICIAN_WORKFLOW.md', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Split by the "---" that separates role overview from diagrams
    # We'll keep: header + role overview + core actions + "---"
    # Then: all action sections (remove diagram interludes)
    # Finally: add all diagrams at end
    
    lines = content.split('\n')
    
    # Find key markers
    overview_end = None
    core_actions_start = None
    core_actions_end = None
    actions_start = None
    
    for i, line in enumerate(lines):
        if line.startswith('## Technician Workflow Overview'):
            overview_start = i
        elif line.startswith('## Core Technician Actions'):
            core_actions_start = i
        elif core_actions_start and line.startswith('---') and i > core_actions_start:
            core_actions_end = i
        elif line.startswith('## Technician Actions by Case Status'):
            actions_start = i
            break
    
    # Extract sections
    header_and_overview = '\n'.join(lines[:core_actions_start])
    core_actions = '\n'.join(lines[core_actions_start:core_actions_end+1])
    
    # From actions_start onwards, remove all diagram code blocks
    remaining = '\n'.join(lines[actions_start:])
    
    # Remove diagram code blocks from remaining content
    cleaned_remaining = remove_diagrams(remaining)
    
    # Extract all diagrams from the original file
    diagrams = extract_diagrams(content)
    
    # Rebuild file
    output = header_and_overview + '\n' + core_actions + '\n' + cleaned_remaining
    
    if diagrams:
        output += '\n\n---\n\n## Reference Diagrams\n\n' + diagrams
    
    with open('TECHNICIAN_WORKFLOW.md', 'w', encoding='utf-8') as f:
        f.write(output)
    
    print("✓ Reorganized TECHNICIAN_WORKFLOW.md")

def remove_diagrams(text):
    """Remove all code block diagrams from text"""
    lines = text.split('\n')
    result = []
    in_diagram = False
    
    for line in lines:
        if line.strip().startswith('```'):
            in_diagram = not in_diagram
            # Skip the line with backticks if it's a diagram
            if in_diagram:
                continue
        elif not in_diagram:
            result.append(line)
    
    return '\n'.join(result)

def extract_diagrams(text):
    """Extract all code block diagrams from text"""
    lines = text.split('\n')
    diagrams = []
    in_diagram = False
    current_diagram = []
    diagram_header = None
    
    for i, line in enumerate(lines):
        # Check if this line is a diagram header (like "## Decision Tree:")
        if line.startswith('##') and i + 1 < len(lines) and lines[i + 1].strip().startswith('```'):
            diagram_header = line
        
        if line.strip().startswith('```'):
            if not in_diagram:
                in_diagram = True
                if diagram_header:
                    diagrams.append(diagram_header)
                    diagram_header = None
                diagrams.append(line)
            else:
                in_diagram = False
                diagrams.append(line)
        elif in_diagram or (diagram_header and not line.strip()):
            diagrams.append(line)
    
    return '\n'.join(diagrams)

if __name__ == '__main__':
    reorganize_tech_workflow_v2()
