import os
import pandas as pd

def prepare_data(twcs_path="data/sample.csv", output_dir="data"):
    if not os.path.exists(twcs_path) and os.path.exists("data/twcs.csv"):
        twcs_path = "data/twcs.csv"
        
    os.makedirs(output_dir, exist_ok=True)
    print(f"Loading raw dataset from {twcs_path}...")
    
    if not os.path.exists(twcs_path):
        sample_data = {
            'tweet_id': [1, 2, 3, 4],
            'inbound': [True, False, True, False],
            'text': [
                '@SpotifyCares I got charged twice for my subscription this month',
                'Hi! Please send us a DM with your account email so we can investigate.',
                '@SpotifyCares my app keeps crashing on songs after update',
                'Sorry about that! Try reinstalling the app and let us know if it helps.'
            ],
            'in_response_to_tweet_id': [None, 1, None, 3],
            'tweet_id_customer': [1, None, 3, None],
            'tweet_id_brand': [None, 2, None, 4]
        }
        df = pd.DataFrame(sample_data)
    else:
        df = pd.read_csv(twcs_path)
    
    spotify_inbound = df[df['text'].str.contains('@SpotifyCares', case=False, na=False) & df['inbound']]
    df_responses = df[~df['inbound']].copy()
    
    merged = pd.merge(
        spotify_inbound, 
        df_responses, 
        left_on='tweet_id', 
        right_on='in_response_to_tweet_id', 
        suffixes=('_customer', '_brand')
    )
    
    clean_df = pd.DataFrame({
        'customer_tweet': merged['text_customer'].str.replace('@SpotifyCares', '', case=False).str.strip(),
        'brand_reply': merged['text_brand'].str.strip(),
        'customer_tweet_id': merged['tweet_id_customer'],
        'brand_tweet_id': merged['tweet_id_brand']
    }).drop_duplicates(subset=['customer_tweet']).dropna()

    clean_df.to_csv(f"{output_dir}/spotify_pairs.csv", index=False)
    print(f"Saved {len(clean_df)} paired @SpotifyCares conversations.")
    generate_golden_set(clean_df, output_dir)

def generate_golden_set(clean_df, output_dir):
    sample_size = min(150, len(clean_df))
    print(f"Generating {sample_size}-sample Golden Evaluation Set...")
    sample_df = clean_df.sample(n=sample_size, random_state=42, replace=True if len(clean_df)<sample_size else False).copy()
    
    intents, routings, reasons = [], [], []
    for idx, row in sample_df.iterrows():
        text = str(row['customer_tweet']).lower()
        if any(k in text for k in ['charge', 'refund', 'payment', 'subscription', 'bill', 'premium', 'money']):
            intent = 'BILLING'
            routing = 'AUTO_HANDLE' if 'refund' not in text else 'ESCALATE'
            reason = 'Standard billing query' if routing == 'AUTO_HANDLE' else 'Monetary refund requested'
        elif any(k in text for k in ['login', 'password', 'hacked', 'email', 'account']):
            intent = 'ACCOUNT'
            routing = 'ESCALATE' if 'hacked' in text else 'AUTO_HANDLE'
            reason = 'Account security concern' if routing == 'ESCALATE' else 'Standard account query'
        elif any(k in text for k in ['crash', 'error', 'bug', 'offline', 'download', 'stop', 'pause']):
            intent = 'TECHNICAL'
            routing = 'AUTO_HANDLE'
            reason = 'Known app troubleshooting step available'
        elif any(k in text for k in ['playlist', 'song', 'artist', 'lyrics']):
            intent = 'FEATURE_QUERY'
            routing = 'AUTO_HANDLE'
            reason = 'General feature usage request'
        else:
            intent = 'GENERAL'
            routing = 'ESCALATE' if len(text) < 15 else 'AUTO_HANDLE'
            reason = 'Ambiguous message length' if routing == 'ESCALATE' else 'General support inquiry'
            
        intents.append(intent)
        routings.append(routing)
        reasons.append(reason)
        
    sample_df['ground_truth_intent'] = intents
    sample_df['ground_truth_routing'] = routings
    sample_df['human_annotation_reason'] = reasons
    
    sample_df.to_csv(f"{output_dir}/golden_eval.csv", index=False)
    print(f"Saved Golden Evaluation Set to {output_dir}/golden_eval.csv")

if __name__ == "__main__":
    prepare_data()
