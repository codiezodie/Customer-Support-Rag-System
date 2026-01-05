"""
Customer Support RAG System - Working Without OpenAI
"""

import os
import json
from flask import Flask, request, jsonify
from flask_cors import CORS
from sentence_transformers import SentenceTransformer
import faiss
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Initialize embedding model
print("Loading embedding model...")
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
print("Model loaded!")

class RAGSystem:
    def __init__(self):
        self.index = None
        self.chunks = []
        self.dimension = 384
    
    def load_documents(self, kb_path):
        """Load all documents from knowledge base"""
        print(f"\nLoading documents from {kb_path}...")
        documents = []
        
        for root, dirs, files in os.walk(kb_path):
            for file in files:
                if file.endswith('.txt'):
                    filepath = os.path.join(root, file)
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    category = os.path.basename(os.path.dirname(filepath))
                    documents.append({
                        'filename': file,
                        'category': category,
                        'content': content
                    })
                    print(f"  ✓ Loaded: {category}/{file}")
        
        return documents
    
    def chunk_text(self, text, chunk_size=500):
        """Split text into simple chunks"""
        chunks = []
        words = text.split()
        
        for i in range(0, len(words), chunk_size // 10):
            chunk = ' '.join(words[i:i + chunk_size // 10])
            if len(chunk) > 50:
                chunks.append(chunk)
        
        return chunks
    
    def build_index(self, kb_path):
        """Build FAISS index from documents"""
        documents = self.load_documents(kb_path)
        
        if not documents:
            print("❌ No documents found!")
            return
        
        print("\nProcessing documents into chunks...")
        all_chunks = []
        
        for doc in documents:
            chunks = self.chunk_text(doc['content'])
            for i, chunk in enumerate(chunks):
                all_chunks.append({
                    'text': chunk,
                    'filename': doc['filename'],
                    'category': doc['category'],
                    'chunk_id': i
                })
        
        self.chunks = all_chunks
        print(f"  ✓ Created {len(all_chunks)} chunks")
        
        # Generate embeddings
        print("\nGenerating embeddings...")
        texts = [chunk['text'] for chunk in all_chunks]
        embeddings = embedding_model.encode(texts, show_progress_bar=True, batch_size=32)
        
        # Build FAISS index
        print("\nBuilding FAISS index...")
        self.index = faiss.IndexFlatL2(self.dimension)
        self.index.add(embeddings.astype('float32'))
        print(f"  ✓ Index built with {self.index.ntotal} vectors")
        
        # Save to disk
        self.save_index()
    
    def save_index(self):
        """Save index and chunks to disk"""
        faiss.write_index(self.index, 'faiss_index.bin')
        with open('chunks.json', 'w', encoding='utf-8') as f:
            json.dump(self.chunks, f, indent=2)
        print("  ✓ Index saved to disk")
    
    def load_index(self):
        """Load index and chunks from disk"""
        if os.path.exists('faiss_index.bin') and os.path.exists('chunks.json'):
            print("Loading existing index...")
            self.index = faiss.read_index('faiss_index.bin')
            with open('chunks.json', 'r', encoding='utf-8') as f:
                self.chunks = json.load(f)
            print(f"  ✓ Loaded {len(self.chunks)} chunks")
            return True
        return False
    
    def search(self, query, top_k=3):
        """Search for relevant chunks"""
        query_embedding = embedding_model.encode([query])
        distances, indices = self.index.search(query_embedding.astype('float32'), top_k)
        
        results = []
        for i, idx in enumerate(indices[0]):
            results.append({
                'chunk': self.chunks[idx],
                'score': float(distances[0][i])
            })
        
        return results
    
    def generate_answer(self, query, retrieved_chunks):
        """Generate answer from retrieved context (No OpenAI needed)"""
        
        # Build the answer from retrieved chunks
        answer_parts = ["Based on the knowledge base, here's what I found:\n"]
        
        for i, chunk_data in enumerate(retrieved_chunks, 1):
            chunk = chunk_data['chunk']
            answer_parts.append(f"\n📄 From {chunk['category']}/{chunk['filename']}:")
            answer_parts.append(f"{chunk['text'][:300]}...")
            answer_parts.append("")
        
        answer_parts.append(f"\n💡 Retrieved {len(retrieved_chunks)} relevant sections from the knowledge base.")
        
        return "\n".join(answer_parts)
    
    def query(self, question, top_k=3):
        """Complete RAG pipeline"""
        retrieved = self.search(question, top_k)
        answer = self.generate_answer(question, retrieved)
        
        return {
            'question': question,
            'answer': answer,
            'sources': [chunk['chunk'] for chunk in retrieved],
            'num_sources': len(retrieved)
        }

# Initialize RAG system
print("\n" + "="*60)
print("🤖 Initializing RAG System")
print("="*60)

rag = RAGSystem()

# Load or build index
if not rag.load_index():
    print("\nNo existing index found. Building new index...")
    rag.build_index('knowledge_base')
else:
    print("  ✓ Using cached index")

print("\n" + "="*60)
print("✅ RAG System Ready!")
print("="*60 + "\n")

# API Routes
@app.route('/')
def home():
    return jsonify({
        'message': 'Customer Support RAG System',
        'status': 'running'
    })

@app.route('/health')
def health():
    return jsonify({
        'status': 'healthy',
        'chunks': len(rag.chunks),
        'index_size': rag.index.ntotal if rag.index else 0
    })

@app.route('/query', methods=['POST'])
def query():
    data = request.json
    question = data.get('question', '')
    top_k = data.get('top_k', 3)
    
    if not question:
        return jsonify({'error': 'Question is required'}), 400
    
    try:
        result = rag.query(question, top_k)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/rebuild-index', methods=['POST'])
def rebuild_index():
    try:
        rag.build_index('knowledge_base')
        return jsonify({
            'status': 'success',
            'chunks': len(rag.chunks),
            'message': 'Index rebuilt successfully'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("\n🚀 Starting Flask server on http://localhost:5000")
    print("Press Ctrl+C to stop\n")
    app.run(debug=True, host='0.0.0.0', port=5000)