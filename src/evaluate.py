import pandas as pd
from sklearn.metrics import accuracy_score, recall_score

def evaluate_pipeline(agent, eval_df_path="data/golden_eval.csv"):
    df = pd.read_csv(eval_df_path)
    trivial_results, agent_results = [], []
    print(f"Running evaluation over {len(df)} golden evaluation samples...")
    
    for text in df['customer_tweet']:
        trivial_results.append(agent.run_trivial_baseline(str(text)))
        agent_results.append(agent.run_agent_pipeline(str(text)))
        
    df['pred_trivial_intent'] = [r['intent'] for r in trivial_results]
    df['pred_agent_intent'] = [r['intent'] for r in agent_results]
    df['pred_trivial_routing'] = [r['routing_decision'] for r in trivial_results]
    df['pred_agent_routing'] = [r['routing_decision'] for r in agent_results]
    
    print("\n" + "="*50)
    print("EVALUATION RESULTS")
    print("="*50)
    print(f"Trivial Baseline Accuracy: {accuracy_score(df['ground_truth_intent'], df['pred_trivial_intent']):.4f}")
    print(f"Agent Pipeline Accuracy:   {accuracy_score(df['ground_truth_intent'], df['pred_agent_intent']):.4f}")
    print("Agent Escalation Recall:   ", recall_score(df['ground_truth_routing'], df['pred_agent_routing'], pos_label='ESCALATE', zero_division=0))
    print("Agent Escalation Accuracy: ", accuracy_score(df['ground_truth_routing'], df['pred_agent_routing']))
    return df
