"""
Inheritance
        Accessing properties of class(object) into another class(Object)

(Parent/super/base class)
class Game
    start(){-----} //Common Property
    stop(){-----} //Common Property

G1_Game(Game):
    g1_run(){-----}


G2_Game(Game):
    g2_run(){-----}

"""

class Employee:# Parent class
    salary=0# Instance variable
    def __init__(self,name,email,designation):
        # Initialize Instance variables with local variable data
        self.name=name
        self.email=email
        self.designation=designation

    def display(self):
        print("Name:",self.name,"\nEmail:",self.email,"\nDesignation:",self.designation,"\nSalary:",self.salary)
# child class
class PartTimeEmployee(Employee):
    # no_of_hrs and per_hrs_salary
    def __init__(self,no_of_hrs,per_hrs_salary,name,email,designation):
        # self.name=name
        # self.email=email
        # self.designation=designation

        # Call parent constructor from child constructor to initialized parent properties
        super().__init__(name,email,designation)#call to parent constructor
        self.no_of_hrs=no_of_hrs
        self.per_hrs_salary=per_hrs_salary

    def calSal(self):
        self.salary=self.no_of_hrs*self.per_hrs_salary # use of inheritance:- access parent salary property into child


pemp=PartTimeEmployee(30,2000,"Ashish","ashish@cybage.com","DBA")
pemp.calSal()
pemp.display()





















