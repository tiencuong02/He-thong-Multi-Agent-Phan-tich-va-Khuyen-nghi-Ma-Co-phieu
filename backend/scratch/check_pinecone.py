
import os
from dotenv import load_dotenv
from pinecone import Pinecone

# Load environment variables
load_dotenv()

api_key = os.getenv("PINECONE_API_KEY")
index_name = os.getenv("PINECONE_INDEX_NAME")

print(f"Checking Pinecone index: {index_name}")

try:
    pc = Pinecone(api_key=api_key)
    
    # List indexes
    indexes = pc.list_indexes()
    index_names = [idx.name for idx in indexes]
    print(f"Available indexes: {index_names}")
    
    if index_name in index_names:
        print(f"SUCCESS: Index '{index_name}' found.")
        
        # Get index stats
        index = pc.Index(index_name)
        stats = index.describe_index_stats()
        print(f"Index stats: {stats}")
        
        # Check if there are vectors
        total_vector_count = stats.get('total_vector_count', 0)
        if total_vector_count > 0:
            print(f"Index has {total_vector_count} vectors.")
        else:
            print("WARNING: Index is empty.")
    else:
        print(f"ERROR: Index '{index_name}' not found in your Pinecone account.")

except Exception as e:
    print(f"ERROR: Failed to connect to Pinecone: {e}")
