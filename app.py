# app.py

import streamlit as st
import pandas as pd
from neo4j_operation import add_relation, get_family_tree, get_all_individuals, update_all_relations
from dfs import get_ancestors, get_descendants, find_person_dfs
from config import driver

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
