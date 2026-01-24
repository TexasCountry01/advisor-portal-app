#!/usr/bin/env python3

with open('TECHNICIAN_WORKFLOW.md', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find line numbers for key sections
overview_header = None
overview_end = None
decision_tree1_header = None
decision_tree1_end = None
decision_tree2_header = None
decision_tree2_end = None
actions_start = None

for i, line in enumerate(lines):
    if line.startswith('## Technician Workflow Overview'):
        overview_header = i
    elif overview_header and line.startswith('## Decision'):
        overview_end = i
        decision_tree1_header = i
    elif decision_tree1_header and line.startswith('## Decision Tree: "Is This'):
        decision_tree1_end = i
        decision_tree2_header = i
    elif decision_tree2_header and line.strip().startswith('---') and i > decision_tree2_header + 50:
        decision_tree2_end = i
        actions_start = i
        break

print(f"Technician Workflow Overview: {overview_header}-{overview_end}")
print(f"Decision Tree 1: {decision_tree1_header}-{decision_tree1_end}")
print(f"Decision Tree 2: {decision_tree2_header}-{decision_tree2_end}")
print(f"Actions start: {actions_start}")

# Build new file: header + core actions + main content + diagrams
header = lines[:overview_header]
core_actions = lines[overview_end:decision_tree1_header]
main_content = lines[decision_tree2_end:len(lines)]

diagrams = lines[overview_header:overview_end] + lines[decision_tree1_header:decision_tree2_end]

new_content = header + core_actions + main_content
new_content.append('\n')
new_content.append('---\n')
new_content.append('\n')
new_content.append('## Reference Diagrams\n')
new_content.append('\n')
new_content.extend(diagrams)

with open('TECHNICIAN_WORKFLOW.md', 'w', encoding='utf-8') as f:
    f.writelines(new_content)

print("✓ Reorganized TECHNICIAN_WORKFLOW.md")
