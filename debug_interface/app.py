import os
import json
import streamlit as st
import faiss
import numpy as np

def display_vector_stores(data_folder="data"):
    st.header("Vector Stores")
    for root, dirs, files in os.walk(data_folder):
        for file in files:
            if file.endswith(".faiss"):
                file_path = os.path.join(root, file)
                st.subheader(f"Vector Store: `{file_path}`")
                try:
                    index = faiss.read_index(file_path)
                    st.write(f"Number of vectors: {index.ntotal}")
                    st.write(f"Vector dimension: {index.d}")
                except Exception as e:
                    st.error(f"Error loading FAISS index: {e}")

def display_doc_stores(data_folder="data"):
    st.header("Document Stores")
    for root, dirs, files in os.walk(data_folder):
        for file in files:
            if file.endswith(".json"):
                file_path = os.path.join(root, file)
                st.subheader(f"Document Store: `{file_path}`")
                try:
  
                    with open(file_path, "r") as f:
                        data = json.load(f)
                    st.json(data)
                except Exception as e:
                    st.error(f"Error loading document store: {e}")

def main():
    st.title("Debug Interface")
    
    # Add a text input for the data folder path
    data_folder = st.text_input("Enter the path to the data folder:", "data")
    
    if os.path.exists(data_folder):
        display_vector_stores(data_folder)
        display_doc_stores(data_folder)
    else:
        st.error("The specified data folder does not exist.")

if __name__ == "__main__":
    main()