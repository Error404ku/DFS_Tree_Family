# app.py

import streamlit as st
import pandas as pd
from neo4j_operation import add_relation, get_family_tree, get_all_individuals
from dfs import get_ancestors, get_descendants, find_person_dfs

# Inisialisasi sesi Streamlit untuk menyimpan data keluarga
if "family_tree" not in st.session_state:
    st.session_state.family_tree = {}
if "current_person" not in st.session_state:
    st.session_state.current_person = None

# Streamlit GUI
st.title("Sistem Silsilah Keluarga Interaktif")

# Input untuk memilih atau menambah individu baru
st.header("Input Individu")
new_person_name = st.text_input("Nama individu baru:", key="new_person")
new_person_gender = st.selectbox("Jenis kelamin individu baru:", ("male", "female"), key="new_gender")

if st.button("Tambah Individu"):
    if new_person_name:
        st.session_state.current_person = new_person_name
        # Tambahkan individu ke Neo4j
        with st.spinner("Menambahkan individu..."):
            add_relation(
                person=new_person_name,
                relation="Anak",  # Menggunakan "Anak" untuk inisialisasi
                name=new_person_name,
                gender=new_person_gender
            )
        st.success(f"{new_person_name} ({new_person_gender}) telah ditambahkan ke dalam sistem.")
    else:
        st.error("Nama individu tidak boleh kosong.")

# Tampilkan struktur keluarga jika ada individu yang dipilih
if st.session_state.get('current_person'):
    current_person = st.session_state.current_person
    # Mengambil data individu saat ini dari Neo4j
    family_tree = get_family_tree()
    current_person_data = family_tree.get(current_person, {})
    spouse = current_person_data.get("spouse", None)
    if spouse and spouse in family_tree:
        spouse_gender = family_tree[spouse]['gender']
        spouse_info = f"Pasangan: {spouse} ({spouse_gender})"
    else:
        spouse_info = "Tidak ada pasangan"
    
    st.write(f"Individu saat ini: **{current_person}** ({current_person_data.get('gender', 'unknown')})")
    st.write(spouse_info)
    st.json(current_person_data)
    
    # Opsi untuk menambah relasi
    st.subheader("Tambahkan Relasi")
    relation_type = st.selectbox("Pilih jenis relasi:", ("Ayah", "Ibu", "Anak", "Suami", "Istri"), key="relation_type")
    relation_name = st.text_input(f"Nama {relation_type.lower()}:", key="relation_name")
    relation_gender = st.selectbox(
        "Jenis kelamin:", ("male", "female"), key="relation_gender"
    ) if relation_type in ["Anak", "Suami", "Istri"] else None

    if st.button(f"Tambahkan {relation_type}"):
        if relation_name:
            add_relation(
                person=current_person,
                relation=relation_type,
                name=relation_name,
                gender=relation_gender if relation_type in ["Anak", "Suami", "Istri"] else None
            )
            st.success(
                f"{relation_type} {relation_name} telah ditambahkan untuk {current_person}."
            )
        else:
            st.error(f"Nama {relation_type.lower()} tidak boleh kosong.")

# Tampilkan struktur keluarga yang telah dimasukkan
st.header("Struktur Keluarga Saat Ini")
family_tree = get_family_tree()
st.session_state.family_tree = family_tree  # Update session state
st.json(family_tree)

# Menampilkan Daftar Semua Individu untuk Verifikasi
st.header("Daftar Semua Individu")
all_individuals = get_all_individuals()
st.write("**Individu yang ada dalam sistem:**")
st.write(", ".join(all_individuals))

# Opsi untuk beralih ke mode pencarian
st.header("Cari dan Tampilkan Silsilah")
if all_individuals:
    # Membuat dropdown untuk memilih individu yang ada
    person_name = st.selectbox("Pilih nama individu yang ingin ditelusuri:", options=all_individuals, key="search_person_select")

    # Opsi untuk memilih apa yang ingin ditampilkan
    display_option = st.selectbox(
        "Pilih apa yang ingin ditampilkan:",
        ("Relasi Keluarga", "Langkah-langkah Proses DFS", "Keduanya"),
        key="display_option"
    )

    # Jika memilih "Relasi Keluarga" atau "Keduanya", tampilkan opsi relasi
    if display_option in ["Relasi Keluarga", "Keduanya"]:
        relation_options = st.multiselect(
            "Pilih relasi yang ingin ditampilkan:",
            ["Leluhur", "Keturunan", "Saudara", "Paman/Bibi", "Sepupu", "Keponakan", "Cucu"],
            default=["Leluhur", "Keturunan"]
        )
        view_type = st.radio("Pilih tipe tampilan:", ("Teks", "Tabel"), key="view_type")
    else:
        relation_options = []
        view_type = "Teks"  # Default

    if st.button("Tampilkan Silsilah dan Proses DFS"):
        if person_name in all_individuals:
            results = {}
            dfs_steps = []

            # Mengumpulkan relasi yang dipilih
            if "Leluhur" in relation_options:
                ancestors = get_ancestors(family_tree, person_name, dfs_steps=dfs_steps if display_option in ["Langkah-langkah Proses DFS", "Keduanya"] else None)
                if ancestors:
                    results["Leluhur"] = ancestors
            if "Keturunan" in relation_options:
                descendants = get_descendants(family_tree, person_name, dfs_steps=dfs_steps if display_option in ["Langkah-langkah Proses DFS", "Keduanya"] else None)
                if descendants:
                    results["Keturunan"] = descendants
            # (Fungsi untuk saudara, paman/bibi, sepupu, keponakan, dan cucu tetap sama)

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
            if display_option in ["Langkah-langkah Proses DFS", "Keduanya", "Path"]:
                dfs_steps_output, found = find_person_dfs(family_tree, person_name)
                if found:
                    st.success(f"Individu {person_name} ditemukan dalam silsilah.")
                else:
                    st.error(f"Individu {person_name} tidak ditemukan dalam silsilah.")

                if dfs_steps_output:
                    st.write("**Langkah-langkah Proses DFS:**")
                    dfs_steps_df = pd.DataFrame(dfs_steps_output)
                    st.table(dfs_steps_df)

                    # Menampilkan Path secara terpisah jika dipilih
                    if display_option == "Langkah-langkah Proses DFS" or display_option == "Keduanya":
                        st.write("**Path dari DFS:**")
                        # Cari langkah terakhir saat ditemukan
                        if found:
                            path_steps = [step for step in dfs_steps_output if step['Action'] == 'Visit' and step['Person'] == person_name]
                            if path_steps:
                                # Ambil path terakhir yang ditemukan
                                last_step = path_steps[-1]
                                st.write(last_step['Path'])
                        else:
                            st.write("Tidak ada path yang ditemukan.")
                else:
                    st.write("Tidak ada langkah DFS yang dapat ditampilkan.")
        else:
            st.write(f"{person_name} tidak ditemukan dalam data silsilah.")

# Tutup driver Neo4j saat selesai
# driver.close()
