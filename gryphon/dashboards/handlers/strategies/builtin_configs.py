"""
"""

from cdecimal import Decimal

BUILTIN_STRAT_CONFIGS = {
    'manual': {
        'display_name': 'Manual',
        'strategy_actor': 'MULTI',
        'price_currency': 'USD',
        'volume_currency': 'BTC',
        'base_point_radius': 10,
        'graph_volume_threshold': Decimal('0.00001'),
        'position_graph_max': Decimal('100'),
        'position_graph_min': Decimal('-100'),
    },
    'multiexchange_linear': {
        'display_name': 'Multiexchange Linear BTC',
        'strategy_actor': 'MULTIEXCHANGE_LINEAR',
        'price_currency': 'USD',
        'volume_currency': 'BTC',
        'base_point_radius': 10,
        'graph_volume_threshold': Decimal('0.00001'),
        'position_graph_max': Decimal('2'),
        'position_graph_min': Decimal('-2'),
    },
    'simple_mm': {
        'display_name': 'Simple Market Making',
        'strategy_actor': 'SIMPLE_MM',
        'price_currency': 'USD',
        'volume_currency': 'BTC',
        'base_point_radius': 10,
        'graph_volume_threshold': Decimal('0.00001'),
        'position_graph_max': Decimal('2'),
        'position_graph_min': Decimal('-2'),
    },
    'simple_arb': {
        'display_name': 'Simple Arbitrage',
        'strategy_actor': 'SIMPLE_ARB',
        'price_currency': 'USD',
        'volume_currency': 'BTC',
        'base_point_radius': 10,
        'graph_volume_threshold': Decimal('0.00001'),
        'position_graph_max': Decimal('10'),
        'position_graph_min': Decimal('-10'),
    },
}


