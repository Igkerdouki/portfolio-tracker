"""
Stock Analyzer - Evaluates stocks using fundamental and technical metrics
Based on metrics used by investment gurus (Buffett, Lynch, Graham)
"""

import yfinance as yf
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import json
import os

ANALYSIS_FILE = os.path.join(os.path.dirname(__file__), '..', '..', 'analysis_history.json')
REPORT_FILE = os.path.join(os.path.dirname(__file__), '..', '..', 'STOCK_ANALYSIS.md')


class StockAnalyzer:
    """Analyzes stocks using fundamental and technical metrics."""

    # Scoring weights - these get adjusted based on prediction accuracy
    DEFAULT_WEIGHTS = {
        "pe_ratio": 0.10,
        "peg_ratio": 0.12,
        "price_to_book": 0.08,
        "debt_to_equity": 0.10,
        "roe": 0.12,
        "revenue_growth": 0.10,
        "eps_growth": 0.10,
        "dividend_yield": 0.05,
        "price_vs_52w": 0.08,
        "moving_avg_signal": 0.10,
        "analyst_rating": 0.05,
    }

    def __init__(self):
        self.weights = self._load_weights()
        self.history = self._load_history()

    def _load_weights(self) -> Dict[str, float]:
        """Load weights from history or use defaults."""
        if os.path.exists(ANALYSIS_FILE):
            try:
                with open(ANALYSIS_FILE, 'r') as f:
                    data = json.load(f)
                    return data.get('weights', self.DEFAULT_WEIGHTS.copy())
            except:
                pass
        return self.DEFAULT_WEIGHTS.copy()

    def _load_history(self) -> Dict:
        """Load analysis history."""
        if os.path.exists(ANALYSIS_FILE):
            try:
                with open(ANALYSIS_FILE, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {'weights': self.DEFAULT_WEIGHTS.copy(), 'analyses': [], 'predictions': []}

    def _save_history(self):
        """Save analysis history."""
        self.history['weights'] = self.weights
        with open(ANALYSIS_FILE, 'w') as f:
            json.dump(self.history, f, indent=2, default=str)

    def analyze_stock(self, symbol: str) -> Dict:
        """Perform comprehensive stock analysis."""
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            hist = ticker.history(period="1y")

            if hist.empty:
                return {"error": f"No data available for {symbol}"}

            # Gather metrics
            metrics = self._extract_metrics(info, hist)
            scores = self._calculate_scores(metrics)

            # Calculate overall score (0-100)
            overall_score = sum(
                scores.get(metric, 0) * weight
                for metric, weight in self.weights.items()
            )

            # Generate recommendation
            recommendation = self._generate_recommendation(overall_score, metrics, scores)

            # Create analysis result
            analysis = {
                "symbol": symbol.upper(),
                "timestamp": datetime.now().isoformat(),
                "price": info.get("regularMarketPrice") or info.get("currentPrice"),
                "metrics": metrics,
                "scores": scores,
                "overall_score": round(overall_score, 2),
                "recommendation": recommendation,
                "key_strengths": self._identify_strengths(scores),
                "key_concerns": self._identify_concerns(scores),
            }

            # Store in history
            self.history['analyses'].append({
                "symbol": symbol.upper(),
                "timestamp": analysis['timestamp'],
                "price": analysis['price'],
                "overall_score": analysis['overall_score'],
                "recommendation": recommendation['action']
            })

            # Keep only last 100 analyses
            self.history['analyses'] = self.history['analyses'][-100:]
            self._save_history()

            return analysis

        except Exception as e:
            return {"error": str(e), "symbol": symbol}

    def _extract_metrics(self, info: Dict, hist) -> Dict:
        """Extract all relevant metrics from stock data."""
        current_price = info.get("regularMarketPrice") or info.get("currentPrice") or 0

        # Calculate 50-day and 200-day moving averages
        ma_50 = hist['Close'].tail(50).mean() if len(hist) >= 50 else None
        ma_200 = hist['Close'].tail(200).mean() if len(hist) >= 200 else None

        # 52-week high/low
        week_52_high = info.get("fiftyTwoWeekHigh", 0)
        week_52_low = info.get("fiftyTwoWeekLow", 0)

        # Price position in 52-week range (0-100%)
        price_position = 0
        if week_52_high and week_52_low and week_52_high != week_52_low:
            price_position = ((current_price - week_52_low) / (week_52_high - week_52_low)) * 100

        return {
            "current_price": current_price,
            "pe_ratio": info.get("trailingPE"),
            "forward_pe": info.get("forwardPE"),
            "peg_ratio": info.get("pegRatio"),
            "price_to_book": info.get("priceToBook"),
            "price_to_sales": info.get("priceToSalesTrailing12Months"),
            "debt_to_equity": info.get("debtToEquity"),
            "current_ratio": info.get("currentRatio"),
            "quick_ratio": info.get("quickRatio"),
            "roe": info.get("returnOnEquity"),
            "roa": info.get("returnOnAssets"),
            "profit_margin": info.get("profitMargins"),
            "operating_margin": info.get("operatingMargins"),
            "revenue_growth": info.get("revenueGrowth"),
            "earnings_growth": info.get("earningsGrowth"),
            "eps_trailing": info.get("trailingEps"),
            "eps_forward": info.get("forwardEps"),
            "dividend_yield": info.get("dividendYield"),
            "payout_ratio": info.get("payoutRatio"),
            "beta": info.get("beta"),
            "market_cap": info.get("marketCap"),
            "enterprise_value": info.get("enterpriseValue"),
            "week_52_high": week_52_high,
            "week_52_low": week_52_low,
            "price_vs_52w_high": round((current_price / week_52_high * 100), 2) if week_52_high else None,
            "price_position_52w": round(price_position, 2),
            "ma_50": round(ma_50, 2) if ma_50 else None,
            "ma_200": round(ma_200, 2) if ma_200 else None,
            "above_ma_50": current_price > ma_50 if ma_50 else None,
            "above_ma_200": current_price > ma_200 if ma_200 else None,
            "golden_cross": ma_50 > ma_200 if (ma_50 and ma_200) else None,
            "analyst_target": info.get("targetMeanPrice"),
            "analyst_recommendation": info.get("recommendationKey"),
            "num_analysts": info.get("numberOfAnalystOpinions"),
            "sector": info.get("sector"),
            "industry": info.get("industry"),
        }

    def _calculate_scores(self, metrics: Dict) -> Dict[str, float]:
        """Calculate individual metric scores (0-100)."""
        scores = {}

        # P/E Ratio (lower is better, but not too low)
        pe = metrics.get("pe_ratio")
        if pe:
            if pe < 0:
                scores["pe_ratio"] = 20  # Negative earnings
            elif pe < 10:
                scores["pe_ratio"] = 70  # Very cheap, maybe value trap
            elif pe < 15:
                scores["pe_ratio"] = 100  # Excellent (Graham territory)
            elif pe < 20:
                scores["pe_ratio"] = 85  # Good
            elif pe < 25:
                scores["pe_ratio"] = 70  # Fair
            elif pe < 35:
                scores["pe_ratio"] = 50  # Expensive
            else:
                scores["pe_ratio"] = 30  # Very expensive
        else:
            scores["pe_ratio"] = 50  # Neutral if no data

        # PEG Ratio (< 1 is undervalued, per Peter Lynch)
        peg = metrics.get("peg_ratio")
        if peg:
            if peg < 0:
                scores["peg_ratio"] = 20
            elif peg < 0.5:
                scores["peg_ratio"] = 100  # Very undervalued
            elif peg < 1:
                scores["peg_ratio"] = 90  # Undervalued
            elif peg < 1.5:
                scores["peg_ratio"] = 70  # Fair
            elif peg < 2:
                scores["peg_ratio"] = 50
            else:
                scores["peg_ratio"] = 30  # Overvalued
        else:
            scores["peg_ratio"] = 50

        # Price to Book (< 1.5 per Graham, < 3 acceptable)
        pb = metrics.get("price_to_book")
        if pb:
            if pb < 0:
                scores["price_to_book"] = 20
            elif pb < 1:
                scores["price_to_book"] = 100  # Below book value
            elif pb < 1.5:
                scores["price_to_book"] = 90  # Graham territory
            elif pb < 3:
                scores["price_to_book"] = 70
            elif pb < 5:
                scores["price_to_book"] = 50
            else:
                scores["price_to_book"] = 30
        else:
            scores["price_to_book"] = 50

        # Debt to Equity (lower is better, < 50% preferred)
        de = metrics.get("debt_to_equity")
        if de is not None:
            if de < 0:
                scores["debt_to_equity"] = 50
            elif de < 30:
                scores["debt_to_equity"] = 100  # Very low debt
            elif de < 50:
                scores["debt_to_equity"] = 85
            elif de < 100:
                scores["debt_to_equity"] = 70
            elif de < 150:
                scores["debt_to_equity"] = 50
            else:
                scores["debt_to_equity"] = 30  # High debt risk
        else:
            scores["debt_to_equity"] = 50

        # Return on Equity (higher is better, > 15% good)
        roe = metrics.get("roe")
        if roe is not None:
            roe_pct = roe * 100 if roe < 1 else roe
            if roe_pct < 0:
                scores["roe"] = 20
            elif roe_pct < 10:
                scores["roe"] = 50
            elif roe_pct < 15:
                scores["roe"] = 70
            elif roe_pct < 20:
                scores["roe"] = 85
            elif roe_pct < 30:
                scores["roe"] = 100  # Excellent
            else:
                scores["roe"] = 90  # Very high, check sustainability
        else:
            scores["roe"] = 50

        # Revenue Growth (positive and growing)
        rev_growth = metrics.get("revenue_growth")
        if rev_growth is not None:
            growth_pct = rev_growth * 100 if abs(rev_growth) < 1 else rev_growth
            if growth_pct < -10:
                scores["revenue_growth"] = 20
            elif growth_pct < 0:
                scores["revenue_growth"] = 40
            elif growth_pct < 5:
                scores["revenue_growth"] = 60
            elif growth_pct < 10:
                scores["revenue_growth"] = 75
            elif growth_pct < 20:
                scores["revenue_growth"] = 90
            else:
                scores["revenue_growth"] = 100
        else:
            scores["revenue_growth"] = 50

        # EPS Growth
        eps_growth = metrics.get("earnings_growth")
        if eps_growth is not None:
            growth_pct = eps_growth * 100 if abs(eps_growth) < 1 else eps_growth
            if growth_pct < -20:
                scores["eps_growth"] = 20
            elif growth_pct < 0:
                scores["eps_growth"] = 40
            elif growth_pct < 10:
                scores["eps_growth"] = 65
            elif growth_pct < 20:
                scores["eps_growth"] = 80
            elif growth_pct < 30:
                scores["eps_growth"] = 95
            else:
                scores["eps_growth"] = 100
        else:
            scores["eps_growth"] = 50

        # Dividend Yield (bonus for income)
        div_yield = metrics.get("dividend_yield")
        if div_yield is not None:
            yield_pct = div_yield * 100 if div_yield < 1 else div_yield
            if yield_pct <= 0:
                scores["dividend_yield"] = 50  # No dividend, neutral
            elif yield_pct < 2:
                scores["dividend_yield"] = 60
            elif yield_pct < 4:
                scores["dividend_yield"] = 80
            elif yield_pct < 6:
                scores["dividend_yield"] = 90
            else:
                scores["dividend_yield"] = 70  # Very high might be unsustainable
        else:
            scores["dividend_yield"] = 50

        # Price vs 52-week range (middle is neutral, lower is opportunity)
        price_pos = metrics.get("price_position_52w")
        if price_pos is not None:
            if price_pos < 20:
                scores["price_vs_52w"] = 90  # Near 52w low - potential opportunity
            elif price_pos < 40:
                scores["price_vs_52w"] = 80
            elif price_pos < 60:
                scores["price_vs_52w"] = 70
            elif price_pos < 80:
                scores["price_vs_52w"] = 60
            else:
                scores["price_vs_52w"] = 50  # Near 52w high
        else:
            scores["price_vs_52w"] = 50

        # Moving Average Signal
        above_50 = metrics.get("above_ma_50")
        above_200 = metrics.get("above_ma_200")
        golden = metrics.get("golden_cross")

        ma_score = 50
        if above_50 is True:
            ma_score += 15
        if above_200 is True:
            ma_score += 15
        if golden is True:
            ma_score += 20
        elif golden is False:
            ma_score -= 10  # Death cross
        scores["moving_avg_signal"] = min(100, ma_score)

        # Analyst Rating
        rec = metrics.get("analyst_recommendation")
        if rec:
            rec_lower = rec.lower()
            if "strong" in rec_lower and "buy" in rec_lower:
                scores["analyst_rating"] = 100
            elif "buy" in rec_lower:
                scores["analyst_rating"] = 85
            elif "hold" in rec_lower:
                scores["analyst_rating"] = 60
            elif "sell" in rec_lower:
                scores["analyst_rating"] = 30
            else:
                scores["analyst_rating"] = 50
        else:
            scores["analyst_rating"] = 50

        return scores

    def _generate_recommendation(self, score: float, metrics: Dict, scores: Dict) -> Dict:
        """Generate buy/hold/sell recommendation with reasoning."""
        if score >= 80:
            action = "STRONG BUY"
            confidence = "High"
        elif score >= 70:
            action = "BUY"
            confidence = "Medium-High"
        elif score >= 60:
            action = "ACCUMULATE"
            confidence = "Medium"
        elif score >= 50:
            action = "HOLD"
            confidence = "Medium"
        elif score >= 40:
            action = "REDUCE"
            confidence = "Medium"
        else:
            action = "SELL"
            confidence = "Medium-High"

        # Generate reasoning
        reasons = []

        pe = metrics.get("pe_ratio")
        if pe and pe < 15:
            reasons.append(f"Attractive P/E of {pe:.1f}")
        elif pe and pe > 30:
            reasons.append(f"High P/E of {pe:.1f} suggests expensive valuation")

        peg = metrics.get("peg_ratio")
        if peg and peg < 1:
            reasons.append(f"PEG ratio of {peg:.2f} indicates undervaluation (Lynch criteria)")

        roe = metrics.get("roe")
        if roe and roe > 0.15:
            reasons.append(f"Strong ROE of {roe*100:.1f}%")
        elif roe and roe < 0.10:
            reasons.append(f"Weak ROE of {roe*100:.1f}%")

        de = metrics.get("debt_to_equity")
        if de and de > 100:
            reasons.append(f"High debt-to-equity of {de:.0f}%")
        elif de and de < 30:
            reasons.append("Conservative debt levels")

        if metrics.get("golden_cross"):
            reasons.append("Bullish golden cross pattern (50MA > 200MA)")
        elif metrics.get("golden_cross") is False:
            reasons.append("Bearish death cross pattern (50MA < 200MA)")

        rev_growth = metrics.get("revenue_growth")
        if rev_growth and rev_growth > 0.15:
            reasons.append(f"Strong revenue growth of {rev_growth*100:.1f}%")
        elif rev_growth and rev_growth < 0:
            reasons.append(f"Revenue declining by {abs(rev_growth)*100:.1f}%")

        return {
            "action": action,
            "confidence": confidence,
            "score": round(score, 2),
            "reasons": reasons[:5],  # Top 5 reasons
        }

    def _identify_strengths(self, scores: Dict) -> List[str]:
        """Identify top scoring metrics."""
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        strengths = []
        for metric, score in sorted_scores[:3]:
            if score >= 75:
                strengths.append(f"{metric.replace('_', ' ').title()}: {score}/100")
        return strengths

    def _identify_concerns(self, scores: Dict) -> List[str]:
        """Identify lowest scoring metrics."""
        sorted_scores = sorted(scores.items(), key=lambda x: x[1])
        concerns = []
        for metric, score in sorted_scores[:3]:
            if score < 50:
                concerns.append(f"{metric.replace('_', ' ').title()}: {score}/100")
        return concerns

    def review_predictions(self) -> Dict:
        """Review past predictions and adjust weights based on accuracy."""
        predictions = self.history.get('predictions', [])
        if len(predictions) < 5:
            return {"message": "Need more prediction history to review"}

        accurate = 0
        total = 0
        metric_accuracy = {k: {'correct': 0, 'total': 0} for k in self.weights.keys()}

        for pred in predictions:
            if 'actual_outcome' not in pred:
                continue

            total += 1
            predicted = pred.get('predicted_direction', 'neutral')
            actual = pred.get('actual_outcome', 'neutral')

            if predicted == actual:
                accurate += 1
                # Boost weights for metrics that scored high in accurate predictions
                for metric, score in pred.get('scores', {}).items():
                    if metric in metric_accuracy:
                        metric_accuracy[metric]['correct'] += 1 if score > 70 else 0
                        metric_accuracy[metric]['total'] += 1

        # Adjust weights based on accuracy
        if total > 0:
            overall_accuracy = accurate / total

            for metric in self.weights:
                if metric_accuracy[metric]['total'] > 0:
                    metric_acc = metric_accuracy[metric]['correct'] / metric_accuracy[metric]['total']
                    # Adjust weight slightly based on metric accuracy
                    adjustment = (metric_acc - 0.5) * 0.02  # Max 1% adjustment
                    self.weights[metric] = max(0.02, min(0.20, self.weights[metric] + adjustment))

            # Normalize weights to sum to 1
            total_weight = sum(self.weights.values())
            self.weights = {k: v/total_weight for k, v in self.weights.items()}

            self._save_history()

            return {
                "overall_accuracy": f"{overall_accuracy*100:.1f}%",
                "predictions_reviewed": total,
                "weights_adjusted": True,
                "new_weights": self.weights
            }

        return {"message": "No completed predictions to review"}

    def generate_report(self, symbols: List[str]) -> str:
        """Generate comprehensive markdown report."""
        report_lines = [
            "# Stock Analysis Report",
            f"\n**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"\n**Analyzer Version:** 1.0",
            f"\n**Symbols Analyzed:** {len(symbols)}",
            "\n---\n",
            "## Executive Summary\n",
        ]

        analyses = []
        for symbol in symbols:
            analysis = self.analyze_stock(symbol)
            if 'error' not in analysis:
                analyses.append(analysis)

        # Sort by score
        analyses.sort(key=lambda x: x['overall_score'], reverse=True)

        # Summary table
        report_lines.append("| Rank | Symbol | Score | Recommendation | Price |")
        report_lines.append("|------|--------|-------|----------------|-------|")

        for i, a in enumerate(analyses, 1):
            report_lines.append(
                f"| {i} | **{a['symbol']}** | {a['overall_score']}/100 | "
                f"{a['recommendation']['action']} | ${a['price']:.2f} |"
            )

        report_lines.append("\n---\n")
        report_lines.append("## Detailed Analysis\n")

        for analysis in analyses:
            report_lines.extend(self._format_analysis(analysis))
            report_lines.append("\n---\n")

        # Add methodology section
        report_lines.extend([
            "## Methodology\n",
            "This analysis uses a weighted scoring system based on fundamental and technical metrics:\n",
            "| Metric | Weight | Description |",
            "|--------|--------|-------------|",
        ])

        metric_descriptions = {
            "pe_ratio": "Price-to-Earnings ratio (Graham/Buffett criteria)",
            "peg_ratio": "P/E to Growth ratio (Peter Lynch criteria)",
            "price_to_book": "Price-to-Book value (Graham criteria)",
            "debt_to_equity": "Financial leverage indicator",
            "roe": "Return on Equity - profitability metric",
            "revenue_growth": "Year-over-year revenue growth",
            "eps_growth": "Earnings per share growth",
            "dividend_yield": "Annual dividend yield",
            "price_vs_52w": "Position in 52-week price range",
            "moving_avg_signal": "50/200-day moving average signals",
            "analyst_rating": "Wall Street analyst consensus",
        }

        for metric, weight in sorted(self.weights.items(), key=lambda x: x[1], reverse=True):
            desc = metric_descriptions.get(metric, "")
            report_lines.append(f"| {metric.replace('_', ' ').title()} | {weight*100:.1f}% | {desc} |")

        report_lines.extend([
            "\n## Disclaimer\n",
            "*This analysis is for informational purposes only and should not be considered financial advice. "
            "Always conduct your own research and consult with a qualified financial advisor before making "
            "investment decisions.*\n",
            f"\n---\n*Report generated by Portfolio Tracker Stock Analyzer*"
        ])

        report = "\n".join(report_lines)

        # Save to file
        with open(REPORT_FILE, 'w') as f:
            f.write(report)

        return report

    def _format_analysis(self, analysis: Dict) -> List[str]:
        """Format a single stock analysis for the report."""
        lines = [
            f"### {analysis['symbol']}",
            f"\n**Score:** {analysis['overall_score']}/100 | "
            f"**Recommendation:** {analysis['recommendation']['action']} | "
            f"**Confidence:** {analysis['recommendation']['confidence']}",
            f"\n**Current Price:** ${analysis['price']:.2f}",
            "\n#### Key Metrics",
            "| Metric | Value | Score |",
            "|--------|-------|-------|",
        ]

        m = analysis['metrics']
        s = analysis['scores']

        metrics_to_show = [
            ("P/E Ratio", m.get('pe_ratio'), s.get('pe_ratio')),
            ("PEG Ratio", m.get('peg_ratio'), s.get('peg_ratio')),
            ("Price/Book", m.get('price_to_book'), s.get('price_to_book')),
            ("Debt/Equity", m.get('debt_to_equity'), s.get('debt_to_equity')),
            ("ROE", m.get('roe'), s.get('roe')),
            ("Revenue Growth", m.get('revenue_growth'), s.get('revenue_growth')),
            ("52W Position", m.get('price_position_52w'), s.get('price_vs_52w')),
        ]

        for name, value, score in metrics_to_show:
            if value is not None:
                if isinstance(value, float):
                    if 'Growth' in name or 'ROE' in name:
                        val_str = f"{value*100:.1f}%" if abs(value) < 1 else f"{value:.1f}%"
                    elif 'Position' in name:
                        val_str = f"{value:.0f}%"
                    else:
                        val_str = f"{value:.2f}"
                else:
                    val_str = str(value)
                score_str = f"{score:.0f}/100" if score else "N/A"
                lines.append(f"| {name} | {val_str} | {score_str} |")

        lines.append("\n#### Analysis")
        for reason in analysis['recommendation'].get('reasons', []):
            lines.append(f"- {reason}")

        if analysis.get('key_strengths'):
            lines.append("\n**Strengths:**")
            for strength in analysis['key_strengths']:
                lines.append(f"- {strength}")

        if analysis.get('key_concerns'):
            lines.append("\n**Concerns:**")
            for concern in analysis['key_concerns']:
                lines.append(f"- {concern}")

        return lines


# Global instance
stock_analyzer = StockAnalyzer()
