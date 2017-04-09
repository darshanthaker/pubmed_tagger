import time

def timing(func):
    """
        Timing decorator that will take any function and time it. Will print to 
        stdout how long the function took in seconds.
        Example usage:
        @timing
        def some_func():
            # Some long function.
        When running some_func(), it will print out that:
            'some_func took x seconds' 
        This will be useful to time functions easily by adding a decorator.
    """

    def wrapper(*arg):
        t1 = time.time()
        ret_val = func(*arg)
        t2 = time.time()
        print("{} took {} seconds".format(func.__name__, t2 - t1))
        return ret_val

    return wrapper
