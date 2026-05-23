"""
Hedge Fund Performance Metrics
Professional-grade risk and return metrics used by institutional investors.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from scipy import stats
from datetime import datetime, timedelta


class HedgeFundMetrics:
    """
    Comprehensive performance metrics used by hedge funds and institutional investors.
    """

    def __init__(self, returns: pd.Series, benchmark_returns: Optional[pd.Series] = None,
                 risk_free_rate: float = 0.05, periods_per_year: int = 252):
        """
        Args:
            returns: Daily returns series
            benchmark_returns: Benchmark (e.g., S&P 500) returns for comparison
            risk_free_rate: Annual risk-free rate (default 5%)
            periods_per_year: Trading days per year (252 for daily data)
        """
        self.returns = returns.dropna()
        self.benchmark_returns = benchmark_returns.dropna() if benchmark_returns is not None else None
        self.rf_rate = risk_free_rate
        self.periods = periods_per_year
        self.daily_rf = (1 + risk_free_rate) ** (1/periods_per_year) - 1

    def calculate_all(self) -> Dict:
        """Calculate all hedge fund metrics."""
        metrics = {
            "return_metrics": self._return_metrics(),
            "risk_metrics": self._risk_metrics(),
            "risk_adjusted_metrics": self._risk_adjusted_metrics(),
            "drawdown_metrics": self._drawdown_metrics(),
            "tail_risk_metrics": self._tail_risk_metrics(),
            "trading_metrics": self._trading_metrics(),
            "benchmark_metrics": self._benchmark_metrics() if self.benchmark_returns is not None else None,
            "distribution_metrics": self._distribution_metrics(),
        }
        return metrics

    def _return_metrics(self) -> Dict:
        """Basic return statistics."""
        cumulative = (1 + self.returns).cumprod()
        total_return = cumulative.iloc[-1] - 1

        # Annualized return (CAGR)
        n_years = len(self.returns) / self.periods
        cagr = (1 + total_return) ** (1 / max(n_years, 0.01)) - 1

        # Monthly returns approximation
        monthly_returns = self.returns.resample('M').apply(lambda x: (1 + x).prod() - 1)

        return {
            "total_return_pct": float(total_return * 100),
            "cagr_pct": float(cagr * 100),
            "avg_daily_return_pct": float(self.returns.mean() * 100),
            "avg_monthly_return_pct": float(monthly_returns.mean() * 100) if len(monthly_returns) > 0 else 0,
            "best_day_pct": float(self.returns.max() * 100),
            "worst_day_pct": float(self.returns.min() * 100),
            "best_month_pct": float(monthly_returns.max() * 100) if len(monthly_returns) > 0 else 0,
            "worst_month_pct": float(monthly_returns.min() * 100) if len(monthly_returns) > 0 else 0,
            "positive_days_pct": float((self.returns > 0).mean() * 100),
            "positive_months_pct": float((monthly_returns > 0).mean() * 100) if len(monthly_returns) > 0 else 0,
        }

    def _risk_metrics(self) -> Dict:
        """Volatility and variance metrics."""
        daily_vol = self.returns.std()
        annual_vol = daily_vol * np.sqrt(self.periods)

        # Downside deviation (semi-deviation)
        downside_returns = self.returns[self.returns < 0]
        downside_dev = downside_returns.std() * np.sqrt(self.periods) if len(downside_returns) > 0 else 0

        # Upside deviation
        upside_returns = self.returns[self.returns > 0]
        upside_dev = upside_returns.std() * np.sqrt(self.periods) if len(upside_returns) > 0 else 0

        return {
            "daily_volatility_pct": float(daily_vol * 100),
            "annual_volatility_pct": float(annual_vol * 100),
            "downside_deviation_pct": float(downside_dev * 100),
            "upside_deviation_pct": float(upside_dev * 100),
            "upside_downside_ratio": float(upside_dev / downside_dev) if downside_dev > 0 else float('inf'),
            "variance": float(self.returns.var()),
        }

    def _risk_adjusted_metrics(self) -> Dict:
        """Risk-adjusted performance ratios."""
        excess_returns = self.returns - self.daily_rf
        annual_return = self.returns.mean() * self.periods
        annual_vol = self.returns.std() * np.sqrt(self.periods)

        # Sharpe Ratio
        sharpe = (annual_return - self.rf_rate) / annual_vol if annual_vol > 0 else 0

        # Sortino Ratio (uses downside deviation)
        downside_returns = self.returns[self.returns < self.daily_rf] - self.daily_rf
        downside_dev = downside_returns.std() * np.sqrt(self.periods) if len(downside_returns) > 0 else 0
        sortino = (annual_return - self.rf_rate) / downside_dev if downside_dev > 0 else 0

        # Calmar Ratio (return / max drawdown)
        max_dd = self._calculate_max_drawdown()
        calmar = annual_return / abs(max_dd) if max_dd != 0 else 0

        # Omega Ratio
        omega = self._calculate_omega_ratio()

        # Treynor Ratio (if benchmark available)
        treynor = None
        if self.benchmark_returns is not None:
            beta = self._calculate_beta()
            treynor = (annual_return - self.rf_rate) / beta if beta != 0 else 0

        # Information Ratio
        info_ratio = None
        if self.benchmark_returns is not None:
            info_ratio = self._calculate_information_ratio()

        return {
            "sharpe_ratio": float(sharpe),
            "sortino_ratio": float(sortino),
            "calmar_ratio": float(calmar),
            "omega_ratio": float(omega),
            "treynor_ratio": float(treynor) if treynor is not None else None,
            "information_ratio": float(info_ratio) if info_ratio is not None else None,
        }

    def _calculate_omega_ratio(self, threshold: float = 0) -> float:
        """
        Omega Ratio: Probability-weighted ratio of gains vs losses.
        Higher is better. >1 means more upside than downside.
        """
        gains = self.returns[self.returns > threshold] - threshold
        losses = threshold - self.returns[self.returns <= threshold]

        if losses.sum() == 0:
            return float('inf')
        return gains.sum() / losses.sum()

    def _calculate_beta(self) -> float:
        """Calculate beta relative to benchmark."""
        if self.benchmark_returns is None:
            return 1.0

        # Align the series
        aligned = pd.concat([self.returns, self.benchmark_returns], axis=1).dropna()
        if len(aligned) < 2:
            return 1.0

        covariance = aligned.iloc[:, 0].cov(aligned.iloc[:, 1])
        variance = aligned.iloc[:, 1].var()

        return covariance / variance if variance > 0 else 1.0

    def _calculate_information_ratio(self) -> float:
        """Information Ratio: Active return / Tracking error."""
        if self.benchmark_returns is None:
            return 0.0

        aligned = pd.concat([self.returns, self.benchmark_returns], axis=1).dropna()
        if len(aligned) < 2:
            return 0.0

        active_returns = aligned.iloc[:, 0] - aligned.iloc[:, 1]
        tracking_error = active_returns.std() * np.sqrt(self.periods)
        active_return = active_returns.mean() * self.periods

        return active_return / tracking_error if tracking_error > 0 else 0

    def _calculate_max_drawdown(self) -> float:
        """Calculate maximum drawdown."""
        cumulative = (1 + self.returns).cumprod()
        peak = cumulative.cummax()
        drawdown = (cumulative - peak) / peak
        return drawdown.min()

    def _drawdown_metrics(self) -> Dict:
        """Comprehensive drawdown analysis."""
        cumulative = (1 + self.returns).cumprod()
        peak = cumulative.cummax()
        drawdown = (cumulative - peak) / peak

        max_dd = drawdown.min()

        # Drawdown duration
        is_drawdown = drawdown < 0
        drawdown_periods = []
        current_dd_start = None

        for i, (idx, in_dd) in enumerate(is_drawdown.items()):
            if in_dd and current_dd_start is None:
                current_dd_start = i
            elif not in_dd and current_dd_start is not None:
                drawdown_periods.append(i - current_dd_start)
                current_dd_start = None

        if current_dd_start is not None:
            drawdown_periods.append(len(is_drawdown) - current_dd_start)

        avg_dd_duration = np.mean(drawdown_periods) if drawdown_periods else 0
        max_dd_duration = max(drawdown_periods) if drawdown_periods else 0

        # Average drawdown
        avg_dd = drawdown[drawdown < 0].mean() if (drawdown < 0).any() else 0

        # Recovery factor
        total_return = cumulative.iloc[-1] - 1
        recovery_factor = total_return / abs(max_dd) if max_dd != 0 else 0

        # Ulcer Index (RMS of drawdowns)
        ulcer_index = np.sqrt((drawdown ** 2).mean())

        return {
            "max_drawdown_pct": float(max_dd * 100),
            "avg_drawdown_pct": float(avg_dd * 100),
            "max_drawdown_duration_days": int(max_dd_duration),
            "avg_drawdown_duration_days": float(avg_dd_duration),
            "current_drawdown_pct": float(drawdown.iloc[-1] * 100),
            "recovery_factor": float(recovery_factor),
            "ulcer_index": float(ulcer_index * 100),
            "pain_index": float(abs(drawdown).mean() * 100),  # Average of all drawdowns
        }

    def _tail_risk_metrics(self) -> Dict:
        """Value at Risk and tail risk metrics."""
        # Historical VaR
        var_95 = np.percentile(self.returns, 5)
        var_99 = np.percentile(self.returns, 1)

        # Conditional VaR (Expected Shortfall / CVaR)
        cvar_95 = self.returns[self.returns <= var_95].mean()
        cvar_99 = self.returns[self.returns <= var_99].mean()

        # Parametric VaR (assuming normal distribution)
        mean_return = self.returns.mean()
        std_return = self.returns.std()
        param_var_95 = mean_return - 1.645 * std_return
        param_var_99 = mean_return - 2.326 * std_return

        # Tail Ratio
        percentile_95 = np.percentile(self.returns, 95)
        percentile_5 = np.percentile(self.returns, 5)
        tail_ratio = abs(percentile_95 / percentile_5) if percentile_5 != 0 else 0

        # Gain/Loss Ratio
        gains = self.returns[self.returns > 0]
        losses = self.returns[self.returns < 0]
        gain_loss_ratio = abs(gains.mean() / losses.mean()) if len(losses) > 0 and losses.mean() != 0 else 0

        return {
            "var_95_pct": float(var_95 * 100),
            "var_99_pct": float(var_99 * 100),
            "cvar_95_pct": float(cvar_95 * 100) if not np.isnan(cvar_95) else 0,
            "cvar_99_pct": float(cvar_99 * 100) if not np.isnan(cvar_99) else 0,
            "parametric_var_95_pct": float(param_var_95 * 100),
            "parametric_var_99_pct": float(param_var_99 * 100),
            "tail_ratio": float(tail_ratio),
            "gain_loss_ratio": float(gain_loss_ratio),
        }

    def _trading_metrics(self) -> Dict:
        """Trading performance metrics."""
        # Win rate
        wins = (self.returns > 0).sum()
        losses = (self.returns < 0).sum()
        total = wins + losses
        win_rate = wins / total if total > 0 else 0

        # Profit Factor
        gross_profit = self.returns[self.returns > 0].sum()
        gross_loss = abs(self.returns[self.returns < 0].sum())
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')

        # Payoff Ratio (avg win / avg loss)
        avg_win = self.returns[self.returns > 0].mean()
        avg_loss = abs(self.returns[self.returns < 0].mean())
        payoff_ratio = avg_win / avg_loss if avg_loss > 0 else 0

        # Expectancy
        expectancy = (win_rate * avg_win) - ((1 - win_rate) * avg_loss) if not np.isnan(avg_win) and not np.isnan(avg_loss) else 0

        # Kelly Criterion
        kelly = 0
        if payoff_ratio > 0:
            kelly = win_rate - ((1 - win_rate) / payoff_ratio)

        # Consecutive wins/losses
        signs = np.sign(self.returns)
        max_consecutive_wins = self._max_consecutive(signs, 1)
        max_consecutive_losses = self._max_consecutive(signs, -1)

        return {
            "win_rate_pct": float(win_rate * 100),
            "profit_factor": float(profit_factor),
            "payoff_ratio": float(payoff_ratio),
            "expectancy_pct": float(expectancy * 100),
            "kelly_criterion_pct": float(max(0, kelly) * 100),
            "max_consecutive_wins": int(max_consecutive_wins),
            "max_consecutive_losses": int(max_consecutive_losses),
            "total_trades": int(total),
            "winning_trades": int(wins),
            "losing_trades": int(losses),
        }

    def _max_consecutive(self, series: pd.Series, value: int) -> int:
        """Find maximum consecutive occurrences of a value."""
        groups = (series != value).cumsum()
        consecutive = series.groupby(groups).transform('size')
        consecutive = consecutive[series == value]
        return consecutive.max() if len(consecutive) > 0 else 0

    def _benchmark_metrics(self) -> Dict:
        """Metrics relative to benchmark."""
        if self.benchmark_returns is None:
            return {}

        aligned = pd.concat([self.returns, self.benchmark_returns], axis=1).dropna()
        if len(aligned) < 2:
            return {}

        strategy = aligned.iloc[:, 0]
        benchmark = aligned.iloc[:, 1]

        # Beta and Alpha
        beta = self._calculate_beta()
        strategy_return = strategy.mean() * self.periods
        benchmark_return = benchmark.mean() * self.periods
        alpha = strategy_return - (self.rf_rate + beta * (benchmark_return - self.rf_rate))

        # Correlation
        correlation = strategy.corr(benchmark)

        # R-squared
        r_squared = correlation ** 2

        # Tracking error
        active_returns = strategy - benchmark
        tracking_error = active_returns.std() * np.sqrt(self.periods)

        # Up/Down capture
        up_days = benchmark > 0
        down_days = benchmark < 0

        up_capture = (strategy[up_days].mean() / benchmark[up_days].mean() * 100) if up_days.sum() > 0 else 0
        down_capture = (strategy[down_days].mean() / benchmark[down_days].mean() * 100) if down_days.sum() > 0 else 0

        return {
            "beta": float(beta),
            "alpha_pct": float(alpha * 100),
            "correlation": float(correlation),
            "r_squared": float(r_squared),
            "tracking_error_pct": float(tracking_error * 100),
            "up_capture_pct": float(up_capture),
            "down_capture_pct": float(down_capture),
            "capture_ratio": float(up_capture / down_capture) if down_capture != 0 else 0,
        }

    def _distribution_metrics(self) -> Dict:
        """Statistical distribution metrics."""
        skewness = stats.skew(self.returns)
        kurtosis = stats.kurtosis(self.returns)

        # Jarque-Bera test for normality
        jb_stat, jb_pvalue = stats.jarque_bera(self.returns)

        return {
            "skewness": float(skewness),
            "kurtosis": float(kurtosis),  # Excess kurtosis (normal = 0)
            "is_normal_distribution": bool(jb_pvalue > 0.05),
            "jarque_bera_pvalue": float(jb_pvalue),
        }

    def get_summary_report(self) -> str:
        """Generate a human-readable summary report."""
        metrics = self.calculate_all()

        report = []
        report.append("=" * 60)
        report.append("HEDGE FUND PERFORMANCE REPORT")
        report.append("=" * 60)

        # Returns
        ret = metrics['return_metrics']
        report.append("\n📈 RETURN METRICS")
        report.append(f"  Total Return: {ret['total_return_pct']:.2f}%")
        report.append(f"  CAGR: {ret['cagr_pct']:.2f}%")
        report.append(f"  Best Day: {ret['best_day_pct']:.2f}% | Worst Day: {ret['worst_day_pct']:.2f}%")
        report.append(f"  Win Rate: {ret['positive_days_pct']:.1f}%")

        # Risk
        risk = metrics['risk_metrics']
        report.append("\n⚠️ RISK METRICS")
        report.append(f"  Annual Volatility: {risk['annual_volatility_pct']:.2f}%")
        report.append(f"  Downside Deviation: {risk['downside_deviation_pct']:.2f}%")

        # Risk-Adjusted
        ra = metrics['risk_adjusted_metrics']
        report.append("\n⚖️ RISK-ADJUSTED PERFORMANCE")
        report.append(f"  Sharpe Ratio: {ra['sharpe_ratio']:.2f}")
        report.append(f"  Sortino Ratio: {ra['sortino_ratio']:.2f}")
        report.append(f"  Calmar Ratio: {ra['calmar_ratio']:.2f}")
        report.append(f"  Omega Ratio: {ra['omega_ratio']:.2f}")

        # Drawdown
        dd = metrics['drawdown_metrics']
        report.append("\n📉 DRAWDOWN ANALYSIS")
        report.append(f"  Max Drawdown: {dd['max_drawdown_pct']:.2f}%")
        report.append(f"  Avg Drawdown: {dd['avg_drawdown_pct']:.2f}%")
        report.append(f"  Max DD Duration: {dd['max_drawdown_duration_days']} days")
        report.append(f"  Recovery Factor: {dd['recovery_factor']:.2f}")

        # Tail Risk
        tr = metrics['tail_risk_metrics']
        report.append("\n🎯 TAIL RISK (Value at Risk)")
        report.append(f"  VaR 95%: {tr['var_95_pct']:.2f}% (daily)")
        report.append(f"  CVaR 95%: {tr['cvar_95_pct']:.2f}% (expected shortfall)")
        report.append(f"  Tail Ratio: {tr['tail_ratio']:.2f}")

        # Trading
        trade = metrics['trading_metrics']
        report.append("\n💹 TRADING METRICS")
        report.append(f"  Profit Factor: {trade['profit_factor']:.2f}")
        report.append(f"  Payoff Ratio: {trade['payoff_ratio']:.2f}")
        report.append(f"  Kelly Criterion: {trade['kelly_criterion_pct']:.1f}%")

        # Benchmark
        if metrics['benchmark_metrics']:
            bm = metrics['benchmark_metrics']
            report.append("\n📊 VS BENCHMARK")
            report.append(f"  Alpha: {bm['alpha_pct']:.2f}%")
            report.append(f"  Beta: {bm['beta']:.2f}")
            report.append(f"  Correlation: {bm['correlation']:.2f}")
            report.append(f"  Up Capture: {bm['up_capture_pct']:.1f}%")
            report.append(f"  Down Capture: {bm['down_capture_pct']:.1f}%")

        report.append("\n" + "=" * 60)

        return "\n".join(report)


def calculate_metrics_for_returns(returns: List[float],
                                   benchmark_returns: Optional[List[float]] = None) -> Dict:
    """Convenience function to calculate all metrics from return lists."""
    returns_series = pd.Series(returns)
    benchmark_series = pd.Series(benchmark_returns) if benchmark_returns else None

    hfm = HedgeFundMetrics(returns_series, benchmark_series)
    return hfm.calculate_all()
