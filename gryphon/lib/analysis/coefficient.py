from scipy.stats import pearsonr

def xcorr_coefficent(xs, ys, maxlags=None):
    """
    Calculate the correlation coefficient of two series' at different lags.
    """

    coefficients = []
    pvalues = []

    for i in range(2, len(xs)):
        this_x = xs[0:i]
        this_y = ys[len(ys) - i:]

        coeff, pvalue = pearsonr(this_x, this_y)

        coefficients.append(coeff)
        pvalues.append(pvalue)

    for i in range(0, len(xs)):
        this_x = xs[i:]
        this_y = ys[0:len(ys) - i]

        coeff, pvalue = pearsonr(this_x, this_y)

        coefficients.append(coeff)
        pvalues.append(pvalue)

    if maxlags:
        mid = len(coefficients)/2
        coefficients = coefficients[mid - maxlags:mid + maxlags]
        pvalues = pvalues[mid - maxlags:mid + maxlags]

    return coefficients, pvalues


def xcorr_coefficent_2(xs, ys, maxlags=1):
    """
    Calculate the correlation coefficient of two series' at different lags using a
    faster method.
    """

    coefficients = []
    pvalues = []

    for lag in range(-maxlags, 0):
        lag = abs(lag)
        this_x = xs[0:len(xs) - lag]
        this_y = ys[lag:]

        coeff, pvalue = pearsonr(this_x, this_y)

        coefficients.append(coeff)
        pvalues.append(pvalue)

    for lag in range(0, maxlags + 1):
        this_x = xs[lag:]
        this_y = ys[0:len(ys) - lag]

        coeff, pvalue = pearsonr(this_x, this_y)

        coefficients.append(coeff)
        pvalues.append(pvalue)

    return coefficients, pvalues
