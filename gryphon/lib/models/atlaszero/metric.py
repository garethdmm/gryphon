import json
from datetime import datetime

import numpy as np
import pandas as pd
from sqlalchemy.dialects.mysql import DATETIME
from sqlalchemy import Column, Integer, Numeric, Index, DateTime

from metric_types import get_metric_type_int
from base import AtlasZeroBase

metadata = AtlasZeroBase.metadata


class MetricException(Exception):
    pass


class Metric(AtlasZeroBase):
    __tablename__ = 'metric'
    __table_args__ = (Index('idx_metric_type_timestamp', 'metric_type', 'timestamp'), )

    metric_id = Column(Integer, primary_key=True)
    timestamp = Column(DATETIME(fsp=6), nullable=False)
    time_created = Column(DateTime, nullable=False)
    metric_type = Column(Integer, nullable=False)
    value = Column(Numeric(precision=20, scale=10))

    def __init__(self, metric_type, value, timestamp):
        self.time_created = datetime.utcnow()
        self.timestamp = timestamp

        self.metric_type = get_metric_type_int(metric_type)
        self.value = value

    def __unicode__(self):
        return unicode(repr(self))

    def __repr__(self):
        d = {
            'metric_id': self.metric_id,
            'timestamp': str(self.timestamp),
            'value': str(self.value),
            'metric_type': self.metric_type,
        }

        return json.dumps(d, ensure_ascii=False)

    @classmethod
    def get_as_pandas_by_series_id(cls, db, series_id):
        raw_series = db.query(Metric).filter(Metric.metric_type == series_id).all()

        pd_series = cls.convert_metric_series_to_pandas(raw_series)

        return pd_series

    @classmethod
    def convert_metric_series_to_pandas(cls, metric_series):
        metric_series = sorted(metric_series, key=lambda m: m.timestamp)

        index = [m.timestamp for m in metric_series]
        values = [float(m.value) if m.value is not None else np.nan for m in metric_series]

        return pd.Series(values, index=index)
