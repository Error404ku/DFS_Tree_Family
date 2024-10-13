# dfs.py

def get_ancestors(family_tree, person, max_level=20, dfs_steps=None):
    ancestors = []
    visited = set()
    stack = []
    father = family_tree[person].get('father')
    mother = family_tree[person].get('mother')
    
    if father:
        stack.append({'current': father, 'level': 1, 'side': 'ayah'})
    if mother:
        stack.append({'current': mother, 'level': 1, 'side': 'ibu'})

    while stack:
        node = stack.pop()
        current, level, side = node['current'], node['level'], node['side']
        key = (current, side)

        if current in family_tree and level <= max_level and key not in visited:
            visited.add(key)
            ancestors.append({"Relasi": side, "Nama": current})
            if family_tree[current]['father']:
                stack.append({'current': family_tree[current]['father'], 'level': level + 1, 'side': side})
            if family_tree[current]['mother']:
                stack.append({'current': family_tree[current]['mother'], 'level': level + 1, 'side': side})

    return ancestors

def get_descendants(family_tree, person, max_level=20, dfs_steps=None):
    descendants = []
    visited = set()
    stack = [{'current': person, 'level': 0}]
    generation_counters = {}

    while stack:
        node = stack.pop()
        current, level = node['current'], node['level']

        if level >= max_level or current not in family_tree:
            continue

        if current not in visited:
            visited.add(current)
            children = family_tree[current]["children"]

            for child in children:
                generation = level + 1
                if generation not in generation_counters:
                    generation_counters[generation] = 1
                else:
                    generation_counters[generation] += 1

                descendants.append({"Relasi": f"Generasi {generation}", "Nama": child})
                stack.append({'current': child, 'level': generation})

    return descendants

def find_person_dfs(family_tree, target_person, max_level=20):
    steps = []
    visited = set()
    stack = []

    top_ancestors = [person for person, data in family_tree.items() if not data.get('father') and not data.get('mother')]
    found = False

    for ancestor in top_ancestors:
        stack.append({'current': ancestor, 'path': [ancestor], 'level': 1})
        steps.append({'Action': 'Visit', 'Person': ancestor, 'Path': ancestor, 'Level': 1})

        while stack:
            node = stack[-1]
            current, path, level = node['current'], node['path'], node['level']
            if current == target_person:
                found = True
                break
            children = family_tree[current].get('children', [])

            if children:
                next_child = children.pop(0)
                if next_child not in visited:
                    stack.append({'current': next_child, 'path': path + [next_child], 'level': level + 1})
                    steps.append({'Action': 'Add', 'Person': next_child, 'Path': ' -> '.join(path + [next_child]), 'Level': level + 1})
            else:
                stack.pop()
                steps.append({'Action': 'Backtrack', 'Person': current, 'Path': ' -> '.join(path), 'Level': level})

        if found:
            break

    return steps, found
