def humanize_seconds(seconds):
    """Take n seconds and return a human readable string (1h 2m 13s)"""
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    chunks = []

    # 2nd condition is because we want 0 seconds to be represented as "0s" not ""
    if s or seconds == 0:
        seconds_chunk = "%ds" % s
        chunks.insert(0, seconds_chunk)
    if m:
        minutes_chunk = "%dm" % m
        chunks.insert(0, minutes_chunk)
    if h:
        hours_chunk = "%dh" % h
        chunks.insert(0, hours_chunk)

    return " ".join(chunks)
