from collections import defaultdict
from datetime import datetime
import json
import uuid

from cdecimal import Decimal
from sqlalchemy import ForeignKey, Column, Integer, Unicode, DateTime, UnicodeText, Numeric

from gryphon.lib.models.base import Base
from gryphon.lib.session import commit_mysql_session
from gryphon.lib.singleton import Singleton

metadata = Base.metadata


class Datum(Base):
    __tablename__ = 'datum'

    unique_id = Column(Unicode(64), nullable=False)
    datum_id = Column(Integer, primary_key=True)
    time_created = Column(DateTime, nullable=False)
    datum_type = Column(Unicode(256), nullable=False)
    numeric_value = Column(Numeric(precision=20, scale=10))
    string_value = Column(Unicode(256))
    meta_data = Column(UnicodeText(length=2**31))

    order_id = Column(Integer, ForeignKey('order.order_id'), nullable=True)

    def __init__(self, datum_type, numeric_value=None, string_value=None, meta_data={}, order=None):
        self.time_created = datetime.utcnow()
        self.datum_type = datum_type
        self.numeric_value = numeric_value
        self.string_value = string_value
        self.unique_id = u'dat_%s' % unicode(uuid.uuid4().hex)
        self.meta_data = json.dumps(meta_data)
        self.order = order

    def __unicode__(self):
        return unicode(repr(self))

    def __repr__(self):
        d = {
            'datum_type': self.datum_type,
            'time_created': unicode(self.time_created),
            'meta_data': json.loads(self.meta_data),
        }
        if self.numeric_value:
            d.update({'numeric_value': str(self.numeric_value)})
        if self.string_value:
            d.update({'string_value': self.string_value})

        return json.dumps(d, ensure_ascii=False)


class DatumRecorder(object):
    __metaclass__ = Singleton

    def create(self, db=None, logger=None):
        self.db = db
        self.external_logger = logger
        self.data_for_mean = defaultdict(list)

    def record(self, datum_type, numeric_value=None, string_value=None, meta_data={}, order=None):
        datum = Datum(
            datum_type,
            numeric_value=numeric_value,
            string_value=string_value,
            meta_data=meta_data,
            order=order,
        )

        if not hasattr(self, 'db') and not hasattr(self, 'external_logger'):
            raise Exception('DatumRecorder must be created before you can record')

        if self.db:
            self.db.add(datum)
            commit_mysql_session(self.db)
        elif self.external_logger:
            self.external_logger.info(datum)
        else:
            # we aren't recording events.
            pass

    def record_mean(self, datum_type, numeric_value, sample_size):
        """
        Store a datum with the mean of every <sample_size> data points.

        This has weird behaviour if two places call it with different sample_sizes.
        We should only have one DatumRecorder line per datum_type
        """
        if not hasattr(self, 'data_for_mean'):
            raise Exception('DatumRecorder must be created before you can record')

        data = self.data_for_mean[datum_type]
        data.append(numeric_value)

        if len(data) >= sample_size:
            mean = Decimal(sum(data)) / Decimal(len(data))
            self.record(datum_type, numeric_value=mean)
            # Clear the content of a referenced list
            del data[:]
