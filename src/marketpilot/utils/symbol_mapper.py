"""
Symbol Mapper Utility - Maps trading symbols to asset slugs
"""

from typing import Optional, Dict
from pathlib import Path
from marketpilot.utils.config_loader import load_config
from marketpilot.utils.logger import log_event


class SymbolMapper:
    """Utility class for mapping trading symbols to asset slugs"""

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize SymbolMapper

        Args:
            config_path: Path to symbol_mapping.yaml (optional)
        """
        if config_path is None:
            config_path = str(
                Path(__file__).parent.parent / "config" / "symbol_mapping.yaml"
            )

        self.config = load_config(config_path)
        self.rules = self.config.get("mapping_rules", {})

        # Build fast lookup table
        self.lookup = self._build_lookup()

        log_event(
            stage="initialization",
            block="symbol_mapper",
            level="INFO",
            msg="SymbolMapper initialized",
            extra={"total_mappings": len(self.lookup)},
        )

    def _build_lookup(self) -> Dict[str, str]:
        """Build symbol -> slug lookup table"""
        lookup = {}

        # Add cryptocurrencies
        for symbol, info in self.config.get("cryptocurrencies", {}).items():
            slug = info.get("slug")
            lookup[symbol.upper()] = slug
            for alias in info.get("aliases", []):
                lookup[alias.upper()] = slug

        # Add stocks
        for symbol, info in self.config.get("stocks", {}).items():
            slug = info.get("slug")
            lookup[symbol.upper()] = slug
            for alias in info.get("aliases", []):
                lookup[alias.upper()] = slug

        return lookup

    def _normalize(self, symbol: str) -> str:
        """Remove exchange prefixes and suffixes"""
        normalized = symbol.upper()

        # Remove prefixes
        for prefix in self.rules.get("exchange_prefixes", []):
            if normalized.startswith(prefix):
                normalized = normalized[len(prefix) :]
                break

        # Remove suffixes
        for suffix in self.rules.get("symbol_suffixes", []):
            if normalized.endswith(suffix):
                normalized = normalized[: -len(suffix)]
                break

        return normalized

    def _extract_base(self, symbol: str) -> Optional[str]:
        """Extract base crypto from pair (e.g., BTCUSDT -> BTC)"""
        symbol_upper = symbol.upper()

        for pair in self.rules.get("strip_pairs", []):
            if symbol_upper.endswith(pair):
                base = symbol_upper[: -len(pair)]
                if base in self.lookup:
                    return base

        return None

    def map_symbol_to_slug(self, symbol: str) -> str:
        """
        Map trading symbol to asset slug

        Args:
            symbol: Trading symbol (e.g., "BINANCE:BTCUSDT.P", "AAPL")

        Returns:
            Asset slug (e.g., "bitcoin", "apple")
        """
        if not symbol:
            return "unknown"

        # Try exact match
        if symbol.upper() in self.lookup:
            return self.lookup[symbol.upper()]

        # Try normalized
        normalized = self._normalize(symbol)
        if normalized in self.lookup:
            return self.lookup[normalized]

        # Try extracting base
        if self.rules.get("extract_base_from_exchange_format"):
            base = self._extract_base(normalized)
            if base and base in self.lookup:
                return self.lookup[base]

        # Fallback
        fallback = self.rules.get("fallback_strategy", "lowercase")
        if fallback == "lowercase":
            log_event(
                stage="mapping",
                block="symbol_mapper",
                level="WARNING",
                msg=f"No mapping found for {symbol}, using lowercase",
            )
            return normalized.lower()
        elif fallback == "error":
            raise ValueError(f"No mapping found for symbol: {symbol}")
        else:
            return symbol.lower()


# Singleton instance
_mapper: Optional[SymbolMapper] = None


def get_symbol_mapper(config_path: Optional[str] = None) -> SymbolMapper:
    """Get singleton SymbolMapper instance"""
    global _mapper
    if _mapper is None:
        _mapper = SymbolMapper(config_path)
    return _mapper


def map_symbol_to_slug(symbol: str) -> str:
    """Convenience function to map symbol to slug"""
    return get_symbol_mapper().map_symbol_to_slug(symbol)
