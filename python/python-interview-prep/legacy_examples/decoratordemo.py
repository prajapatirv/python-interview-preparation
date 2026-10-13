import functools, time

def timer(func):
    @functools.wraps(func)              # preserves func's name & docstring
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        print(f"{func.__name__} took {time.time()-start:.4f}s")
        return result
    return wrapper

@timer
def compute(n):
    return sum(i*i for i in range(n))

compute(1000000)   # prints timing, then returns result

def repeat(times):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for _ in range(times):
                result = func(*args, **kwargs)
            return result
        return wrapper
    return decorator

@repeat(times=3)
def greet(name):
    print(f"Hi {name}")

print("greet > ",greet(" Durgesh"))