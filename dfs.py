# dfs.py

def get_ancestors(family_tree, person, max_level=20, dfs_steps=None):
    ancestors = []
    visited = set()
    stack = []
    father = family_tree[person].get('father')
    if father:
        stack.append({'current': father, 'level': 1, 'side': 'ayah'})
    mother = family_tree[person].get('mother')
    if mother:
        stack.append({'current': mother, 'level': 1, 'side': 'ibu'})

    while stack:
        node = stack.pop()
        current = node['current']
        level = node['level']
        side = node['side']
        key = (current, side)
        if current and current in family_tree and level <= max_level and key not in visited:
            visited.add(key)
            if dfs_steps is not None:
                dfs_steps.append({
                    "Action": "Visit",
                    "Person": current,
                    "Level": level,
                    "Side": side
                })
            father = family_tree[current].get('father')
            mother = family_tree[current].get('mother')
            # Tentukan relasi
            if level == 1:
                relation = "ayah" if side == "ayah" else "ibu"
            else:
                is_male = family_tree[current]['gender'] == 'male'
                ancestor_type = "kakek" if is_male else "nenek"
                generation = level - 1
                if generation == 1:
                    relation = f"{ancestor_type} dari {side}"
                else:
                    relation = f"{ancestor_type} ke-{generation -1} dari {side}"
            ancestors.append({"Relasi": relation, "Nama": f"{current} ({family_tree[current]['gender']})"})
            # Tambahkan ke stack
            if father:
                if dfs_steps is not None:
                    dfs_steps.append({
                        "Action": "Add to Stack",
                        "Person": father,
                        "Level": level +1,
                        "Side": side
                    })
                stack.append({'current': father, 'level': level +1, 'side': side})
            if mother:
                if dfs_steps is not None:
                    dfs_steps.append({
                        "Action": "Add to Stack",
                        "Person": mother,
                        "Level": level +1,
                        "Side": side
                    })
                stack.append({'current': mother, 'level': level +1, 'side': side})
    return ancestors

def get_descendants(family_tree, person, max_level=20, dfs_steps=None):
    descendants = []
    visited = set()
    stack = [{'current': person, 'level': 0}]  # Mulai dengan level 0 untuk generasi 1

    # Dictionary untuk menghitung nomor anak per generasi
    generation_counters = {}

    while stack:
        node = stack.pop()
        current = node['current']
        level = node['level']

        if level >= max_level or current not in family_tree:
            continue

        if current not in visited:
            visited.add(current)
            if dfs_steps is not None:
                dfs_steps.append({
                    "Action": "Visit",
                    "Person": current,
                    "Level": level
                })

            children = family_tree[current]["children"]

            for child in reversed(children):  # reverse untuk LIFO
                if child not in visited:
                    # Hitung generasi untuk anak
                    generasi = level + 1  # generasi 1 untuk anak langsung

                    # Inisialisasi counter untuk generasi ini jika belum ada
                    if generasi not in generation_counters:
                        generation_counters[generasi] = 1
                    else:
                        generation_counters[generasi] += 1

                    # Tentukan nomor anak ke
                    anak_ke = generation_counters[generasi]

                    relation = f"anak ke-{anak_ke} dari generasi {generasi}"

                    descendants.append({"Relasi": relation, "Nama": f"{child} ({family_tree[child]['gender']})"})

                    if dfs_steps is not None:
                        dfs_steps.append({
                            "Action": "Add to Stack",
                            "Person": child,
                            "Level": level + 1
                        })

                    stack.append({'current': child, 'level': level +1})

        else:
            if dfs_steps is not None:
                dfs_steps.append({
                    "Action": "Backtrack",
                    "Person": current,
                    "Level": level
                })
    return descendants

def find_person_dfs(family_tree, target_person, max_level=20):
    steps = []
    visited = set()
    stack = []

    # Temukan semua leluhur tertinggi (orang tanpa ayah dan ibu)
    top_ancestors = [person for person, data in family_tree.items() if data.get('father') is None and data.get('mother') is None]

    found = False

    for ancestor in top_ancestors:
        stack.append({'current_person': ancestor, 'path': [ancestor], 'level': 1, 'child_index': 0})
        steps.append({
            'Action': 'Add to Stack',
            'Person': ancestor,
            'Path': ' -> '.join([ancestor]),
            'Level': 1
        })

        while stack:
            node = stack[-1]  # Lihat node di atas stack tanpa menghapusnya
            current_person = node['current_person']
            path = node['path']
            level = node['level']
            child_index = node['child_index']

            if current_person not in visited:
                steps.append({
                    'Action': 'Visit',
                    'Person': current_person,
                    'Path': ' -> '.join(path),
                    'Level': level
                })
                visited.add(current_person)

            if current_person == target_person:
                found = True
                break

            # Dapatkan anak-anak dari orang saat ini
            children = family_tree[current_person].get('children', [])
            if child_index < len(children) and level < max_level:
                next_child = children[child_index]
                node['child_index'] += 1  # Increment child index for current node

                if next_child not in visited:
                    stack.append({'current_person': next_child, 'path': path + [next_child], 'level': level + 1, 'child_index': 0})
                    steps.append({
                        'Action': 'Add to Stack',
                        'Person': next_child,
                        'Path': ' -> '.join(path + [next_child]),
                        'Level': level + 1
                    })
            else:
                # Semua anak telah dikunjungi, backtrack
                popped_node = stack.pop()
                steps.append({
                    'Action': 'Backtrack',
                    'Person': popped_node['current_person'],
                    'Path': ' -> '.join(popped_node['path']),
                    'Level': popped_node['level']
                })

        if found:
            break

    return steps, found
