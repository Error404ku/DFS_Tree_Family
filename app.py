# app.py

import streamlit as st
import pandas as pd
from neo4j_operation import add_relation, get_family_tree, get_all_individuals, update_all_relations
from dfs import get_ancestors, get_descendants, find_person_dfs
from config import driver

def main():
    st.title("Sistem Silsilah Keluarga Interaktif")

    st.sidebar.title("Navigasi")
    page = st.sidebar.selectbox("Pilih Halaman:", ["Tambah Individu dan Relasi", "Cari Silsilah Keluarga", "Update Semua Relasi"])
    all_individuals = get_all_individuals()

    if page == "Tambah Individu dan Relasi":
        st.header("Tambah Individu dan Relasi")
        new_person_name = st.text_input("Nama individu baru:", key="new_person")
        new_person_gender = st.selectbox("Jenis kelamin individu baru:", ("male", "female"), key="new_gender")

        if st.button("Tambah Individu"):
            if new_person_name:
                if new_person_name in all_individuals:
                    st.error(f"Individu dengan nama {new_person_name} sudah ada dalam sistem.")
                else:
                    with driver.session() as session:
                        session.run("""
                            MERGE (p:Person {name: $person_name})
                            SET p.gender = $person_gender
                            """, person_name=new_person_name, person_gender=new_person_gender)
                    st.success(f"{new_person_name} ({new_person_gender}) telah ditambahkan ke dalam sistem.")
                    all_individuals = get_all_individuals()
            else:
                st.error("Nama individu tidak boleh kosong.")

        st.subheader("Tambahkan Relasi")
        if all_individuals:
            selected_person = st.selectbox("Pilih individu untuk menambah relasi:", all_individuals, key="selected_person_relasi")
        else:
            st.info("Belum ada individu dalam sistem.")
            selected_person = None

        if selected_person:
            relation_type = st.selectbox("Pilih jenis relasi:", 
                                         ("Ayah", "Ibu", "Anak", "Suami", "Istri", "Saudara", "Mertua", "Sepupu"), 
                                         key="relation_type_relasi")
            relation_name = st.text_input(f"Nama {relation_type.lower()}:", key="relation_name_relasi")
            relation_gender = st.selectbox("Jenis kelamin:", ("male", "female"), key="relation_gender_relasi") if relation_type in ["Anak", "Suami", "Istri"] else None

            if st.button(f"Tambahkan {relation_type}"):
                if relation_name:
                    if relation_type in ["Ayah", "Ibu", "Suami", "Istri"] and relation_name in all_individuals:
                        st.error(f"Individu dengan nama {relation_name} sudah ada dalam sistem.")
                    else:
                        add_relation(selected_person, relation_type, relation_name, relation_gender if relation_type in ["Anak", "Suami", "Istri"] else None)
                        st.success(f"{relation_type} {relation_name} telah ditambahkan untuk {selected_person}.")
                        all_individuals = get_all_individuals()
                else:
                    st.error(f"Nama {relation_type.lower()} tidak boleh kosong.")

    elif page == "Cari Silsilah Keluarga":
        st.header("Cari dan Tampilkan Silsilah Keluarga")
        if all_individuals:
            person_name = st.selectbox("Pilih nama individu:", options=all_individuals, key="search_person_select_cari")
            display_option = st.selectbox("Pilih apa yang ingin ditampilkan:", ("Relasi Keluarga", "Langkah-langkah Proses DFS", "Keduanya"), key="display_option_cari")
            relation_options = st.multiselect("Pilih relasi yang ingin ditampilkan:", ["Pasangan", "Leluhur", "Keturunan", "Saudara", "Paman/Bibi", "Sepupu", "Mertua"], default=["Leluhur", "Keturunan"])
            view_type = st.radio("Pilih tipe tampilan:", ("Teks", "Tabel"), key="view_type_cari")

            if st.button("Tampilkan Silsilah dan Proses DFS"):
                if person_name in all_individuals:
                    results = {}
                    dfs_steps = []
                    family_tree = get_family_tree()

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

                    for relation, data in results.items():
                        st.write(f"**{relation} dari {person_name}:**")
                        if view_type == "Tabel":
                            st.table(pd.DataFrame(data))
                        else:
                            for item in data:
                                st.write(f"{item['Relasi']}: {item['Nama']}")

    elif page == "Update Semua Relasi":
        st.header("Update Semua Relasi")
        if st.button("Update Relasi Sekarang"):
            update_all_relations()
            st.success("Semua hubungan telah diperbarui.")

if __name__ == "__main__":
    main()
