# config.py

from neo4j import GraphDatabase

# Detail koneksi Neo4j
NEO4J_URI = "bolt://localhost:7687"  # Ganti dengan URI Neo4j Anda
NEO4J_USER = "neo4j"                 # Ganti dengan username Neo4j Anda
NEO4J_PASSWORD = "password"          # Ganti dengan password Neo4j Anda

# Membuat instance driver Neo4j
driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
