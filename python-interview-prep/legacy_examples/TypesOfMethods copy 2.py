
"""
Note:- If class is not holding any constructor PVM provide default constructor implicitly
Instance method
    can invoke on class object
    accept first implicit parameter 'self'

Class Method
    Add decorator @classmethod
    and accept default implicit parameter call 'cls'
    invoked on class object or class name
    'cls' is used to access and declare instance variable under class method

Static Method
        Add decorator @staticmethod
        It does not accept any default implicit parameter
        can invoke on class name or object
        Can access Instance variable using Class Name
"""

class Abc:
    # Instance variable
    company="Cybage"

    # Instance method
    def show_1(self):
        print("Instance method:",self.company,self.address)

    @classmethod
    def show_2(cls):
        # Declare instance variable
        cls.address="Pune"
        print("Class Method:",cls.company,cls.address)

    @staticmethod
    def show_3(a,b):# variable from parameter list are always in local scope
        print("Static method:",Abc.address,Abc.company,a,b)

obj=Abc()# Default constructor
# Call class method
obj.show_2()# invoked on class object
Abc.show_2()# invoked on class Object

#Call instance method
obj.show_1()
# Abc.show_1()# Error

# Call static method
obj.show_3(1,2)
Abc.show_3(1,2)



"""
Note:- If class is not holding any constructor PVM provide default constructor implicitly
Instance method
    can invoke on class object
    accept first implicit parameter 'self'

Class Method
    Add decorator @classmethod
    and accept default implicit parameter call 'cls'
    invoked on class object or class name
    'cls' is used to access and declare instance variable under class method

Static Method
        Add decorator @staticmethod
        It does not accept any default implicit parameter
        can invoke on class name or object
        Can access Instance variable using Class Name
"""

class Abc:
    # Instance variable
    company="Cybage"

    # Instance method
    def show_1(self):
        print("Instance method:",self.company,self.address)

    @classmethod
    def show_2(cls):
        # Declare instance variable
        cls.address="Pune"
        print("Class Method:",cls.company,cls.address)

    @staticmethod
    def show_3(a,b):# variable from parameter list are always in local scope
        print("Static method:",Abc.address,Abc.company,a,b)

obj=Abc()# Default constructor
# Call class method
obj.show_2()# invoked on class object
Abc.show_2()# invoked on class Object

#Call instance method
obj.show_1()
# Abc.show_1()# Error

# Call static method
obj.show_3(1,2)
Abc.show_3(1,2)


