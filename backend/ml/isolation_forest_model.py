"""Isolation Forest model for unsupervised anomaly detection in transactions."""

from __future__ import annotations

import logging
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)


class IsolationForestAnomalyModel:
    """
    Unsupervised anomaly detection using Isolation Forest.
    
    Detects statistical outliers in transaction data without requiring pre-labeled examples.
    Features are engineered from transaction amount, account code, and categorical fields.
    """

    def __init__(self, contamination: float = 0.1):
        """
        Initialize the model.
        
        Args:
            contamination: Expected proportion of anomalies in data (0.0-1.0).
                          Default 0.1 means ~10% of transactions are expected to be anomalous.
        """
        self.contamination = contamination
        self.model = None
        self.scaler = None
        self.feature_names = None
        self.is_fitted = False

    def _engineer_features(self, df: pd.DataFrame) -> tuple[np.ndarray, list[str]]:
        """
        Extract and engineer features from raw transaction data.
        
        Features:
        - amount/log_amount: Transaction amount (normalized and log-scaled)
        - amount_zscore: Z-score of amount within account type
        - account_code_numeric: Numeric encoding of account code
        - num_decimals: Precision of amount (e.g., 1000.50 = 2 decimals)
        
        Args:
            df: DataFrame with columns: amount, account, and optional categories
            
        Returns:
            X: Feature matrix (n_samples, n_features)
            feature_names: List of feature names
        """
        features_list = []
        feature_names = []

        # Feature 1: Log-transformed amount (handles skewed distribution)
        amount = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)
        log_amount = np.log1p(np.abs(amount))  # log1p handles negative amounts
        features_list.append(log_amount.values)
        feature_names.append("log_amount")

        # Feature 2: Amount Z-score by account (local anomalies)
        account_group_zscore = amount.groupby(df["account"], observed=True).transform(
            lambda x: (x - x.mean()) / (x.std() + 1e-8)
        )
        features_list.append(account_group_zscore.fillna(0.0).values)
        feature_names.append("amount_zscore_by_account")

        # Feature 3: Numeric encoding of account code
        account_encoded = pd.factorize(df["account"])[0].astype(float)
        features_list.append(account_encoded)
        feature_names.append("account_numeric")

        # Feature 4: Decimal precision (suspicious if many decimals)
        def count_decimals(val):
            s = str(val)
            if "." in s:
                return len(s.split(".")[1])
            return 0

        decimals = amount.apply(count_decimals).astype(float)
        features_list.append(decimals.values)
        feature_names.append("amount_decimals")

        # Feature 5: Absolute difference from median (global outliers)
        median_amount = amount.median()
        features_list.append(np.abs(amount - median_amount).values)
        feature_names.append("abs_diff_from_median")

        # Combine features
        X = np.column_stack(features_list)
        return X, feature_names

    def fit(self, csv_path: str | Path) -> None:
        """
        Train the Isolation Forest model on transaction data.
        
        Args:
            csv_path: Path to CSV file with columns: amount, account, and optional label/category columns
        """
        csv_path = Path(csv_path)
        if not csv_path.exists():
            logger.warning(f"CSV path does not exist: {csv_path}")
            return

        df = pd.read_csv(csv_path)
        if df.empty:
            logger.warning(f"CSV is empty: {csv_path}")
            return

        # Require minimum columns
        required_cols = {"amount", "account"}
        if not required_cols.issubset(df.columns):
            # Try alternative column names
            if "DMBTR" in df.columns and "amount" not in df.columns:
                df["amount"] = df["DMBTR"]
            if "HKONT" in df.columns and "account" not in df.columns:
                df["account"] = df["HKONT"]

        if not required_cols.issubset(df.columns):
            raise ValueError(
                f"CSV must contain 'amount' and 'account' columns. Found: {df.columns.tolist()}"
            )

        # Engineer features
        X, self.feature_names = self._engineer_features(df)

        # Normalize features (important for Isolation Forest consistency)
        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X)

        # Train Isolation Forest
        self.model = IsolationForest(
            contamination=self.contamination,
            random_state=42,
            n_estimators=100,
        )
        self.model.fit(X_scaled)
        self.is_fitted = True
        logger.info(f"Trained Isolation Forest on {len(df)} transactions")

    def predict_anomaly_score(self, amount: float, account: str) -> float:
        """
        Score a single transaction for anomalies.
        
        Returns a normalized score from 0.0 (normal) to 1.0 (anomalous).
        
        Args:
            amount: Transaction amount
            account: Account code
            
        Returns:
            Anomaly score (0.0-1.0)
        """
        if not self.is_fitted:
            logger.warning("Model not fitted. Returning neutral score 0.5")
            return 0.5

        # Create a single-row DataFrame for feature engineering
        df_single = pd.DataFrame({
            "amount": [amount],
            "account": [account],
        })

        X, _ = self._engineer_features(df_single)
        X_scaled = self.scaler.transform(X)

        # Get anomaly score from Isolation Forest
        # predict() returns -1 (anomaly) or 1 (normal)
        # decision_function() returns raw anomaly score (negative = anomalous)
        raw_score = self.model.decision_function(X_scaled)[0]
        
        # Normalize to 0-1 range: more negative = higher anomaly score
        # Typically decision_function ranges from -1 to 1
        normalized_score = 1.0 - (raw_score + 1.0) / 2.0  # Maps [-1, 1] to [0, 1]
        return float(np.clip(normalized_score, 0.0, 1.0))

    def predict_batch(self, amounts: list[float], accounts: list[str]) -> list[float]:
        """
        Score multiple transactions efficiently.
        
        Args:
            amounts: List of transaction amounts
            accounts: List of account codes
            
        Returns:
            List of anomaly scores (0.0-1.0)
        """
        if not self.is_fitted:
            logger.warning("Model not fitted. Returning neutral scores")
            return [0.5] * len(amounts)

        df_batch = pd.DataFrame({
            "amount": amounts,
            "account": accounts,
        })

        X, _ = self._engineer_features(df_batch)
        X_scaled = self.scaler.transform(X)

        raw_scores = self.model.decision_function(X_scaled)
        normalized_scores = 1.0 - (raw_scores + 1.0) / 2.0
        return [float(np.clip(s, 0.0, 1.0)) for s in normalized_scores]

    def save(self, model_path: str | Path) -> None:
        """Save trained model and scaler to disk."""
        model_path = Path(model_path)
        model_path.parent.mkdir(parents=True, exist_ok=True)
        
        joblib.dump({
            "model": self.model,
            "scaler": self.scaler,
            "feature_names": self.feature_names,
            "contamination": self.contamination,
        }, model_path)
        logger.info(f"Saved model to {model_path}")

    @classmethod
    def load(cls, model_path: str | Path) -> IsolationForestAnomalyModel:
        """Load a previously trained model from disk."""
        model_path = Path(model_path)
        data = joblib.load(model_path)
        
        instance = cls(contamination=data["contamination"])
        instance.model = data["model"]
        instance.scaler = data["scaler"]
        instance.feature_names = data["feature_names"]
        instance.is_fitted = True
        logger.info(f"Loaded model from {model_path}")
        return instance
