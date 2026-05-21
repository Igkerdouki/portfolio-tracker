"""
Autonomous Stock Analysis Agent
Runs continuously, analyzes stocks, tracks predictions, and self-improves.
"""

import os
import sys
import json
import time
import signal
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import threading

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.stock_analyzer import StockAnalyzer, REPORT_FILE, ANALYSIS_FILE

STATE_FILE = os.path.join(os.path.dirname(__file__), '..', '..', 'agent_state.json')
LOG_FILE = os.path.join(os.path.dirname(__file__), '..', '..', 'ANALYSIS_LOG.md')


class AnalysisAgent:
    """
    Autonomous agent that:
    1. Analyzes stocks from portfolio + watchlist
    2. Tracks predictions and outcomes
    3. Self-improves by reviewing prediction accuracy
    4. Generates reports and suggestions
    5. Persists state to continue from where it left off
    """

    def __init__(self):
        self.analyzer = StockAnalyzer()
        self.state = self._load_state()
        self.running = False
        self._stop_event = threading.Event()

    def _load_state(self) -> Dict:
        """Load agent state from file."""
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, 'r') as f:
                    return json.load(f)
            except:
                pass

        return {
            'watchlist': ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NVDA', 'TSLA'],
            'last_analysis': None,
            'analysis_count': 0,
            'improvement_cycles': 0,
            'pending_predictions': [],
            'completed_predictions': [],
            'top_picks': [],
            'avoid_list': [],
            'learning_log': [],
            'started_at': None,
        }

    def _save_state(self):
        """Save agent state to file."""
        with open(STATE_FILE, 'w') as f:
            json.dump(self.state, f, indent=2, default=str)

    def add_to_watchlist(self, symbols: List[str]):
        """Add symbols to watchlist."""
        for symbol in symbols:
            s = symbol.upper()
            if s not in self.state['watchlist']:
                self.state['watchlist'].append(s)
        self._save_state()

    def remove_from_watchlist(self, symbols: List[str]):
        """Remove symbols from watchlist."""
        for symbol in symbols:
            s = symbol.upper()
            if s in self.state['watchlist']:
                self.state['watchlist'].remove(s)
        self._save_state()

    def run_analysis_cycle(self) -> Dict:
        """Run a single analysis cycle on all watchlist stocks."""
        cycle_start = datetime.now()
        results = {
            'timestamp': cycle_start.isoformat(),
            'symbols_analyzed': 0,
            'top_picks': [],
            'concerns': [],
            'new_predictions': [],
        }

        self._log(f"\n## Analysis Cycle #{self.state['analysis_count'] + 1}")
        self._log(f"**Started:** {cycle_start.strftime('%Y-%m-%d %H:%M:%S')}")
        self._log(f"**Watchlist:** {', '.join(self.state['watchlist'])}\n")

        analyses = []

        for symbol in self.state['watchlist']:
            analysis = self.analyzer.analyze_stock(symbol)

            if 'error' not in analysis:
                analyses.append(analysis)
                results['symbols_analyzed'] += 1

                # Log individual analysis
                self._log(f"### {symbol}: {analysis['overall_score']}/100 - {analysis['recommendation']['action']}")

                # Create prediction for tracking
                if analysis['recommendation']['action'] in ['STRONG BUY', 'BUY']:
                    prediction = {
                        'symbol': symbol,
                        'timestamp': cycle_start.isoformat(),
                        'entry_price': analysis['price'],
                        'score': analysis['overall_score'],
                        'action': analysis['recommendation']['action'],
                        'predicted_direction': 'up',
                        'scores': analysis['scores'],
                        'check_date': (cycle_start + timedelta(days=30)).isoformat(),
                    }
                    self.state['pending_predictions'].append(prediction)
                    results['new_predictions'].append(prediction)

                elif analysis['recommendation']['action'] in ['SELL', 'REDUCE']:
                    prediction = {
                        'symbol': symbol,
                        'timestamp': cycle_start.isoformat(),
                        'entry_price': analysis['price'],
                        'score': analysis['overall_score'],
                        'action': analysis['recommendation']['action'],
                        'predicted_direction': 'down',
                        'scores': analysis['scores'],
                        'check_date': (cycle_start + timedelta(days=30)).isoformat(),
                    }
                    self.state['pending_predictions'].append(prediction)
            else:
                self._log(f"### {symbol}: Error - {analysis.get('error')}")

        # Sort by score and identify top picks
        analyses.sort(key=lambda x: x['overall_score'], reverse=True)

        # Top 3 picks
        top_picks = []
        for a in analyses[:3]:
            if a['overall_score'] >= 65:
                pick = {
                    'symbol': a['symbol'],
                    'score': a['overall_score'],
                    'action': a['recommendation']['action'],
                    'price': a['price'],
                    'reasons': a['recommendation']['reasons'][:3],
                }
                top_picks.append(pick)
                results['top_picks'].append(pick)

        self.state['top_picks'] = top_picks

        # Bottom 3 (concerns)
        for a in analyses[-3:]:
            if a['overall_score'] < 45:
                results['concerns'].append({
                    'symbol': a['symbol'],
                    'score': a['overall_score'],
                    'reasons': a['key_concerns'],
                })

        # Update state
        self.state['last_analysis'] = cycle_start.isoformat()
        self.state['analysis_count'] += 1

        # Log summary
        self._log("\n### Cycle Summary")
        self._log(f"- Stocks analyzed: {results['symbols_analyzed']}")
        self._log(f"- New predictions: {len(results['new_predictions'])}")

        if top_picks:
            self._log("\n**Top Picks:**")
            for pick in top_picks:
                self._log(f"- **{pick['symbol']}** (Score: {pick['score']}) - {pick['action']}")

        self._save_state()

        # Generate updated report
        self.analyzer.generate_report(self.state['watchlist'])

        return results

    def check_predictions(self) -> Dict:
        """Check pending predictions against actual outcomes."""
        self._log("\n## Prediction Review")

        results = {
            'checked': 0,
            'correct': 0,
            'incorrect': 0,
            'details': [],
        }

        now = datetime.now()
        still_pending = []

        for pred in self.state['pending_predictions']:
            check_date = datetime.fromisoformat(pred['check_date'])

            if now >= check_date:
                # Time to check this prediction
                current_analysis = self.analyzer.analyze_stock(pred['symbol'])

                if 'error' not in current_analysis:
                    entry_price = pred['entry_price']
                    current_price = current_analysis['price']
                    price_change = ((current_price - entry_price) / entry_price) * 100

                    # Determine actual outcome
                    if price_change > 2:
                        actual = 'up'
                    elif price_change < -2:
                        actual = 'down'
                    else:
                        actual = 'neutral'

                    predicted = pred['predicted_direction']
                    correct = (predicted == actual) or (actual == 'neutral')

                    # Record outcome
                    pred['actual_outcome'] = actual
                    pred['actual_price'] = current_price
                    pred['price_change_pct'] = round(price_change, 2)
                    pred['correct'] = correct

                    results['checked'] += 1
                    if correct:
                        results['correct'] += 1
                    else:
                        results['incorrect'] += 1

                    results['details'].append({
                        'symbol': pred['symbol'],
                        'predicted': predicted,
                        'actual': actual,
                        'price_change': f"{price_change:.1f}%",
                        'correct': correct,
                    })

                    self._log(f"- **{pred['symbol']}**: Predicted {predicted}, Actual {actual} ({price_change:+.1f}%) - {'Correct' if correct else 'Wrong'}")

                    # Move to completed
                    self.state['completed_predictions'].append(pred)

                    # Also add to analyzer history for weight adjustment
                    self.analyzer.history['predictions'].append(pred)
            else:
                still_pending.append(pred)

        self.state['pending_predictions'] = still_pending

        # If we checked predictions, trigger learning
        if results['checked'] > 0:
            accuracy = results['correct'] / results['checked'] * 100
            self._log(f"\n**Accuracy this cycle:** {accuracy:.1f}% ({results['correct']}/{results['checked']})")

            # Trigger weight adjustment
            self._improve_model()

        self._save_state()
        self.analyzer._save_history()

        return results

    def _improve_model(self):
        """Adjust weights based on prediction accuracy."""
        self.state['improvement_cycles'] += 1

        review = self.analyzer.review_predictions()

        if 'overall_accuracy' in review:
            self._log(f"\n### Model Improvement Cycle #{self.state['improvement_cycles']}")
            self._log(f"- Overall accuracy: {review['overall_accuracy']}")
            self._log(f"- Predictions reviewed: {review['predictions_reviewed']}")
            self._log("- Weights adjusted based on performance")

            # Log what we learned
            learning = {
                'timestamp': datetime.now().isoformat(),
                'accuracy': review['overall_accuracy'],
                'cycle': self.state['improvement_cycles'],
            }
            self.state['learning_log'].append(learning)

    def _log(self, message: str):
        """Append to analysis log."""
        with open(LOG_FILE, 'a') as f:
            f.write(message + "\n")

    def get_suggestions(self) -> Dict:
        """Get current suggestions based on latest analysis."""
        return {
            'top_picks': self.state['top_picks'],
            'watchlist': self.state['watchlist'],
            'pending_predictions': len(self.state['pending_predictions']),
            'completed_predictions': len(self.state['completed_predictions']),
            'improvement_cycles': self.state['improvement_cycles'],
            'last_analysis': self.state['last_analysis'],
        }

    def run_continuous(self, interval_hours: float = 4):
        """Run analysis continuously in background."""
        self.running = True
        self.state['started_at'] = datetime.now().isoformat()
        self._stop_event.clear()

        # Initialize log
        self._log(f"\n# Analysis Agent Started")
        self._log(f"**Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self._log(f"**Interval:** {interval_hours} hours")
        self._log(f"**Watchlist:** {', '.join(self.state['watchlist'])}")
        self._log("\n---")

        while not self._stop_event.is_set():
            try:
                # Run analysis cycle
                self.run_analysis_cycle()

                # Check any due predictions
                self.check_predictions()

                # Wait for next cycle
                self._log(f"\n*Next analysis in {interval_hours} hours...*\n---")

                # Wait with ability to stop
                self._stop_event.wait(timeout=interval_hours * 3600)

            except Exception as e:
                self._log(f"\n**Error:** {str(e)}")
                time.sleep(60)  # Wait a minute on error

        self.running = False
        self._log(f"\n# Agent Stopped at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    def stop(self):
        """Stop the continuous analysis loop."""
        self._stop_event.set()


# Create global instance
analysis_agent = AnalysisAgent()


def main():
    """Run agent from command line."""
    import argparse

    parser = argparse.ArgumentParser(description='Stock Analysis Agent')
    parser.add_argument('--once', action='store_true', help='Run single analysis cycle')
    parser.add_argument('--continuous', action='store_true', help='Run continuously')
    parser.add_argument('--interval', type=float, default=4, help='Hours between analyses')
    parser.add_argument('--add', nargs='+', help='Add symbols to watchlist')
    parser.add_argument('--remove', nargs='+', help='Remove symbols from watchlist')
    parser.add_argument('--status', action='store_true', help='Show current status')

    args = parser.parse_args()

    agent = AnalysisAgent()

    if args.add:
        agent.add_to_watchlist(args.add)
        print(f"Added to watchlist: {args.add}")
        print(f"Current watchlist: {agent.state['watchlist']}")

    elif args.remove:
        agent.remove_from_watchlist(args.remove)
        print(f"Removed from watchlist: {args.remove}")
        print(f"Current watchlist: {agent.state['watchlist']}")

    elif args.status:
        suggestions = agent.get_suggestions()
        print("\n=== Analysis Agent Status ===")
        print(f"Watchlist: {', '.join(suggestions['watchlist'])}")
        print(f"Last analysis: {suggestions['last_analysis']}")
        print(f"Pending predictions: {suggestions['pending_predictions']}")
        print(f"Completed predictions: {suggestions['completed_predictions']}")
        print(f"Improvement cycles: {suggestions['improvement_cycles']}")

        if suggestions['top_picks']:
            print("\nTop Picks:")
            for pick in suggestions['top_picks']:
                print(f"  - {pick['symbol']}: {pick['score']}/100 ({pick['action']})")

    elif args.once:
        print("Running single analysis cycle...")
        results = agent.run_analysis_cycle()
        print(f"\nAnalyzed {results['symbols_analyzed']} stocks")

        if results['top_picks']:
            print("\nTop Picks:")
            for pick in results['top_picks']:
                print(f"  {pick['symbol']}: {pick['score']}/100 - {pick['action']}")

        print(f"\nReport saved to: {REPORT_FILE}")

    elif args.continuous:
        print(f"Starting continuous analysis (every {args.interval} hours)...")
        print("Press Ctrl+C to stop")

        def signal_handler(sig, frame):
            print("\nStopping agent...")
            agent.stop()

        signal.signal(signal.SIGINT, signal_handler)
        agent.run_continuous(args.interval)

    else:
        parser.print_help()


if __name__ == '__main__':
    main()
