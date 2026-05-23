"""
Earnings Call Sentiment Analyzer
Uses HuggingFace transformers to analyze earnings call transcripts
and predict post-earnings price moves.
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import re
import warnings
warnings.filterwarnings('ignore')

# Try importing transformers
try:
    from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
    import torch
    HAS_TRANSFORMERS = True
except ImportError:
    HAS_TRANSFORMERS = False

# Try importing yfinance for price data
try:
    import yfinance as yf
    HAS_YFINANCE = True
except ImportError:
    HAS_YFINANCE = False

from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, classification_report


class SentimentModel:
    """Wrapper for HuggingFace sentiment models."""

    def __init__(self, model_name: str = "ProsusAI/finbert"):
        """
        Initialize sentiment model.

        Recommended models for financial text:
        - ProsusAI/finbert (financial sentiment)
        - yiyanghkust/finbert-tone (earnings call tone)
        - mrm8488/distilroberta-finetuned-financial-news-sentiment-analysis
        """
        self.model_name = model_name
        self.pipeline = None
        self.tokenizer = None
        self.model = None

        if HAS_TRANSFORMERS:
            self._load_model()

    def _load_model(self):
        """Load the sentiment analysis pipeline."""
        try:
            self.pipeline = pipeline(
                "sentiment-analysis",
                model=self.model_name,
                tokenizer=self.model_name,
                truncation=True,
                max_length=512
            )
        except Exception as e:
            print(f"Error loading model {self.model_name}: {e}")
            # Fallback to basic sentiment
            self.pipeline = pipeline("sentiment-analysis", truncation=True, max_length=512)

    def analyze(self, text: str) -> Dict:
        """
        Analyze sentiment of text.

        Returns:
            Dict with label (positive/negative/neutral) and score
        """
        if not self.pipeline:
            return {"label": "neutral", "score": 0.5, "error": "Model not loaded"}

        try:
            # Split long text into chunks if necessary
            chunks = self._split_text(text, max_length=500)
            results = []

            for chunk in chunks:
                result = self.pipeline(chunk)[0]
                results.append(result)

            # Aggregate results
            return self._aggregate_results(results)

        except Exception as e:
            return {"label": "neutral", "score": 0.5, "error": str(e)}

    def _split_text(self, text: str, max_length: int = 500) -> List[str]:
        """Split text into chunks for processing."""
        words = text.split()
        chunks = []
        current_chunk = []
        current_length = 0

        for word in words:
            if current_length + len(word) + 1 <= max_length:
                current_chunk.append(word)
                current_length += len(word) + 1
            else:
                if current_chunk:
                    chunks.append(' '.join(current_chunk))
                current_chunk = [word]
                current_length = len(word)

        if current_chunk:
            chunks.append(' '.join(current_chunk))

        return chunks if chunks else [text[:max_length]]

    def _aggregate_results(self, results: List[Dict]) -> Dict:
        """Aggregate sentiment from multiple chunks."""
        if not results:
            return {"label": "neutral", "score": 0.5}

        # Count labels
        label_scores = {"positive": 0, "negative": 0, "neutral": 0}

        for r in results:
            label = r['label'].lower()
            score = r['score']

            if label in label_scores:
                label_scores[label] += score
            elif label in ['pos', 'positive']:
                label_scores['positive'] += score
            elif label in ['neg', 'negative']:
                label_scores['negative'] += score
            else:
                label_scores['neutral'] += score

        # Normalize
        total = sum(label_scores.values())
        if total > 0:
            for k in label_scores:
                label_scores[k] /= total

        # Determine overall sentiment
        best_label = max(label_scores, key=label_scores.get)
        best_score = label_scores[best_label]

        return {
            "label": best_label,
            "score": best_score,
            "breakdown": label_scores,
            "chunks_analyzed": len(results)
        }


class EarningsCallAnalyzer:
    """
    Analyze earnings call transcripts and correlate with price moves.
    """

    def __init__(self):
        self.sentiment_model = SentimentModel() if HAS_TRANSFORMERS else None
        self.earnings_data: Dict[str, List[Dict]] = {}

    def analyze_transcript(self, transcript: str, sections: bool = True) -> Dict:
        """
        Analyze an earnings call transcript.

        Args:
            transcript: Full text of earnings call
            sections: If True, analyze prepared remarks and Q&A separately
        """
        if not self.sentiment_model:
            return {"error": "Transformers not installed. Run: pip install transformers torch"}

        result = {
            "timestamp": datetime.now().isoformat(),
            "full_sentiment": self.sentiment_model.analyze(transcript),
            "word_count": len(transcript.split()),
        }

        if sections:
            # Try to split into sections
            sections_data = self._extract_sections(transcript)
            result["sections"] = {}

            for section_name, section_text in sections_data.items():
                if section_text:
                    result["sections"][section_name] = self.sentiment_model.analyze(section_text)

        # Extract key metrics mentions
        result["metrics_mentioned"] = self._extract_metrics(transcript)

        # Calculate composite score (-1 to 1)
        sentiment = result["full_sentiment"]
        if sentiment["label"] == "positive":
            result["composite_score"] = sentiment["score"]
        elif sentiment["label"] == "negative":
            result["composite_score"] = -sentiment["score"]
        else:
            result["composite_score"] = 0

        return result

    def _extract_sections(self, transcript: str) -> Dict[str, str]:
        """Extract prepared remarks and Q&A sections."""
        sections = {
            "prepared_remarks": "",
            "qa_session": "",
            "guidance": ""
        }

        text_lower = transcript.lower()

        # Common section markers
        qa_markers = ["question-and-answer", "q&a", "questions and answers", "operator:"]
        guidance_markers = ["outlook", "guidance", "going forward", "expect", "forecast"]

        # Find Q&A section
        qa_start = -1
        for marker in qa_markers:
            pos = text_lower.find(marker)
            if pos != -1 and (qa_start == -1 or pos < qa_start):
                qa_start = pos

        if qa_start > 0:
            sections["prepared_remarks"] = transcript[:qa_start]
            sections["qa_session"] = transcript[qa_start:]
        else:
            sections["prepared_remarks"] = transcript

        # Extract guidance mentions
        guidance_sentences = []
        sentences = transcript.split('.')
        for sentence in sentences:
            if any(marker in sentence.lower() for marker in guidance_markers):
                guidance_sentences.append(sentence.strip())
        sections["guidance"] = '. '.join(guidance_sentences[:10])  # Limit to first 10

        return sections

    def _extract_metrics(self, transcript: str) -> Dict:
        """Extract financial metrics mentioned in transcript."""
        metrics = {
            "revenue_mentions": 0,
            "earnings_mentions": 0,
            "margin_mentions": 0,
            "growth_mentions": 0,
            "guidance_mentions": 0,
            "beat_mentions": 0,
            "miss_mentions": 0
        }

        text_lower = transcript.lower()

        metrics["revenue_mentions"] = text_lower.count("revenue") + text_lower.count("sales")
        metrics["earnings_mentions"] = text_lower.count("earnings") + text_lower.count("eps") + text_lower.count("profit")
        metrics["margin_mentions"] = text_lower.count("margin")
        metrics["growth_mentions"] = text_lower.count("growth") + text_lower.count("grew") + text_lower.count("increase")
        metrics["guidance_mentions"] = text_lower.count("guidance") + text_lower.count("outlook") + text_lower.count("expect")
        metrics["beat_mentions"] = text_lower.count("beat") + text_lower.count("exceeded") + text_lower.count("above")
        metrics["miss_mentions"] = text_lower.count("miss") + text_lower.count("below") + text_lower.count("shortfall")

        return metrics


class EarningsEventStudy:
    """
    Event study to test if sentiment predicts post-earnings price moves.
    """

    def __init__(self):
        self.analyzer = EarningsCallAnalyzer()
        self.results: List[Dict] = []

    def analyze_earnings_event(
        self,
        symbol: str,
        transcript: str,
        earnings_date: datetime,
        window_days: int = 5
    ) -> Dict:
        """
        Analyze a single earnings event.

        Args:
            symbol: Stock ticker
            transcript: Earnings call transcript
            earnings_date: Date of earnings announcement
            window_days: Days to track price after earnings
        """
        if not HAS_YFINANCE:
            return {"error": "yfinance not installed"}

        # Analyze sentiment
        sentiment = self.analyzer.analyze_transcript(transcript)

        # Get price data around earnings
        start_date = earnings_date - timedelta(days=5)
        end_date = earnings_date + timedelta(days=window_days + 5)

        ticker = yf.Ticker(symbol)
        df = ticker.history(start=start_date, end=end_date)

        if len(df) == 0:
            return {"error": f"No price data for {symbol}"}

        # Calculate returns
        pre_earnings_close = df.loc[:earnings_date]['Close'].iloc[-1] if len(df.loc[:earnings_date]) > 0 else None

        # Post-earnings returns at various horizons
        returns = {}
        for days in [1, 2, 3, 5]:
            target_date = earnings_date + timedelta(days=days)
            post_df = df.loc[target_date:]
            if len(post_df) > 0:
                post_close = post_df['Close'].iloc[0]
                if pre_earnings_close:
                    returns[f"return_{days}d"] = (post_close / pre_earnings_close - 1) * 100
            else:
                returns[f"return_{days}d"] = None

        # Classify actual outcome
        actual_direction = "positive" if returns.get("return_1d", 0) and returns["return_1d"] > 0 else "negative"

        # Compare prediction vs actual
        predicted_direction = sentiment["full_sentiment"]["label"]
        is_correct = (
            (predicted_direction == "positive" and actual_direction == "positive") or
            (predicted_direction == "negative" and actual_direction == "negative")
        )

        result = {
            "symbol": symbol,
            "earnings_date": earnings_date.isoformat(),
            "sentiment": sentiment,
            "returns": returns,
            "predicted_direction": predicted_direction,
            "actual_direction": actual_direction,
            "prediction_correct": is_correct,
            "confidence": sentiment["full_sentiment"]["score"]
        }

        self.results.append(result)
        return result

    def backtest_strategy(self, events: List[Dict]) -> Dict:
        """
        Backtest a trading strategy based on sentiment predictions.

        Strategy:
        - Go long if sentiment is positive
        - Go short if sentiment is negative
        - Hold for N days after earnings
        """
        if not events:
            return {"error": "No events to backtest"}

        predictions = []
        actuals = []
        returns_1d = []
        strategy_returns = []

        for event in events:
            if event.get("sentiment") and event.get("returns"):
                pred = 1 if event["predicted_direction"] == "positive" else 0
                actual = 1 if event["actual_direction"] == "positive" else 0
                ret_1d = event["returns"].get("return_1d", 0) or 0

                predictions.append(pred)
                actuals.append(actual)
                returns_1d.append(ret_1d)

                # Strategy return: long if positive sentiment, short if negative
                position = 1 if pred == 1 else -1
                strategy_returns.append(position * ret_1d)

        if not predictions:
            return {"error": "No valid predictions"}

        predictions = np.array(predictions)
        actuals = np.array(actuals)
        returns_1d = np.array(returns_1d)
        strategy_returns = np.array(strategy_returns)

        # Classification metrics
        accuracy = accuracy_score(actuals, predictions)
        precision = precision_score(actuals, predictions, zero_division=0)
        recall = recall_score(actuals, predictions, zero_division=0)
        f1 = f1_score(actuals, predictions, zero_division=0)

        # Strategy metrics
        total_return = np.sum(strategy_returns)
        mean_return = np.mean(strategy_returns)
        win_rate = np.mean(strategy_returns > 0) * 100
        sharpe = np.mean(strategy_returns) / np.std(strategy_returns) if np.std(strategy_returns) > 0 else 0

        # Buy and hold comparison
        buy_hold_return = np.sum(returns_1d)

        return {
            "n_events": len(events),
            "classification_metrics": {
                "accuracy": float(accuracy),
                "precision": float(precision),
                "recall": float(recall),
                "f1_score": float(f1)
            },
            "strategy_metrics": {
                "total_return_pct": float(total_return),
                "mean_return_pct": float(mean_return),
                "win_rate_pct": float(win_rate),
                "sharpe_ratio": float(sharpe),
                "buy_hold_return_pct": float(buy_hold_return),
                "alpha": float(total_return - buy_hold_return)
            },
            "confusion_matrix": {
                "true_positive": int(np.sum((predictions == 1) & (actuals == 1))),
                "true_negative": int(np.sum((predictions == 0) & (actuals == 0))),
                "false_positive": int(np.sum((predictions == 1) & (actuals == 0))),
                "false_negative": int(np.sum((predictions == 0) & (actuals == 1)))
            }
        }


class SentimentTradingSignal:
    """
    Generate trading signals from news/earnings sentiment.
    Integrates with the existing agent system.
    """

    def __init__(self):
        self.analyzer = EarningsCallAnalyzer()
        self.sentiment_cache: Dict[str, Dict] = {}

    def analyze_news(self, symbol: str, news_items: List[str]) -> Dict:
        """
        Analyze multiple news items for a symbol.
        """
        if not news_items:
            return {"error": "No news items provided"}

        sentiments = []
        for news in news_items[:10]:  # Limit to 10 items
            sentiment = self.analyzer.sentiment_model.analyze(news)
            sentiments.append(sentiment)

        # Aggregate sentiments
        positive_count = sum(1 for s in sentiments if s["label"] == "positive")
        negative_count = sum(1 for s in sentiments if s["label"] == "negative")
        neutral_count = sum(1 for s in sentiments if s["label"] == "neutral")

        avg_score = np.mean([s["score"] for s in sentiments])

        # Determine overall signal
        if positive_count > negative_count and positive_count > neutral_count:
            signal = "BUY"
            confidence = avg_score * (positive_count / len(sentiments))
        elif negative_count > positive_count and negative_count > neutral_count:
            signal = "SELL"
            confidence = avg_score * (negative_count / len(sentiments))
        else:
            signal = "HOLD"
            confidence = 0.5

        result = {
            "symbol": symbol,
            "signal": signal,
            "confidence": float(confidence),
            "sentiment_breakdown": {
                "positive": positive_count,
                "negative": negative_count,
                "neutral": neutral_count
            },
            "items_analyzed": len(sentiments),
            "timestamp": datetime.now().isoformat()
        }

        self.sentiment_cache[symbol] = result
        return result

    def get_signal(self, symbol: str) -> Optional[Dict]:
        """Get cached signal for a symbol."""
        return self.sentiment_cache.get(symbol)


# Global instances
sentiment_model = SentimentModel() if HAS_TRANSFORMERS else None
earnings_analyzer = EarningsCallAnalyzer()
event_study = EarningsEventStudy()
sentiment_signal = SentimentTradingSignal()
