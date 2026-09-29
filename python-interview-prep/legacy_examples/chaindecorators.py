def decorator1(func):
    def wrapper():
        print("Decorator 1 - Before Function")
        func()
        print("Decorator 1 - After Function")
    return wrapper

def decorator2(func):
    def wrapper():
        print("Decorator 2 - Before Function")
        func()
        print("Decorator 2 - After Function")
    return wrapper

@decorator1
@decorator2
def greet():
    print("Hello, World!")

greet()