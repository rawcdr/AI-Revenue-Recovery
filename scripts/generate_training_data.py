import os
import random
import pandas as pd
import numpy as np

def generate_synthetic_data(num_rows=20000, seed=42):
    random.seed(seed)
    np.random.seed(seed)
    
    # Feature distributions
    customer_segments = ['new', 'standard', 'high_value']
    payment_methods = ['card', 'upi', 'netbanking']
    error_codes = ['insufficient_funds', 'expired_card', 'customer_dispute', 'network_error', 'suspected_fraud']
    
    data = []
    
    for i in range(num_rows):
        customer_id = f"cus_{random.randint(1, 5000):04d}"
        segment = random.choice(customer_segments)
        method = random.choice(payment_methods)
        error_code = random.choice(error_codes)
        
        hist_count = random.randint(0, 50)
        hist_success = random.randint(0, hist_count)
        hist_success_rate = hist_success / hist_count if hist_count > 0 else 0.0
        avg_amount = random.uniform(100, 10000)
        amount = avg_amount * random.uniform(0.5, 2.0)
        amount_relative = amount / avg_amount if avg_amount > 0 else 1.0
        retry_count = random.randint(0, 4)
        hour = random.randint(0, 23)
        day_of_week = random.randint(0, 6)
        
        # Calculate probabilities deterministically for simulation
        # Base probabilities
        p_retry = 0.3
        p_update = 0.3
        
        # Adjust based on error_code
        if error_code == 'insufficient_funds':
            p_retry += 0.3
            p_update -= 0.1
        elif error_code == 'expired_card':
            p_retry -= 0.2
            p_update += 0.5
        elif error_code in ['customer_dispute', 'suspected_fraud']:
            p_retry -= 0.3
            p_update -= 0.3
        
        # Adjust based on customer history
        if hist_success_rate > 0.8:
            p_retry += 0.1
            p_update += 0.1
            
        # Adjust based on retry count (diminishing returns)
        p_retry -= (retry_count * 0.1)
        
        # Add noise
        p_retry = max(0.01, min(0.99, p_retry + np.random.normal(0, 0.1)))
        p_update = max(0.01, min(0.99, p_update + np.random.normal(0, 0.1)))
        
        # Sample outcomes
        retry_success = 1 if random.random() < p_retry else 0
        payment_update_success = 1 if random.random() < p_update else 0
        
        # Escalate logic (not a direct target, but we'll use retry and update to deduce it in inference, 
        # or we can just train models on the success of retry and update).
        
        data.append({
            'customer_id': customer_id,
            'customer_segment': segment,
            'payment_method': method,
            'error_code': error_code,
            'hist_payment_count': hist_count,
            'hist_success_rate': hist_success_rate,
            'amount': amount,
            'amount_relative': amount_relative,
            'retry_count': retry_count,
            'hour': hour,
            'day_of_week': day_of_week,
            'retry_success': retry_success,
            'payment_update_success': payment_update_success
        })
        
    df = pd.DataFrame(data)
    
    os.makedirs('data/training', exist_ok=True)
    df.to_csv('data/training/recovery_training_data.csv', index=False)
    print(f"Generated {num_rows} rows of training data at data/training/recovery_training_data.csv")

if __name__ == "__main__":
    generate_synthetic_data()
