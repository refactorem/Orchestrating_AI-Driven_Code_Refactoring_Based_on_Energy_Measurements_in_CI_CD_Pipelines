import pytest
from primes import primes

def test_primes_benchmark(benchmark):
    benchmark(primes, 5 * 10**3)
