# config.py

import os
from neo4j import GraphDatabase  # Impor pustaka Neo4j untuk menghubungkan aplikasi dengan database Neo4j

# Ganti dengan kredensial Neo4j Anda
NEO4J_URI = "bolt://localhost:7687"  # URI default untuk koneksi ke Neo4j menggunakan protokol Bolt
NEO4J_USERNAME = "neo4j"             # Nama pengguna default Neo4j
NEO4J_PASSWORD = "kata_sandi_anda"   # Ganti dengan kata sandi Neo4j Anda

# Buat instance driver Neo4j
# Driver ini digunakan untuk menghubungkan dan berinteraksi dengan database Neo4j
driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))
