import streamlit as st
import pandas as pd
from neo4j import GraphDatabase

# === Konfigurasi Koneksi Neo4j ===
NEO4J_URI = "bolt://localhost:7687"  # Ganti dengan URI Neo4j Anda
NEO4J_USER = "neo4j"                  # Ganti dengan username Neo4j Anda
NEO4J_PASSWORD = "password"           # Ganti dengan password Neo4j Anda

# Mengelola driver Neo4j dengan cache_resource
@st.cache_resource
def get_driver():
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    return driver

driver = get_driver()

# Fungsi untuk menutup driver saat aplikasi selesai
def close_driver():
    driver.close()

# Menggunakan event API Streamlit untuk menutup driver saat shutdown
# st.on_event("shutdown", close_driver)

# === Fungsi Utama ===

# Fungsi untuk menambah relasi
def add_relation(person, relation, name, gender):
    with driver.session() as session:
        # Pastikan node `person` ada
        session.run("""
            MERGE (p:Person {name: $person_name})
            ON CREATE SET p.gender = $person_gender
            """, person_name=person, person_gender="unknown")

        # Pastikan node `name` ada
        session.run("""
            MERGE (r:Person {name: $relation_name})
            ON CREATE SET r.gender = $relation_gender
            """, relation_name=name, relation_gender=gender if gender else "unknown")

        # Tambahkan relasi sesuai jenisnya
        if relation == "Ayah":
            st.write(f"Adding Ayah relationship: {name} is Ayah of {person}")
            session.run("""
                MATCH (child:Person {name: $person_name}), (father:Person {name: $relation_name})
                MERGE (father)-[:FATHER_OF]->(child)
                SET father.gender = 'male'
                """, person_name=person, relation_name=name)
            # Cari ibu dari `person` dan tambahkan relasi Suami-Istri antara Ayah-Ibu
            mother = session.run("""
                MATCH (child:Person {name: $person_name})<-[:MOTHER_OF]-(mother:Person)
                RETURN mother.name AS mother_name
                """, person_name=person).single()
            if mother and mother['mother_name']:
                session.run("""
                    MATCH (father:Person {name: $father_name}), (mother:Person {name: $mother_name})
                    MERGE (father)-[:MARRIED_TO]-(mother)
                    """, father_name=name, mother_name=mother['mother_name'])
                st.write(f"Created MARRIED_TO relationship between {name} and {mother['mother_name']}")
            # Otomatisasi relasi lainnya
            create_siblings(session, parent_name=name, child_name=person)
            create_uncles_aunts(session, child_name=person)
            create_sepupu(session, parent_name=name, child_name=person)

        elif relation == "Ibu":
            st.write(f"Adding Ibu relationship: {name} is Ibu of {person}")
            session.run("""
                MATCH (child:Person {name: $person_name}), (mother:Person {name: $relation_name})
                MERGE (mother)-[:MOTHER_OF]->(child)
                SET mother.gender = 'female'
                """, person_name=person, relation_name=name)
            # Cari ayah dari `person` dan tambahkan relasi Suami-Istri antara Ayah-Ibu
            father = session.run("""
                MATCH (child:Person {name: $person_name})<-[:FATHER_OF]-(father:Person)
                RETURN father.name AS father_name
                """, person_name=person).single()
            if father and father['father_name']:
                session.run("""
                    MATCH (father:Person {name: $father_name}), (mother:Person {name: $mother_name})
                    MERGE (father)-[:MARRIED_TO]-(mother)
                    """, father_name=father['father_name'], mother_name=name)
                st.write(f"Created MARRIED_TO relationship between {father['father_name']} and {name}")
            # Otomatisasi relasi lainnya
            create_siblings(session, parent_name=name, child_name=person)
            create_uncles_aunts(session, child_name=person)
            create_sepupu(session, parent_name=name, child_name=person)

        elif relation == "Anak":
            st.write(f"Adding Anak relationship: {name} is Anak of {person}")
            # Ambil gender dari `person` dari database
            result = session.run("""
                MATCH (p:Person {name: $person_name})
                RETURN p.gender AS gender
                """, person_name=person)
            record = result.single()
            if record and record['gender']:
                person_gender = record['gender']
            else:
                person_gender = 'unknown'
            if person_gender == 'male':
                parent_relation = 'FATHER_OF'
            elif person_gender == 'female':
                parent_relation = 'MOTHER_OF'
            else:
                # Jika gender tidak diketahui, minta pengguna untuk memasukkan gender
                st.error(f"Gender dari {person} tidak diketahui. Silakan perbarui gender terlebih dahulu.")
                return
            session.run(f"""
                MATCH (parent:Person {{name: $person_name}}), (child:Person {{name: $relation_name}})
                MERGE (parent)-[:{parent_relation}]->(child)
                SET child.gender = $child_gender
                """, person_name=person, relation_name=name, child_gender=gender if gender else "unknown")
            st.write(f"Created {parent_relation} relationship between {person} and {name}")
            # Otomatisasi relasi Saudara
            create_siblings(session, parent_name=person, child_name=name)
            # Otomatisasi relasi Paman/Bibi
            create_uncles_aunts(session, child_name=name)
            # Otomatisasi relasi Sepupu
            create_sepupu(session, parent_name=person, child_name=name)

        elif relation == "Suami":
            st.write(f"Adding Suami relationship: {name} is Suami of {person}")
            session.run("""
                MATCH (wife:Person {name: $person_name}), (husband:Person {name: $relation_name})
                MERGE (husband)-[:MARRIED_TO]-(wife)
                SET husband.gender = 'male'
                """, person_name=person, relation_name=name)
            # Update gender wife jika belum diset
            session.run("""
                MATCH (wife:Person {name: $person_name})
                SET wife.gender = 'female'
                """, person_name=person)
            st.write(f"Set gender 'female' for {person}")
            # Otomatisasi relasi mertua
            create_inlaws(session, person_name=name, spouse_name=person)

        elif relation == "Istri":
            st.write(f"Adding Istri relationship: {name} is Istri of {person}")
            session.run("""
                MATCH (husband:Person {name: $person_name}), (wife:Person {name: $relation_name})
                MERGE (husband)-[:MARRIED_TO]-(wife)
                SET wife.gender = 'female'
                """, person_name=person, relation_name=name)
            # Update gender husband jika belum diset
            session.run("""
                MATCH (husband:Person {name: $person_name})
                SET husband.gender = 'male'
                """, person_name=person)
            st.write(f"Set gender 'male' for {person}")
            # Otomatisasi relasi mertua
            create_inlaws(session, person_name=name, spouse_name=person)

        elif relation == "Saudara":
            st.write(f"Adding Saudara relationship: {name} is Saudara of {person}")
            session.run("""
                MATCH (p1:Person {name: $person1}), (p2:Person {name: $person2})
                MERGE (p1)-[:SAUDARA]-(p2)
                """, person1=person, person2=name)
            st.write(f"Created SAUDARA relationship between {person} and {name}")
            
            # Setelah menambahkan hubungan saudara, perbarui sepupu untuk semua anak
            children_person = session.run("""
                MATCH (p:Person {name: $person_name})-[:FATHER_OF|MOTHER_OF]->(child:Person)
                RETURN child.name AS child_name
                """, person_name=person).values("child_name")
            
            children_sibling = session.run("""
                MATCH (sibling:Person {name: $sibling_name})-[:FATHER_OF|MOTHER_OF]->(child:Person)
                RETURN child.name AS child_name
                """, sibling_name=name).values("child_name")
            
            # Buat hubungan sepupu antara semua anak dari person dan anak dari saudara
            for child_p in children_person:
                for child_s in children_sibling:
                    if child_p != child_s:  # Hindari membuat sepupu diri sendiri
                        session.run("""
                            MATCH (child_p:Person {name: $child_p}), (child_s:Person {name: $child_s})
                            MERGE (child_p)-[:SEPAKU_OF]->(child_s)
                            MERGE (child_s)-[:SEPAKU_OF]->(child_p)
                            """, child_p=child_p, child_s=child_s)
                        st.success(f"Created SEPAKU_OF relationship between {child_p} and {child_s}")

        elif relation == "Mertua":
            st.write(f"Adding Mertua relationship: {name} is Mertua of {person}")
            # Implementasi penambahan mertua
            session.run("""
                MATCH (mertua:Person {name: $relation_name})<-[:FATHER_OF|MOTHER_OF]-(parent:Person)
                MATCH (child:Person {name: $person_name})
                MERGE (mertua)-[:MERTUA_OF]->(child)
                MERGE (child)-[:MENANTU_OF]->(mertua)
                """, relation_name=name, person_name=person)
            st.success(f"Created MERTUA_OF and MENANTU_OF relationships between {name} and {person}")

        elif relation == "Sepupu":
            st.warning("Penambahan relasi 'Sepupu' secara otomatis sudah diatur. Tidak perlu menambahkannya secara manual.")

        else:
            st.error(f"Relasi '{relation}' belum diimplementasikan.")

# Fungsi untuk membuat relasi Saudara secara otomatis
def create_siblings(session, parent_name, child_name):
    # Cari semua anak dari orang tua yang sama kecuali anak yang baru ditambahkan
    siblings = session.run("""
        MATCH (parent:Person)-[:FATHER_OF|MOTHER_OF]->(sibling:Person)
        WHERE parent.name = $parent_name AND sibling.name <> $child_name
        RETURN DISTINCT sibling.name AS sibling_name
        """, parent_name=parent_name, child_name=child_name)

    for record in siblings:
        sibling_name = record['sibling_name']
        # Tambahkan relasi Saudara dua arah
        session.run("""
            MATCH (p1:Person {name: $person1}), (p2:Person {name: $person2})
            MERGE (p1)-[:SAUDARA]-(p2)
            """, person1=child_name, person2=sibling_name)
        st.write(f"Created SAUDARA relationship between {child_name} and {sibling_name}")

# Fungsi untuk membuat relasi Paman/Bibi secara otomatis
def create_uncles_aunts(session, child_name):
    # Cari ayah dan ibu dari anak
    parents = session.run("""
        MATCH (parent:Person)-[:FATHER_OF|MOTHER_OF]->(child:Person {name: $child_name})
        RETURN parent.name AS parent_name, parent.gender AS parent_gender
        """, child_name=child_name)

    for record in parents:
        parent_name = record['parent_name']
        parent_gender = record['parent_gender']
        # Cari saudara kandung dari orang tua (paman/bibi)
        siblings = session.run("""
            MATCH (sibling:Person)-[:SAUDARA]-(parent:Person {name: $parent_name})
            RETURN sibling.name AS sibling_name, sibling.gender AS sibling_gender
            """, parent_name=parent_name)

        for sib in siblings:
            sibling_name = sib['sibling_name']
            sibling_gender = sib['sibling_gender']
            if sibling_gender == 'male':
                # Sibling adalah paman
                session.run("""
                    MATCH (uncle:Person {name: $uncle_name}), (child:Person {name: $child_name})
                    MERGE (uncle)-[:PAMAN_OF]->(child)
                    """, uncle_name=sibling_name, child_name=child_name)
                st.write(f"Created PAMAN_OF relationship between {sibling_name} and {child_name}")
            elif sibling_gender == 'female':
                # Sibling adalah bibi
                session.run("""
                    MATCH (aunt:Person {name: $aunt_name}), (child:Person {name: $child_name})
                    MERGE (aunt)-[:BIBI_OF]->(child)
                    """, aunt_name=sibling_name, child_name=child_name)
                st.write(f"Created BIBI_OF relationship between {sibling_name} and {child_name}")

# Fungsi untuk membuat relasi Sepupu secara otomatis
def create_sepupu(session, parent_name, child_name):
    st.write(f"Creating SEPAKU_OF relationships for {child_name} based on parent {parent_name}")
    
    # Cari saudara kandung dari parent_name (orang tua)
    siblings = session.run("""
        MATCH (sibling:Person)-[:SAUDARA]-(parent:Person {name: $parent_name})
        RETURN sibling.name AS sibling_name
        """, parent_name=parent_name)

    for record in siblings:
        sibling_name = record['sibling_name']
        st.write(f"Found sibling of {parent_name}: {sibling_name}")
        
        # Cari anak-anak dari saudara kandung tersebut (sepupu)
        cousins = session.run("""
            MATCH (sibling:Person {name: $sibling_name})-[:FATHER_OF|MOTHER_OF]->(cousin:Person)
            RETURN cousin.name AS cousin_name
            """, sibling_name=sibling_name)

        for cousin in cousins:
            cousin_name = cousin['cousin_name']
            if cousin_name != child_name:  # Hindari membuat sepupu diri sendiri
                # Buat relasi Sepupu dua arah
                session.run("""
                    MATCH (child_p:Person {name: $child_p}), (cousin:Person {name: $cousin_name})
                    MERGE (child_p)-[:SEPAKU_OF]->(cousin)
                    MERGE (cousin)-[:SEPAKU_OF]->(child_p)
                    """, child_p=child_name, cousin_name=cousin_name)
                st.success(f"Created SEPAKU_OF relationship between {child_name} and {cousin_name}")

# Fungsi untuk membuat relasi Mertua secara otomatis
def create_inlaws(session, person_name, spouse_name):
    # Cari orang tua dari orang yang dinikahi
    parents = session.run("""
        MATCH (parent:Person)-[:FATHER_OF|MOTHER_OF]->(spouse:Person {name: $spouse_name})
        RETURN parent.name AS parent_name, parent.gender AS parent_gender
        """, spouse_name=spouse_name)

    for record in parents:
        parent_name = record['parent_name']
        parent_gender = record['parent_gender']
        # Tambahkan relasi Mertua dua arah
        session.run("""
            MATCH (mertua:Person {name: $parent_name}), (menantu:Person {name: $person_name})
            MERGE (mertua)-[:MERTUA_OF]->(menantu)
            MERGE (menantu)-[:MENANTU_OF]->(mertua)
            """, parent_name=parent_name, person_name=person_name)
        st.write(f"Created MERTUA_OF relationship between {parent_name} and {person_name}")

# Fungsi untuk mengambil struktur keluarga dari Neo4j
def get_family_tree():
    family_tree = {}
    with driver.session() as session:
        # Mengambil data individu
        result = session.run("""
            MATCH (p:Person)
            RETURN p.name AS name, p.gender AS gender
        """)

        # Menyimpan data awal
        for record in result:
            name = record['name']
            gender = record['gender']
            family_tree[name] = {
                "father": None,
                "mother": None,
                "children": [],
                "spouse": None,
                "siblings": [],
                "uncles_aunts": [],
                "children_inlaw": [],
                "cousins": [],
                "gender": gender,
                "inlaws": []  # Menambahkan kunci untuk Mertua
            }

        # Mengambil relasi orang tua dan anak
        result = session.run("""
            MATCH (parent:Person)-[r:FATHER_OF|MOTHER_OF]->(child:Person)
            RETURN parent.name AS parent_name, child.name AS child_name, type(r) AS relation
        """)

        for record in result:
            parent_name = record['parent_name']
            child_name = record['child_name']
            relation = record['relation']
            if relation in ['FATHER_OF', 'MOTHER_OF']:
                if child_name in family_tree:
                    if relation == 'FATHER_OF':
                        family_tree[child_name]['father'] = parent_name
                    else:
                        family_tree[child_name]['mother'] = parent_name
                if parent_name in family_tree:
                    if child_name not in family_tree[parent_name]['children']:
                        family_tree[parent_name]['children'].append(child_name)

        # Mengambil relasi pasangan
        result = session.run("""
            MATCH (p1:Person)-[:MARRIED_TO]-(p2:Person)
            RETURN p1.name AS person1, p2.name AS person2
        """)

        for record in result:
            person1 = record['person1']
            person2 = record['person2']
            if person1 in family_tree:
                family_tree[person1]['spouse'] = person2
            if person2 in family_tree:
                family_tree[person2]['spouse'] = person1

        # Mengambil relasi saudara
        result = session.run("""
            MATCH (p1:Person)-[:SAUDARA]-(p2:Person)
            RETURN p1.name AS person1, p2.name AS person2
        """)

        for record in result:
            person1 = record['person1']
            person2 = record['person2']
            if person1 in family_tree and person2 not in family_tree[person1]['siblings']:
                family_tree[person1]['siblings'].append(person2)
            if person2 in family_tree and person1 not in family_tree[person2]['siblings']:
                family_tree[person2]['siblings'].append(person1)

        # Mengambil relasi paman/bibi
        result = session.run("""
            MATCH (p:Person)-[r:PAMAN_OF|BIBI_OF]->(child:Person)
            RETURN p.name AS relative_name, child.name AS child_name, type(r) AS relation
        """)

        for record in result:
            relative_name = record['relative_name']
            child_name = record['child_name']
            relation = record['relation']
            if child_name in family_tree and relative_name not in family_tree[child_name]['uncles_aunts']:
                family_tree[child_name]['uncles_aunts'].append(relative_name)

        # Mengambil relasi Sepupu
        result = session.run("""
            MATCH (p1:Person)-[:SEPAKU_OF]-(p2:Person)
            RETURN p1.name AS person1, p2.name AS person2
        """)

        for record in result:
            person1 = record['person1']
            person2 = record['person2']
            if person1 in family_tree and person2 not in family_tree[person1]['cousins']:
                family_tree[person1]['cousins'].append(person2)
            if person2 in family_tree and person1 not in family_tree[person2]['cousins']:
                family_tree[person2]['cousins'].append(person1)

        # Mengambil relasi Mertua
        result = session.run("""
            MATCH (mertua:Person)-[r:MERTUA_OF]->(menantu:Person)
            RETURN mertua.name AS mertua_name, menantu.name AS menantu_name, type(r) AS relation
        """)

        for record in result:
            mertua_name = record['mertua_name']
            menantu_name = record['menantu_name']
            relation = record['relation']
            if menantu_name in family_tree:
                if mertua_name not in family_tree[menantu_name]['inlaws']:
                    family_tree[menantu_name]['inlaws'].append(mertua_name)
            if mertua_name in family_tree:
                if menantu_name not in family_tree[mertua_name]['children_inlaw']:
                    family_tree[mertua_name]['children_inlaw'].append(menantu_name)

    return family_tree

# Fungsi untuk mendapatkan semua individu
def get_all_individuals():
    with driver.session() as session:
        result = session.run("MATCH (p:Person) RETURN p.name AS name")
        return [record['name'] for record in result]

# Fungsi untuk mendapatkan semua leluhur
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

# Fungsi untuk mendapatkan semua keturunan
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

# Fungsi DFS yang telah dimodifikasi
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

# Fungsi batch untuk memperbarui semua relasi berdasarkan data eksisting
def update_all_relations():
    with driver.session() as session:
        st.write("Memulai pembaruan semua relasi...")

        # (Opsional) Menghapus semua relasi MERTUA_OF dan MENANTU_OF yang sudah ada
        session.run("""
            MATCH (p:Person)-[r:MERTUA_OF|MENANTU_OF]->(c:Person)
            DELETE r
        """)
        st.write("Menghapus semua relasi MERTUA_OF dan MENANTU_OF yang sudah ada.")

        # Ambil semua orang tua dan anak-anak mereka
        parents_children = session.run("""
            MATCH (parent:Person)-[:FATHER_OF|MOTHER_OF]->(child:Person)
            RETURN parent.name AS parent, collect(child.name) AS children
        """)

        # Simpan dalam dictionary
        parent_dict = {}
        for record in parents_children:
            parent = record['parent']
            children = record['children']
            parent_dict[parent] = children
            st.write(f"Orang Tua: {parent}, Anak-anak: {children}")

        # Cari semua pasangan orang tua (MARRIED_TO)
        marriages = session.run("""
            MATCH (p1:Person)-[:MARRIED_TO]-(p2:Person)
            RETURN p1.name AS spouse1, p2.name AS spouse2
        """)

        marriage_list = []
        for marriage in marriages:
            spouse1 = marriage['spouse1']
            spouse2 = marriage['spouse2']
            marriage_list.append((spouse1, spouse2))
            st.write(f"Pernikahan ditemukan antara {spouse1} dan {spouse2}")

        # Proses setiap pasangan untuk membuat relasi Mertua
        for spouse1, spouse2 in marriage_list:
            # Cari orang tua dari spouse1
            parents_spouse1 = session.run("""
                MATCH (parent:Person)-[:FATHER_OF|MOTHER_OF]->(spouse:Person {name: $spouse_name})
                RETURN parent.name AS parent_name, parent.gender AS parent_gender
            """, spouse_name=spouse1)

            for record in parents_spouse1:
                parent_name = record['parent_name']
                parent_gender = record['parent_gender']
                # Buat relasi MERTUA_OF dan MENANTU_OF
                session.run("""
                    MATCH (mertua:Person {name: $parent_name}), (menantu:Person {name: $spouse2})
                    MERGE (mertua)-[:MERTUA_OF]->(menantu)
                    MERGE (menantu)-[:MENANTU_OF]->(mertua)
                """, parent_name=parent_name, spouse2=spouse2)
                st.success(f"Created MERTUA_OF relationship between {parent_name} and {spouse2}")

            # Cari orang tua dari spouse2
            parents_spouse2 = session.run("""
                MATCH (parent:Person)-[:FATHER_OF|MOTHER_OF]->(spouse:Person {name: $spouse_name})
                RETURN parent.name AS parent_name, parent.gender AS parent_gender
            """, spouse_name=spouse2)

            for record in parents_spouse2:
                parent_name = record['parent_name']
                parent_gender = record['parent_gender']
                # Buat relasi MERTUA_OF dan MENANTU_OF
                session.run("""
                    MATCH (mertua:Person {name: $parent_name}), (menantu:Person {name: $spouse1})
                    MERGE (mertua)-[:MERTUA_OF]->(menantu)
                    MERGE (menantu)-[:MENANTU_OF]->(mertua)
                """, parent_name=parent_name, spouse1=spouse1)
                st.success(f"Created MERTUA_OF relationship between {parent_name} and {spouse1}")

        # Proses relasi Sepupu
        for parent, children in parent_dict.items():
            st.write(f"Memproses orang tua: {parent}")
            # Cari saudara kandung dari orang tua
            siblings = session.run("""
                MATCH (sibling:Person)-[:SAUDARA]-(parent:Person {name: $parent})
                RETURN sibling.name AS sibling_name
            """, parent=parent)

            for sib in siblings:
                sibling_name = sib['sibling_name']
                st.write(f"Menemukan saudara dari {parent}: {sibling_name}")
                # Cari anak-anak dari saudara kandung tersebut
                cousins = session.run("""
                    MATCH (sibling:Person {name: $sibling_name})-[:FATHER_OF|MOTHER_OF]->(cousin:Person)
                    RETURN cousin.name AS cousin_name
                """, sibling_name=sibling_name)

                for cousin in cousins:
                    cousin_name = cousin['cousin_name']
                    st.write(f"Menemukan sepupu: {cousin_name} dari orang tua {parent}")
                    # Buat hubungan sepupu antara semua anak dari parent dan anak dari saudara
                    for child in children:
                        if child != cousin_name:  # Hindari membuat sepupu diri sendiri
                            session.run("""
                                MATCH (child_p:Person {name: $child_p}), (child_s:Person {name: $child_s})
                                MERGE (child_p)-[:SEPAKU_OF]->(child_s)
                                MERGE (child_s)-[:SEPAKU_OF]->(child_p)
                                """, child_p=child, child_s=cousin_name)
                            st.success(f"Created SEPAKU_OF relationship between {child} and {cousin_name}")

        st.write("Finished updating all relationships.")

# Fungsi Streamlit GUI
def main():
    st.title("Sistem Silsilah Keluarga Interaktif")

    # Menambahkan Navigasi dengan Sidebar
    st.sidebar.title("Navigasi")
    page = st.sidebar.selectbox("Pilih Halaman:", ["Tambah Individu dan Relasi", "Cari Silsilah Keluarga", "Update Semua Relasi"])

    # Mendapatkan daftar semua individu
    all_individuals = get_all_individuals()

    if page == "Tambah Individu dan Relasi":
        st.header("Tambah Individu dan Relasi")

        # === Bagian 1: Input Individu Baru ===
        st.subheader("Input Individu Baru")
        new_person_name = st.text_input("Nama individu baru:", key="new_person")
        new_person_gender = st.selectbox("Jenis kelamin individu baru:", ("male", "female"), key="new_gender")

        if st.button("Tambah Individu"):
            if new_person_name:
                if new_person_name in all_individuals:
                    st.error(f"Individu dengan nama {new_person_name} sudah ada dalam sistem.")
                else:
                    # Tambahkan individu ke Neo4j
                    with driver.session() as session:
                        session.run("""
                            MERGE (p:Person {name: $person_name})
                            SET p.gender = $person_gender
                            """, person_name=new_person_name, person_gender=new_person_gender)
                    st.success(f"{new_person_name} ({new_person_gender}) telah ditambahkan ke dalam sistem.")
                    # Refresh the list of individuals after adding
                    all_individuals = get_all_individuals()
            else:
                st.error("Nama individu tidak boleh kosong.")

        st.markdown("---")

        # === Bagian 2: Tambah Relasi ===
        st.subheader("Tambahkan Relasi")
        if all_individuals:
            # Memilih individu utama untuk ditambahkan relasi
            selected_person = st.selectbox("Pilih individu untuk menambah relasi:", all_individuals, key="selected_person_relasi")
        else:
            st.info("Belum ada individu dalam sistem. Silakan tambahkan individu terlebih dahulu.")
            selected_person = None

        if selected_person:
            relation_type = st.selectbox("Pilih jenis relasi:", 
                                         ("Ayah", "Ibu", "Anak", "Suami", "Istri", "Saudara", "Mertua", "Sepupu"), 
                                         key="relation_type_relasi")

            # Input nama orang yang akan menjadi relasi
            relation_name = st.text_input(f"Nama {relation_type.lower()}:", key="relation_name_relasi")

            # Input jenis kelamin jika diperlukan
            relation_gender = st.selectbox(
                "Jenis kelamin:",
                ("male", "female"),
                key="relation_gender_relasi"
            ) if relation_type in ["Anak", "Suami", "Istri"] else None

            if st.button(f"Tambahkan {relation_type}"):
                if relation_name:
                    # Validasi untuk relasi tertentu yang harus unik (misalnya Ayah, Ibu, Suami, Istri)
                    if relation_type in ["Ayah", "Ibu", "Suami", "Istri"] and relation_name in all_individuals:
                        st.error(f"Individu dengan nama {relation_name} sudah ada dalam sistem. Silakan gunakan nama unik.")
                    else:
                        add_relation(
                            selected_person,
                            relation_type,
                            relation_name,
                            relation_gender if relation_type in ["Anak", "Suami", "Istri"] else None
                        )
                        st.success(
                            f"{relation_type} {relation_name} telah ditambahkan untuk {selected_person}."
                        )
                        # Refresh the list of individuals setelah menambah relasi
                        all_individuals = get_all_individuals()
                else:
                    st.error(f"Nama {relation_type.lower()} tidak boleh kosong.")

    elif page == "Cari Silsilah Keluarga":
        st.header("Cari dan Tampilkan Silsilah Keluarga")

        if all_individuals:
            # Membuat dropdown untuk memilih individu yang ada
            person_name = st.selectbox("Pilih nama individu yang ingin ditelusuri:", options=all_individuals, key="search_person_select_cari")

            # Opsi untuk memilih apa yang ingin ditampilkan
            display_option = st.selectbox(
                "Pilih apa yang ingin ditampilkan:",
                ("Relasi Keluarga", "Langkah-langkah Proses DFS", "Keduanya"),
                key="display_option_cari"
            )

            # Jika memilih "Relasi Keluarga" atau "Keduanya", tampilkan opsi relasi
            if display_option in ["Relasi Keluarga", "Keduanya"]:
                relation_options = st.multiselect(
                    "Pilih relasi yang ingin ditampilkan:",
                    ["Pasangan", "Leluhur", "Keturunan", "Saudara", "Paman/Bibi", "Sepupu", "Mertua"],
                    default=["Leluhur", "Keturunan"]
                )
                view_type = st.radio("Pilih tipe tampilan:", ("Teks", "Tabel"), key="view_type_cari")
            else:
                relation_options = []
                view_type = "Teks"  # Default

            if st.button("Tampilkan Silsilah dan Proses DFS"):
                if person_name in all_individuals:
                    results = {}
                    dfs_steps = []

                    # Menggunakan family_tree yang telah diambil
                    family_tree = get_family_tree()

                    # Mengumpulkan relasi yang dipilih
                    if "Pasangan" in relation_options:
                        spouse = family_tree[person_name].get('spouse')
                        if spouse:
                            results["Pasangan"] = [{"Relasi": "Pasangan", "Nama": f"{spouse} ({family_tree[spouse]['gender']})"}]
                        else:
                            results["Pasangan"] = [{"Relasi": "Pasangan", "Nama": "Tidak ada pasangan"}]
                    if "Leluhur" in relation_options:
                        ancestors = get_ancestors(family_tree, person_name, dfs_steps=dfs_steps if display_option in ["Langkah-langkah Proses DFS", "Keduanya"] else None)
                        if ancestors:
                            results["Leluhur"] = ancestors
                    if "Keturunan" in relation_options:
                        descendants = get_descendants(family_tree, person_name, dfs_steps=dfs_steps if display_option in ["Langkah-langkah Proses DFS", "Keduanya"] else None)
                        if descendants:
                            results["Keturunan"] = descendants
                    if "Saudara" in relation_options:
                        siblings = family_tree[person_name].get('siblings', [])
                        if siblings:
                            results["Saudara"] = [{"Relasi": "Saudara", "Nama": f"{sibling} ({family_tree[sibling]['gender']})"} for sibling in siblings]
                    if "Paman/Bibi" in relation_options:
                        uncles_aunts = family_tree[person_name].get('uncles_aunts', [])
                        if uncles_aunts:
                            results["Paman/Bibi"] = [{"Relasi": "Paman/Bibi", "Nama": f"{relative} ({family_tree[relative]['gender']})"} for relative in uncles_aunts]
                    if "Sepupu" in relation_options:
                        cousins = family_tree[person_name].get('cousins', [])
                        if cousins:
                            results["Sepupu"] = [{"Relasi": "Sepupu", "Nama": f"{cousin} ({family_tree[cousin]['gender']})"} for cousin in cousins]
                    if "Mertua" in relation_options:
                        mertua = []
                        spouse = family_tree[person_name].get('spouse')
                        if spouse:
                            with driver.session() as session:
                                # Cari orang tua dari pasangan
                                parent_results = session.run("""
                                    MATCH (parent:Person)-[r:FATHER_OF|MOTHER_OF]->(spouse:Person {name: $spouse_name})
                                    RETURN parent.name AS parent_name, parent.gender AS parent_gender, type(r) AS relation
                                """, spouse_name=spouse)
                                for pr in parent_results:
                                    mertua_name = pr['parent_name']
                                    mertua.append(mertua_name)
                        if mertua:
                            results["Mertua"] = [{"Relasi": "Mertua", "Nama": f"{m} ({family_tree[m]['gender']})"} for m in mertua]
                        else:
                            results["Mertua"] = [{"Relasi": "Mertua", "Nama": "Tidak ada mertua"}]

                    # Tampilkan relasi yang dipilih
                    if results:
                        for relation, data in results.items():
                            st.write(f"**{relation} dari {person_name}:**")
                            if view_type == "Tabel":
                                df = pd.DataFrame(data)
                                st.table(df)
                            else:
                                for item in data:
                                    st.write(f"{item['Relasi']}: {item['Nama']}")
                    else:
                        if display_option in ["Relasi Keluarga", "Keduanya"]:
                            st.write(f"Tidak ada data relasi yang dipilih untuk {person_name}.")

                    # Menampilkan langkah-langkah DFS jika dipilih
                    if display_option in ["Langkah-langkah Proses DFS", "Keduanya"]:
                        dfs_steps_output, found = find_person_dfs(family_tree, person_name)
                        if found:
                            st.success(f"Individu {person_name} ditemukan dalam silsilah.")
                        else:
                            st.error(f"Individu {person_name} tidak ditemukan dalam silsilah.")

                        if dfs_steps_output:
                            st.write("**Langkah-langkah Proses DFS:**")
                            dfs_steps_df = pd.DataFrame(dfs_steps_output)
                            st.table(dfs_steps_df)
                        else:
                            st.write("Tidak ada langkah DFS yang dapat ditampilkan.")
                else:
                    st.write(f"{person_name} tidak ditemukan dalam data silsilah.")
        else:
            st.info("Belum ada individu dalam sistem. Silakan tambahkan individu terlebih dahulu.")

    elif page == "Update Semua Relasi":
        st.header("Update Semua Relasi")
        st.write("Klik tombol di bawah untuk memperbarui semua hubungan berdasarkan data yang ada.")
        if st.button("Update Relasi Sekarang"):
            update_all_relations()
            st.success("Semua hubungan telah diperbarui.")

    # Sidebar Informasi Sistem
    st.sidebar.markdown("---")
    st.sidebar.write("**Informasi Sistem**")
    st.sidebar.write(f"**Total Individu:** {len(all_individuals)}")
    family_tree = get_family_tree()
    st.sidebar.write("**Struktur Keluarga Saat Ini:**")
    st.sidebar.json(family_tree)

if __name__ == "__main__":
    main()
