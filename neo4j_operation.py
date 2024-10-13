# neo4j_operation.py

from config import driver
import streamlit as st

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
            session.run("""
                MATCH (child:Person {name: $person_name}), (father:Person {name: $relation_name})
                MERGE (father)-[:FATHER_OF]->(child)
                SET father.gender = 'male'
                """, person_name=person, relation_name=name)

        elif relation == "Ibu":
            session.run("""
                MATCH (child:Person {name: $person_name}), (mother:Person {name: $relation_name})
                MERGE (mother)-[:MOTHER_OF]->(child)
                SET mother.gender = 'female'
                """, person_name=person, relation_name=name)

        elif relation == "Anak":
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
                st.error(f"Gender dari {person} tidak diketahui.")
                return

            session.run(f"""
                MATCH (parent:Person {{name: $person_name}}), (child:Person {{name: $relation_name}})
                MERGE (parent)-[:{parent_relation}]->(child)
                SET child.gender = $child_gender
                """, person_name=person, relation_name=name, child_gender=gender if gender else "unknown")

        elif relation == "Suami":
            session.run("""
                MATCH (wife:Person {name: $person_name}), (husband:Person {name: $relation_name})
                MERGE (husband)-[:MARRIED_TO]-(wife)
                SET husband.gender = 'male'
                """, person_name=person, relation_name=name)

        elif relation == "Istri":
            session.run("""
                MATCH (husband:Person {name: $person_name}), (wife:Person {name: $relation_name})
                MERGE (husband)-[:MARRIED_TO]-(wife)
                SET wife.gender = 'female'
                """, person_name=person, relation_name=name)

# Fungsi untuk mengambil struktur keluarga dari Neo4j
def get_family_tree():
    family_tree = {}
    with driver.session() as session:
        result = session.run("""
            MATCH (p:Person)
            RETURN p.name AS name, p.gender AS gender
        """)
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
                "cousins": [],
                "gender": gender
            }

        result = session.run("""
            MATCH (parent:Person)-[r:FATHER_OF|MOTHER_OF]->(child:Person)
            RETURN parent.name AS parent_name, child.name AS child_name, type(r) AS relation
        """)
        for record in result:
            parent_name = record['parent_name']
            child_name = record['child_name']
            if record['relation'] == 'FATHER_OF':
                family_tree[child_name]['father'] = parent_name
            elif record['relation'] == 'MOTHER_OF':
                family_tree[child_name]['mother'] = parent_name

        result = session.run("""
            MATCH (p1:Person)-[:MARRIED_TO]-(p2:Person)
            RETURN p1.name AS person1, p2.name AS person2
        """)
        for record in result:
            family_tree[record['person1']]['spouse'] = record['person2']
            family_tree[record['person2']]['spouse'] = record['person1']

    return family_tree

# Fungsi untuk mendapatkan semua individu
def get_all_individuals():
    with driver.session() as session:
        result = session.run("MATCH (p:Person) RETURN p.name AS name")
        return [record['name'] for record in result]

# Fungsi untuk memperbarui semua relasi
def update_all_relations():
    with driver.session() as session:
        session.run("""
            MATCH (p:Person)-[r:MERTUA_OF|MENANTU_OF]->(c:Person)
            DELETE r
        """)
