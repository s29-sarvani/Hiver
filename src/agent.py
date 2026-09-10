import os
import json
import chromadb
from sentence_transformers import SentenceTransformer
from openai import OpenAI

class RAGRetriever:
    def __init__(self, df, collection_name="spotify_support"):
        self.chroma_client = chromadb.Client()
        self.encoder = SentenceTransformer('all-MiniLM-L6-v2')
        self.collection = self.chroma_client.get_or_create_collection(name=collection_name)
        
        documents = df['customer_tweet'].astype(str).tolist()
        metadatas = [{'reply': str(r)} for r in df['brand_reply'].tolist()]
        ids = [str(i) for i in range(len(df))]
        
        embeddings = self.encoder.encode(documents).tolist()
        self.collection.add(embeddings=embeddings, documents=documents, metadatas=metadatas, ids=ids)
        
    def query(self, text, k=3):
        emb = self.encoder.encode([text]).tolist()
        results = self.collection.query(query_embeddings=emb, n_results=min(k, self.collection.count()))
        retrieved = []
        if results and results.get('metadatas'):
            for meta in results['metadatas'][0]:
                retrieved.append(meta['reply'])
        return retrieved

class SupportAgent:
    def __init__(self, retriever):
        self.retriever = retriever
        self.client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", "mock-key"))

    def run_trivial_baseline(self, text: str) -> dict:
        return {
            "intent": "GENERAL",
            "draft_reply": "Hi there! Please send us a Direct Message so we can look into this for you.",
            "routing_decision": "ESCALATE",
            "routing_reason": "Default trivial baseline rule."
        }

    def run_agent_pipeline(self, text: str) -> dict:
        historical_contexts = self.retriever.query(text, k=3)
        context_str = "\n".join([f"- {c}" for c in historical_contexts])
        
        if os.environ.get("OPENAI_API_KEY", "mock-key") == "mock-key":
            is_escalate = any(w in text.lower() for w in ['hack', 'refund', 'stolen', 'sue', 'money'])
            ref_reply = historical_contexts[0][:60] if historical_contexts else "our help center"
            return {
                "intent": "BILLING" if "charge" in text.lower() else "TECHNICAL",
                "draft_reply": f"Hi! Thanks for reaching out to @SpotifyCares. Check your settings or reference: {ref_reply}...",
                "routing_decision": "ESCALATE" if is_escalate else "AUTO_HANDLE",
                "routing_reason": "Detected high-risk policy trigger" if is_escalate else "Standard resolution workflow applied"
            }

        system_prompt = f"""You are the automated AI support agent for @SpotifyCares.
Analyze incoming customer tweets, classify intent, draft grounded responses, and decide routing.

HISTORICAL SPOTIFY RESOLUTION EXAMPLES:
{context_str}

RULES:
1. Intent categories: [BILLING, ACCOUNT, TECHNICAL, FEATURE_QUERY, GENERAL]
2. Auto-escalate if: User requests direct refunds, reports security/hacking, or uses abusive language.
3. Respond in JSON matching:
{{
  "intent": "<INTENT>",
  "draft_reply": "<REPLY>",
  "routing_decision": "AUTO_HANDLE" | "ESCALATE",
  "routing_reason": "<REASON>"
}}"""

        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text}
            ],
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)
