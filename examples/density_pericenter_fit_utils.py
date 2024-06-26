import time
import numpy as np
import emcee
from multiprocessing import Pool
from scipy.optimize import minimize


def log_model(x, q, m):
    # Model: Power-law function
    # f_theta = 10^q r^m
    # log10 f_theta
    f = q + m * x
    return f


def log_prior(theta):
    """
    The natural logarithm of the prior probability.
    It sets prior to 1 (log prior to 0) if params are in range, and zero (-inf) otherwise.
    Args: theta (tuple): a sample containing individual parameter values
    """
    q, m = theta
    log_prior = -np.inf
    if -2 < q < 2 and -2 < m < 2 : log_prior = 0.0
    return log_prior


def log_likelihood(theta, x, y, xerr, yerr):
    """
    The natural logarithm of the joint likelihood.
    Args:
        theta (tuple): a sample containing individual parameter values
        x (array): values over which the data/model is defined
        y (array): the set of data
        xerr (array): the standard deviation of the data points
        yerr (array): the standard deviation of the data points
    """
    q, m = theta
    model = log_model(x, q, m)
    sigma2 = yerr**2 + (m * 10**model) **2 * (xerr / 10**x) **2
    ll = (10**y - 10**model) ** 2 / sigma2
    ll += np.log( 2. * np.pi * sigma2 )
    log_l = -0.5 * np.sum(ll)
    return log_l

def log_likelihood_sim(theta, x, y, yerr):
    """
    The natural logarithm of the joint likelihood.
    Args:
        theta (tuple): a sample containing individual parameter values
        x (array): values over which the data/model is defined
        y (array): the set of data
    """
    q, m = theta
    model = log_model(x, q, m)
    sigma2 = yerr**2
    ll = (10**y - 10**model) ** 2 / sigma2
    log_l = -0.5 * np.sum(ll)
    return log_l


def log_posterior(theta, x, y, xerr, yerr):
    """
    The natural logarithm of the joint posterior.
    Args:
        theta (tuple): a sample containing individual parameter values
        x (array): values over which the data/model is defined
        y (array): the set of data
        xerr (array): the standard deviation of the data points
        yerr (array): the standard deviation of the data points
    """
    lp = log_prior(theta)
    if not np.isfinite(lp):
        return -np.inf
    return lp + log_likelihood(theta, x, y, xerr, yerr)

def log_posterior_sim(theta, x, y, yerr):
    """
    The natural logarithm of the joint posterior.
    Args:
        theta (tuple): a sample containing individual parameter values
        x (array): values over which the data/model is defined
        y (array): the set of data
    """
    lp = log_prior(theta)
    if not np.isfinite(lp):
        return -np.inf
    return lp + log_likelihood_sim(theta, x, y, yerr)


def run_mcmc(x, y, xerr, yerr, soln):

    pos = soln.x + 1e-1 * np.random.randn(64, 2)
    nwalkers, ndim = pos.shape

    with Pool() as pool:
        sampler = emcee.EnsembleSampler(nwalkers, ndim, log_posterior, args=(x, y, xerr, yerr))
        start = time.time()
        sampler.run_mcmc(pos, 2000, progress=True)
        end = time.time()
        multi_time = end - start
        print("Multiprocessing took {0:.1f} minutes".format(multi_time / 60))

    samples = sampler.get_chain(discard=100, thin=15, flat=True)

    print("Mean autocorrelation time: {0:.3f} steps".format(np.mean(sampler.get_autocorr_time(quiet=True))))
    return samples

def run_mcmc_sim(x, y, yerr, soln):

    pos = soln.x + 1e-1 * np.random.randn(64, 2)
    nwalkers, ndim = pos.shape

    with Pool() as pool:
        sampler = emcee.EnsembleSampler(nwalkers, ndim, log_posterior_sim, args=(x, y, yerr))
        start = time.time()
        sampler.run_mcmc(pos, 2000, progress=True)
        end = time.time()
        multi_time = end - start
        # print("Multiprocessing took {0:.1f} minutes".format(multi_time / 60))

    samples = sampler.get_chain(discard=100, thin=15, flat=True)

    # print("Mean autocorrelation time: {0:.3f} steps".format(np.mean(sampler.get_autocorr_time(quiet=True))))
    return samples


def run_best_fit(r_p, rho_150pc):
    # Prepare arrays ..
    x = np.log10(r_p[0, :])
    xerr = r_p[1, :] ** 2 + r_p[2, :] ** 2
    xerr = np.sqrt(xerr)

    y = np.log10(rho_150pc[0, :] / 1e7)
    yerr = rho_150pc[1, :] ** 2 + rho_150pc[2, :] ** 2
    yerr = np.sqrt(yerr) / 1e7

    # Make initial fit ..
    np.random.seed(42)
    nl = lambda *args: -log_likelihood(*args)
    initial = np.array([1, 0])
    soln = minimize(nl, initial, args=(x, y, xerr, yerr))
    q, m = soln.x
    print('=======')
    print(q, m)

    samples = run_mcmc(x, y, xerr, yerr, soln)

    return samples

def run_best_fit_for_sim(r_p, rho_150pc):

    # Prepare arrays ..
    x = np.log10(r_p)
    y = np.log10(rho_150pc / 1e7)
    yerr = np.ones(len(y)) * 1e5 / 1e7

    # Make initial fit ..
    np.random.seed(42)
    nl = lambda *args: -log_likelihood_sim(*args)
    initial = np.array([1, 0])
    bounds = ((-2, 2), (-2, 2))
    soln = minimize(nl, initial, args=(x, y, yerr), bounds=bounds)
    q, m = soln.x
    # print('=======')
    # print(q, m)
    #
    # samples = run_mcmc(x, y, xerr, yerr, soln)
    # return samples
    return q, m


def run_best_fit_for_sim_with_mcmc(r_p, rho_150pc):

    # Prepare arrays ..
    x = np.log10(r_p)
    y = np.log10(rho_150pc / 1e7)
    yerr = np.ones(len(y)) * 1e5 / 1e7

    # Make initial fit ..
    np.random.seed(42)
    nl = lambda *args: -log_likelihood_sim(*args)
    initial = np.array([1, 0])
    bounds = ((-2, 2), (-2, 2))
    soln = minimize(nl, initial, args=(x, y, yerr), bounds=bounds)
    q, m = soln.x
    samples = run_mcmc_sim(x, y, yerr, soln)
    return samples
