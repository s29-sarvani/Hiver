import os
import pandas as pd
from src.dataset_prep import prepare_data
from src.agent import RAGRetriever, SupportAgent
from src.evaluate import evaluate_pipeline

def main():
    if not os.path.exists("data/golden_eval.csv"):
        prepare_data()

    spotify_pairs = pd.read_csv("data/spotify_pairs.csv")
    print("Initializing Vector Store Retriever...")
    retriever = RAGRetriever(spotify_pairs.head(1000))
    agent = SupportAgent(retriever)
    
    print("Executing Evaluation Harness...")
    evaluate_pipeline(agent)

if __name__ == "__main__":
    main()
