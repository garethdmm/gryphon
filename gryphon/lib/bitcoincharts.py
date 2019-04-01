import requests
import datetime
from delorean import Delorean
from cdecimal import Decimal
from gryphon.lib.logger import get_logger
logger = get_logger(__name__)

class BitcoinCharts(object):
    trades_base_url = 'http://api.bitcoincharts.com/v1/trades.csv?symbol=bitstampUSD&start='


    """
        This function seems to be off frequently by about 1000 bitcoins
        from the graphs bitcoincharts gives. This may be because they
        don't operate in UTC or could be something more sinister.
        For now it acts as a reasonable approximation.

        The control flow of this function is a little bit hard to 
        understand immediately. Essentially it continues requesting more
        trades from bitcoincharts until it sees one that is after the 'end'
        argument, but we have to guard for several edge cases, such as when
        we're requesting the most recent period of trades, in which case
        we will never hit the normal termination condition.
    """
    def get_bitstamp_volume_between_timestamps(self, start, end):
        volume = Decimal('0.0')
        last_processed_timestamp = start

        while last_processed_timestamp < end:
            request_url = self.trades_base_url + str(last_processed_timestamp)

            req = requests.get(request_url)

            if len(req.text) < 2:
                logger.info("Bad response from bitcoincharts")
                break

            lines = req.text.split('\n')

            for line in lines:
                tokens = line.split(',')

                trade_volume = float(tokens[2].strip())
                trade_timestamp = int(tokens[0])

                last_processed_timestamp = trade_timestamp

                if not last_processed_timestamp < end:
                    break
                else:
                    volume = volume + Decimal(trade_volume)
            
            # this catches the case that it was a single-line response
            # but that one line is a trade shortly before our 'end'
            if len(lines) <= 1:
                break

        return volume


    def get_24_hour_bitstamp_exchange_volume(self):
        start = int(Delorean().last_day().epoch)
        end = int(Delorean().epoch)

        volume = self.get_bitstamp_volume_between_timestamps(
            start,
            end,
        )

        return volume
        

