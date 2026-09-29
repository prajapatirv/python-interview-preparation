# """
# Dict:--
# key and value
# created by using {}
# key must be unique
# value can be duplicate
# on the basis of key we can get value from dict
# It supports Item Assignment :- we can modify value associated with given key
# It maintain data in insertion order
#
# """
# my_dict={'Sonali':111,'Niteen':'Java','Sonali':'Python','Vivek':'.Net','Santosh':'.Net'}
# print(type(my_dict))
# print(my_dict)
# print("Sonali:",my_dict['Sonali'])
# my_dict['Sonali']=20000
#
# print("Sonali:",my_dict['Sonali'])
#
#
# # Dynamic inputs in dict
# employees={}
# count=int(input("Enter Count of Employees"))# 3
# # for val in range(3):# 0,1,2
# #     name=input("Enter Employee Name:")
# #     techStack=input("Enter Current Tech Stack:")
# #     employees[name]=techStack
# #
# # print(employees)
#
# # code comprehension
#
# emp_stack={input("Enter Employee Name:"):input("Enter Current Tech Stack:") for val in range(count)}
# print(emp_stack)
#
# # Accept List of Numbers from User--1 2 3 4 5
# my_list=list(map(int,input("Enter List Elements:").split(" ")))
# # Iterate(For) List and find square(** power Operator) of each element and store it in key value as part dict.
# # {element:element**2}
# # basic approach
# # sq_dict={}
# # for ele in my_list:
# #     sq_dict[ele]=ele**2
# #
# # print(sq_dict)
#
# # code comprehension
# sq_dict={ele:ele**2 for ele in my_list}
# print(sq_dict)
#
#
#
# """
# Get Set from User holding numbers
# if number is even-in dict store no(key):"Even"
# if number is odd-in dict store no(key):"ODD"
#
# """
# numbers=set(map(int,input("Enter Set Elements").split(" ")))
# even_odd={val:"EVEN" if val%2==0 else "ODD" for val in numbers}
# print(even_odd)


"""
Methods of dict

"""
my_dict={'Sonali':111,'Niteen':'Java','Sonali':'Python','Vivek':'.Net','Santosh':'.Net'}
print(my_dict.keys())
print(my_dict.values())
print(my_dict.items())# use with for

for k,v in my_dict.items():
    print(k,v)
# //Accept Dict from user holding Employee id as key and name as value and then create new dict with hold
# name as key and id as value




