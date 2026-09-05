from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler

def get_feature_schema():
    # Defines the categorical and numerical features used across the pipeline
    categorical_features = ['customer_segment', 'payment_method', 'error_code']
    numerical_features = ['hist_payment_count', 'hist_success_rate', 'amount_relative', 'retry_count', 'hour', 'day_of_week']
    
    return categorical_features, numerical_features

def build_preprocessor():
    categorical_features, numerical_features = get_feature_schema()
    
    preprocessor = ColumnTransformer(
        transformers=[
            ('num', StandardScaler(), numerical_features),
            ('cat', OneHotEncoder(handle_unknown='ignore', sparse_output=False), categorical_features)
        ]
    )
    return preprocessor
