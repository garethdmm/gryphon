from collections import defaultdict
import logging
import tornado.web

from delorean import Delorean

from gryphon.dashboards.handlers.admin_base import AdminBaseHandler
from gryphon.dashboards.handlers.mixins.active_exchanges import ActiveExchangesMixin
from gryphon.dashboards.handlers.mixins.start_and_end_time import StartAndEndTimeMixin
from gryphon.lib.models.emeraldhavoc.trade import Trade as EHTrade
from gryphon.lib.models.trade import Trade

logger = logging.getLogger(__name__)


class TradeViewHandler(AdminBaseHandler, StartAndEndTimeMixin, ActiveExchangesMixin):
    @tornado.web.authenticated
    def get(self):
        start_time, end_time = self.get_start_time_and_end_time()
        active_exchanges = self.get_active_exchanges()
        highlight_ours = self.get_argument('highlight_ours', 'false') == 'true'
        show_sides = self.get_argument('show_sides', 'false') == 'true'

        start_timestamp = Delorean(start_time, 'UTC').epoch * 1000
        end_timestamp = Delorean(end_time, 'UTC').epoch * 1000

        our_trades = self.get_our_trades(start_time, end_time)

        trade_data_by_exchange = self.get_exchange_trades_for_period(
            start_time,
            end_time,
            our_trades,
        )

        self.render_template(
            'trade_view.html',
            args={
                'active_exchanges': active_exchanges,
                'trade_data_by_exchange': trade_data_by_exchange,
                'start_timestamp': start_timestamp,
                'end_timestamp': end_timestamp,
                'highlight_ours': highlight_ours,
                'show_sides': show_sides,
            },
        )

    def get_our_trades(self, start_time, end_time):
        our_trades = self.trading_db.query(
            Trade.exchange_trade_id,
            Trade.trade_type,
        ).filter(Trade.time_created > start_time)\
            .filter(Trade.time_created <= end_time)\
            .filter(Trade.exchange_trade_id != None)\
            .all()

        trade_dict = {}

        for exchange_trade_id, trade_type in our_trades:
            trade_dict[exchange_trade_id] = trade_type

        return trade_dict

    def get_exchange_trades_for_period(self, start_time, end_time, our_trades):
        trades = self.gds_db.query(EHTrade)\
            .filter(EHTrade.timestamp > start_time)\
            .filter(EHTrade.timestamp <= end_time)\
            .all()

        trade_data_by_exchange = defaultdict(lambda: defaultdict(lambda: []))

        for t in trades:
            timestamp = Delorean(t.timestamp, 'UTC').epoch * 1000
            price = float(t.price.to('USD').amount),
            volume = float(t.volume.amount)

            trade_data_by_exchange[t.exchange]['prices'].append([
                timestamp,
                price,
            ])

            trade_data_by_exchange[t.exchange]['volumes'].append(volume)

            if t.exchange_trade_id in our_trades.keys():
                trade_data_by_exchange[t.exchange]['ours'].append(True)

                trade_data_by_exchange[t.exchange]['trade_type'].append(
                    our_trades[t.exchange_trade_id],
                )
            else:
                trade_data_by_exchange[t.exchange]['ours'].append(False)
                trade_data_by_exchange[t.exchange]['trade_type'].append(None)

        return trade_data_by_exchange

