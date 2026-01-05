import requests
import json

def test_query(question):
    print(f"\n{'='*60}")
    print(f"❓ Question: {question}")
    print('='*60)
    
    response = requests.post('http://localhost:5000/query', 
        json={'question': question}
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"\n✅ Answer:\n{result['answer']}")
        print(f"\n📊 Sources Used: {result['num_sources']}")
    else:
        print(f"❌ Error: {response.text}")

# Test multiple questions
questions = [
    "What is the refund policy?",
    "How do I upgrade my subscription?",
    "What storage plans are available?",
    "How to troubleshoot server crashes?"
]

print("🧪 Testing RAG System")
print("="*60)

for question in questions:
    test_query(question)
    input("\nPress Enter for next question...")