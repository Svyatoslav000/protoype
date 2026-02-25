import numpy as np
from scipy.stats import norm


def calculate_sample_size(cv_intra, power=0.8, alpha=0.05, dropout=0.2):
    if cv_intra is None:
        raise ValueError("cv_intra не может быть None")
    if cv_intra <= 0:
        raise ValueError("cv_intra должен быть положительным")

    z_alpha = norm.ppf(1 - alpha / 2)  # 1.96
    z_beta = norm.ppf(power)  # 0.842
    sigma2 = np.log(1 + cv_intra ** 2)
    theta_low = np.log(0.80)

    N = int(np.ceil(2 * ((z_alpha + z_beta) ** 2 * sigma2) / (theta_low ** 2)))
    N_total = int(np.ceil(N / (1 - dropout)))

    return N, N_total