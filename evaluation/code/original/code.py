def primes(n):
    composites = set()
    for i in range(2, n+1):
        for j in range(2, n+1):
            composites.add(i * j)
    primes = []
    for x in range(2, n+1):
        if x not in composites:
            primes.append(x)
    return primes