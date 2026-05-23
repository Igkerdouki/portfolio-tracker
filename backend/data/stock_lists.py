"""
Preset stock lists for market scanning.
Includes major indices and sector-based groupings.
"""

# S&P 500 - Top 100 by market cap (most actively traded)
SP500_TOP100 = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BRK.B", "UNH", "JNJ",
    "V", "XOM", "JPM", "PG", "MA", "HD", "CVX", "LLY", "ABBV", "MRK",
    "PEP", "COST", "KO", "AVGO", "WMT", "MCD", "CSCO", "ACN", "TMO", "ABT",
    "DHR", "VZ", "ADBE", "NKE", "CMCSA", "WFC", "PM", "TXN", "CRM", "NEE",
    "UPS", "RTX", "MS", "BMY", "ORCL", "QCOM", "UNP", "COP", "HON", "LOW",
    "INTC", "IBM", "AMGN", "SPGI", "GS", "CAT", "BA", "ELV", "SBUX", "PLD",
    "INTU", "BLK", "DE", "AXP", "GILD", "AMD", "MDLZ", "ADI", "LMT", "ISRG",
    "CVS", "SYK", "BKNG", "REGN", "VRTX", "ADP", "TJX", "CI", "TMUS", "ZTS",
    "PANW", "PGR", "LRCX", "MO", "CB", "SO", "DUK", "MMC", "SNPS", "CME",
    "BDX", "EOG", "SLB", "SCHW", "ITW", "NOC", "EQIX", "FI", "USB", "APD"
]

# Full S&P 500 (all 500 components)
SP500_FULL = SP500_TOP100 + [
    "AON", "CL", "CSX", "ICE", "WM", "PNC", "MCO", "GD", "NSC", "EMR",
    "FCX", "SHW", "TGT", "ORLY", "PSA", "F", "HUM", "ATVI", "GM", "MET",
    "AEP", "D", "EW", "KLAC", "ROP", "TRV", "PSX", "GIS", "AIG", "MNST",
    "FTNT", "ADSK", "MSCI", "AZO", "PAYX", "APH", "MCHP", "NXPI", "CDNS", "DXCM",
    "JCI", "KMB", "SRE", "O", "A", "HES", "AFL", "PCAR", "PRU", "MAR",
    "NEM", "KHC", "TEL", "BIIB", "CMI", "STZ", "HLT", "EA", "ALL", "MSI",
    "YUM", "AJG", "OTIS", "IDXX", "DOW", "IQV", "CARR", "CTSH", "BK", "ROST",
    "DHI", "NUE", "GPN", "WELL", "FAST", "AME", "OXY", "VRSK", "ECL", "SPG",
    "XEL", "ROK", "CTAS", "WMB", "DVN", "KR", "ED", "PEG", "EXC", "ANET",
    "CPRT", "HPQ", "WEC", "DD", "DLTR", "EIX", "VICI", "AWK", "ILMN", "GLW",
    "MTD", "KEYS", "LEN", "FTV", "EBAY", "ANSS", "RSG", "PWR", "ODFL", "CBRE",
    "GWW", "CDW", "DAL", "EFX", "WTW", "WST", "ABC", "HAL", "APTV", "VMC",
    "PPG", "TROW", "HPE", "BAX", "FANG", "EQR", "LH", "CHD", "MTB", "AVB",
    "CAH", "DFS", "ON", "TDY", "TSCO", "RMD", "DTE", "FITB", "FE", "ALB",
    "WAB", "SBAC", "MKC", "WY", "BR", "ES", "URI", "ZBH", "ARE", "LVS",
    "AKAM", "NTRS", "VTR", "DOV", "HBAN", "AEE", "PFG", "CF", "STLD", "STE",
    "RF", "CTRA", "PKI", "EXR", "GPC", "WRB", "IR", "WAT", "HOLX", "CINF",
    "COO", "CNP", "DRI", "LYB", "IEX", "BALL", "LUV", "IP", "KEY", "SYF",
    "CLX", "BRO", "DGX", "EXPD", "MOH", "BBY", "FLT", "JBHT", "K", "TRGP",
    "EXPE", "FDS", "TER", "CE", "NVR", "J", "TXT", "AES", "CAG", "CHRW",
    "NDAQ", "PTC", "AMCR", "MRO", "BXP", "L", "SJM", "DPZ", "LDOS", "TYL",
    "AVY", "MAA", "TECH", "LNT", "SWKS", "CFG", "CMS", "UDR", "HRL", "POOL",
    "KIM", "PAYC", "ATO", "HST", "JKHY", "PHM", "MGM", "MOS", "HIG", "VTRS",
    "BEN", "WDC", "TPR", "IFF", "NTAP", "IPG", "CPT", "TAP", "EMN", "WBA",
    "BWA", "ROL", "RE", "KMX", "PEAK", "QRVO", "RHI", "UHS", "NRG", "SNA",
    "CTLT", "INCY", "AAL", "AAP", "AIZ", "AOS", "BIO", "CBOE", "CRL", "CZR",
    "DVA", "ETSY", "EVRG", "FFIV", "FMC", "FOXA", "FOX", "GL", "GNRC", "HAS",
    "HSIC", "HWM", "IRM", "JNPR", "LKQ", "LW", "MKTX", "MTCH", "NI", "NWSA",
    "NWS", "PARA", "PNR", "PNW", "REG", "RCL", "RL", "SEDG", "SEE", "SIVB",
    "ALLE", "BBWI", "CCL", "CPB", "CMA", "DISH", "GRMN", "HII", "LUMN", "MLM",
    "NLOK", "NCLH", "OGN", "PENN", "RNR", "WHR", "WYNN", "XRAY", "ZM", "ZBRA"
]

# NASDAQ 100
NASDAQ100 = [
    "AAPL", "MSFT", "AMZN", "NVDA", "META", "GOOGL", "GOOG", "TSLA", "AVGO", "COST",
    "PEP", "ADBE", "CSCO", "NFLX", "AMD", "CMCSA", "TMUS", "INTC", "TXN", "QCOM",
    "INTU", "AMGN", "AMAT", "ISRG", "HON", "BKNG", "SBUX", "MDLZ", "ADI", "VRTX",
    "GILD", "LRCX", "ADP", "REGN", "PANW", "SNPS", "KLAC", "CDNS", "MELI", "ASML",
    "PYPL", "MNST", "CSX", "ORLY", "MAR", "FTNT", "CHTR", "ABNB", "MRNA", "NXPI",
    "KDP", "MCHP", "CTAS", "AEP", "DXCM", "ADSK", "CPRT", "KHC", "PCAR", "AZN",
    "LULU", "PAYX", "EXC", "ROST", "EA", "ODFL", "WDAY", "XEL", "CRWD", "FAST",
    "CTSH", "VRSK", "BKR", "IDXX", "FANG", "CSGP", "CEG", "DDOG", "GEHC", "DLTR",
    "ILMN", "TEAM", "ZS", "ANSS", "EBAY", "BIIB", "WBD", "ALGN", "ENPH", "ZM",
    "JD", "LCID", "SIRI", "RIVN", "WBA", "MTCH", "OKTA", "DOCU", "SPLK", "VRSN"
]

# Dow Jones Industrial Average
DOW30 = [
    "AAPL", "AMGN", "AXP", "BA", "CAT", "CRM", "CSCO", "CVX", "DIS", "DOW",
    "GS", "HD", "HON", "IBM", "INTC", "JNJ", "JPM", "KO", "MCD", "MMM",
    "MRK", "MSFT", "NKE", "PG", "TRV", "UNH", "V", "VZ", "WBA", "WMT"
]

# Technology sector
TECH_STOCKS = [
    "AAPL", "MSFT", "GOOGL", "META", "NVDA", "AVGO", "CSCO", "ORCL", "CRM", "ADBE",
    "AMD", "INTC", "TXN", "QCOM", "IBM", "NOW", "INTU", "AMAT", "MU", "LRCX",
    "SNPS", "CDNS", "ADI", "KLAC", "MCHP", "NXPI", "HPQ", "HPE", "DELL", "KEYS",
    "NET", "DDOG", "ZS", "CRWD", "PANW", "FTNT", "OKTA", "MDB", "SNOW", "PLTR"
]

# Financial sector
FINANCIAL_STOCKS = [
    "JPM", "BAC", "WFC", "GS", "MS", "C", "BLK", "SCHW", "AXP", "USB",
    "PNC", "TFC", "COF", "BK", "STT", "NTRS", "FITB", "MTB", "CFG", "KEY",
    "HBAN", "RF", "ZION", "CMA", "ALLY", "DFS", "SYF", "AIG", "MET", "PRU",
    "AFL", "TRV", "ALL", "CB", "PGR", "HIG", "CINF", "WRB", "GL", "L"
]

# Healthcare sector
HEALTHCARE_STOCKS = [
    "UNH", "JNJ", "LLY", "PFE", "ABBV", "MRK", "TMO", "ABT", "DHR", "BMY",
    "AMGN", "GILD", "VRTX", "REGN", "ISRG", "MDT", "ELV", "CI", "HUM", "CVS",
    "SYK", "BDX", "ZTS", "BSX", "EW", "DXCM", "IDXX", "ALGN", "HOLX", "IQV",
    "A", "MTD", "RMD", "TECH", "WST", "PKI", "CRL", "DGX", "LH", "BIIB"
]

# Energy sector
ENERGY_STOCKS = [
    "XOM", "CVX", "COP", "EOG", "SLB", "MPC", "PSX", "VLO", "OXY", "PXD",
    "HES", "DVN", "FANG", "HAL", "WMB", "KMI", "OKE", "BKR", "TRGP", "MRO",
    "APA", "CTRA", "EQT", "MTDR", "PR", "RRC", "AR", "CNX", "NOV", "CHK"
]

# Consumer discretionary
CONSUMER_DISCRETIONARY = [
    "AMZN", "TSLA", "HD", "MCD", "NKE", "LOW", "SBUX", "TJX", "BKNG", "MAR",
    "YUM", "CMG", "ORLY", "AZO", "ROST", "DHI", "LEN", "GM", "F", "APTV",
    "MGM", "LVS", "WYNN", "RCL", "CCL", "NCLH", "DRI", "EXPE", "HLT", "H"
]

# ETFs for index tracking
POPULAR_ETFS = [
    "SPY", "QQQ", "IWM", "DIA", "VOO", "VTI", "VEA", "VWO", "EFA", "EEM",
    "GLD", "SLV", "USO", "UNG", "TLT", "IEF", "HYG", "LQD", "JNK", "BND",
    "XLF", "XLK", "XLE", "XLV", "XLI", "XLP", "XLY", "XLU", "XLB", "XLRE",
    "ARKK", "ARKG", "ARKW", "ARKF", "ARKQ", "SOXL", "TQQQ", "SPXL", "VXX", "UVXY"
]

# Cryptocurrencies (via ETFs/trusts where available)
CRYPTO_RELATED = [
    "COIN", "MSTR", "RIOT", "MARA", "CLSK", "HUT", "BITF", "CORZ", "SI", "SQ",
    "PYPL", "HOOD", "GBTC", "ETHE", "BITO", "BTF", "XBTF"
]

# High volatility / meme stocks
HIGH_VOLATILITY = [
    "GME", "AMC", "BBBY", "BB", "NOK", "PLTR", "SOFI", "WISH", "CLOV", "SPCE",
    "RIVN", "LCID", "NIO", "XPEV", "LI", "NKLA", "GOEV", "FSR", "RIDE", "WKHS"
]

# Dividend aristocrats (25+ years of dividend increases)
DIVIDEND_ARISTOCRATS = [
    "KO", "PG", "JNJ", "MMM", "PEP", "WMT", "ABT", "MCD", "XOM", "CVX",
    "EMR", "CL", "ITW", "ADP", "SHW", "BDX", "CTAS", "GPC", "SYY", "HRL",
    "AFL", "ED", "PPG", "TGT", "ABBV", "CAT", "GD", "CB", "AOS", "SPGI",
    "DOV", "LOW", "KMB", "NUE", "WBA", "FRT", "LEG", "T", "TROW", "VFC"
]

# All preset lists with descriptions
PRESET_LISTS = {
    "sp500_top100": {
        "name": "S&P 500 Top 100",
        "description": "Top 100 S&P 500 companies by market cap",
        "symbols": SP500_TOP100,
        "count": len(SP500_TOP100)
    },
    "sp500_full": {
        "name": "S&P 500 (Full)",
        "description": "All S&P 500 components",
        "symbols": SP500_FULL,
        "count": len(SP500_FULL)
    },
    "nasdaq100": {
        "name": "NASDAQ 100",
        "description": "Top 100 NASDAQ companies",
        "symbols": NASDAQ100,
        "count": len(NASDAQ100)
    },
    "dow30": {
        "name": "Dow Jones 30",
        "description": "Dow Jones Industrial Average",
        "symbols": DOW30,
        "count": len(DOW30)
    },
    "tech": {
        "name": "Technology",
        "description": "Major tech companies",
        "symbols": TECH_STOCKS,
        "count": len(TECH_STOCKS)
    },
    "financial": {
        "name": "Financials",
        "description": "Banks, insurance, asset managers",
        "symbols": FINANCIAL_STOCKS,
        "count": len(FINANCIAL_STOCKS)
    },
    "healthcare": {
        "name": "Healthcare",
        "description": "Pharma, biotech, medical devices",
        "symbols": HEALTHCARE_STOCKS,
        "count": len(HEALTHCARE_STOCKS)
    },
    "energy": {
        "name": "Energy",
        "description": "Oil, gas, and energy companies",
        "symbols": ENERGY_STOCKS,
        "count": len(ENERGY_STOCKS)
    },
    "consumer": {
        "name": "Consumer",
        "description": "Retail, restaurants, entertainment",
        "symbols": CONSUMER_DISCRETIONARY,
        "count": len(CONSUMER_DISCRETIONARY)
    },
    "etfs": {
        "name": "Popular ETFs",
        "description": "Index, sector, and thematic ETFs",
        "symbols": POPULAR_ETFS,
        "count": len(POPULAR_ETFS)
    },
    "crypto": {
        "name": "Crypto-Related",
        "description": "Crypto exchanges, miners, and ETFs",
        "symbols": CRYPTO_RELATED,
        "count": len(CRYPTO_RELATED)
    },
    "high_volatility": {
        "name": "High Volatility",
        "description": "Meme stocks and high-beta names",
        "symbols": HIGH_VOLATILITY,
        "count": len(HIGH_VOLATILITY)
    },
    "dividends": {
        "name": "Dividend Aristocrats",
        "description": "25+ years of dividend increases",
        "symbols": DIVIDEND_ARISTOCRATS,
        "count": len(DIVIDEND_ARISTOCRATS)
    }
}


def get_preset(preset_id: str) -> list:
    """Get symbols for a preset list."""
    preset = PRESET_LISTS.get(preset_id)
    if preset:
        return preset["symbols"]
    return []


def get_all_presets() -> dict:
    """Get all available preset lists with metadata."""
    return {
        key: {
            "name": value["name"],
            "description": value["description"],
            "count": value["count"]
        }
        for key, value in PRESET_LISTS.items()
    }
