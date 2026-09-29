""""
Local variable :-
    declared with in particular block(method)
    And can be access within that block only
Instance Variables
    name
    email
    designation
    salary
    Instance method :- method which accept first implicit parameter 'self'
                        method will get invoked on class object
                        we do not require to pass argument(value) for 'self' parameter PVM will take care of it.
                        self is used to declare instance variables and even used to access same
                        First Parameter is implicit parameter we can rename name that parameter

    Constructor is a special method-Instance method
        _ _ init _ _ (self):--Default Constructor
        It always gets invoked/call implicitly once we create object of class
        Constructor overloading is not applicable in python
"""
class Employee:
    #  Variables
    # constructor
    def __init__(self):
        print("Default Constructor")

    def __init__(cybage,name,email,designation,salary):# Local variables
        print("Second Constructor")
        # Declare instance variable using 'self'
        # Copy data from local to instance variable--constructor is build from initialization of Instance variable
        cybage.name=name
        cybage.email=email
        cybage.salary=salary
        cybage.designation=designation

    # Instance methods
    def display(cybage):
        print("!!!Employee Details!!!")
        print(cybage.name,cybage.email,cybage.designation,cybage.salary)
# Object
# emp=Employee()# call default constructor
emp=Employee("Anagha","a@gmail.com","QA",70000)# call last implemented parametrized constructor
emp.display()
# Create Class call Product-productName/brandName,price,quantity --Accept data from user





