# neo4j_operation.py

import streamlit as st
from config import driver

# Fungsi untuk menambahkan relasi ke Neo4j
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
        
        # Tambahkan relasi
        if relation == "Ayah":
            session.run("""
                MATCH (child:Person {name: $person_name}), (parent:Person {name: $relation_name})
                MERGE (parent)-[:FATHER_OF]->(child)
                SET parent.gender = 'male'
                """, person_name=person, relation_name=name)
        elif relation == "Ibu":
            session.run("""
                MATCH (child:Person {name: $person_name}), (parent:Person {name: $relation_name})
                MERGE (parent)-[:MOTHER_OF]->(child)
                SET parent.gender = 'female'
                """, person_name=person, relation_name=name)
        elif relation == "Anak":
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
                """, person_name=person, relation_name=name, child_gender=gender)
        elif relation in ["Suami", "Istri"]:
            if relation == "Suami":
                # `person` adalah istri, `name` adalah suami
                session.run("""
                    MATCH (wife:Person {name: $person_name}), (husband:Person {name: $relation_name})
                    MERGE (wife)-[:MARRIED_TO]-(husband)
                    SET wife.gender = 'female', husband.gender = 'male'
                    """, person_name=person, relation_name=name)
            else:  # relation == "Istri"
                # `person` adalah suami, `name` adalah istri
                session.run("""
                    MATCH (husband:Person {name: $person_name}), (wife:Person {name: $relation_name})
                    MERGE (husband)-[:MARRIED_TO]-(wife)
                    SET husband.gender = 'male', wife.gender = 'female'
                    """, person_name=person, relation_name=name)

# Fungsi untuk mengambil struktur keluarga dari Neo4j
def get_family_tree():
    family_tree = {}
    with driver.session() as session:
        # Mengambil data individu
        result = session.run("""
            MATCH (p:Person)
            OPTIONAL MATCH (p)-[:FATHER_OF|MOTHER_OF]->(child)
            OPTIONAL MATCH (p)-[:MARRIED_TO]-(spouse)
            RETURN p.name AS name, p.gender AS gender, collect(DISTINCT child.name) AS children, collect(DISTINCT spouse.name) AS spouse_names
            """)
        for record in result:
            name = record['name']
            gender = record['gender']
            children = record['children']
            spouse_names = record['spouse_names']
            family_tree[name] = {
                "father": None,
                "mother": None,
                "children": children,
                "spouse": spouse_names[0] if spouse_names else None,
                "gender": gender
            }
        # Mengambil relasi orang tua
        result = session.run("""
            MATCH (parent)-[r:FATHER_OF|MOTHER_OF]->(child)
            RETURN parent.name AS parent_name, child.name AS child_name, type(r) AS relation
            """)
        for record in result:
            parent_name = record['parent_name']
            child_name = record['child_name']
            relation = record['relation']
            if relation == 'FATHER_OF':
                family_tree[child_name]['father'] = parent_name
            elif relation == 'MOTHER_OF':
                family_tree[child_name]['mother'] = parent_name
    return family_tree

# Fungsi untuk mendapatkan semua individu
def get_all_individuals():
    with driver.session() as session:
        result = session.run("MATCH (p:Person) RETURN p.name AS name")
        return [record['name'] for record in result]
